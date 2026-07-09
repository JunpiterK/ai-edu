# -*- coding: utf-8 -*-
"""
Build the public AI_EDU static site into dist/.

Usage:
    python build_site.py
    $env:SITE_URL = "https://your-domain.com"; python build_site.py

The build keeps source files simple while making deployment output cleaner:
    - copies only public-facing pages
    - excludes backups, drafts, local settings, markdown docs, and caches
    - rewrites placeholder canonical/OG URLs to SITE_URL in dist
    - generates sitemap.xml, robots.txt, and Cloudflare Pages _headers
    - checks Cloudflare Pages' 25 MB per-file limit
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape, unescape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

MAX_FILE_SIZE = 25 * 1024 * 1024  # Cloudflare Pages: 25 MB per file
SITE_URL = os.environ.get("SITE_URL", "https://ai-edu-archive.pages.dev").rstrip("/")
SITE_HOST = urlparse(SITE_URL).netloc or SITE_URL.removeprefix("https://").removeprefix("http://")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", f"hello@{SITE_HOST}")

PLACEHOLDER_URLS = (
    "https://ai-edu.example",
    "https://ai-edu-archive.example.com",
)

PLACEHOLDER_DOMAINS = (
    "ai-edu.example",
    "ai-edu-archive.example.com",
)

TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".htm",
    ".js",
    ".json",
    ".svg",
    ".txt",
    ".xml",
}

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_RE = re.compile(r"<meta\s+([^>]+)>", re.IGNORECASE)
ATTR_RE = re.compile(r'([a-zA-Z_:.-]+)\s*=\s*["\']([^"\']*)["\']')
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
RT_RE = re.compile(r'<span\s+class=["\']rt["\']>(.*?)</span>', re.IGNORECASE | re.DOTALL)
ARTICLE_INDEX_RE = re.compile(
    r'(<ol[^>]*class=["\'][^"\']*article-index[^"\']*["\'][^>]*id=["\']articleIndex["\'][^>]*>)(.*?)(</ol>)',
    re.IGNORECASE | re.DOTALL,
)
EXISTING_POST_RE = re.compile(
    r'<li><a\s+class=["\']post["\']\s+data-cat=["\']([^"\']*)["\']\s+href=["\']([^"\']*)["\'][^>]*>'
    r'.*?<span\s+class=["\']cat-tag["\']>(.*?)</span>'
    r'.*?<time\s+datetime=["\']([^"\']*)["\']>(.*?)</time>'
    r'.*?<span\s+class=["\']rt["\']>(.*?)</span>',
    re.IGNORECASE | re.DOTALL,
)


def normalize_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def first_match(pattern: str) -> str:
    matches = sorted(ROOT.glob(pattern))
    if not matches:
        sys.exit(f"[ERROR] No file matched required pattern: {pattern}")
    return normalize_rel(matches[0])


def public_blog_files() -> list[str]:
    files: list[str] = []
    for path in sorted((ROOT / "blog").rglob("*")):
        if not path.is_file():
            continue

        rel = normalize_rel(path)
        name = path.name.lower()
        suffix = path.suffix.lower()

        if (
            "backup" in name
            or name == "article-template.html"
            or name.startswith(".translation_cache")
            or suffix in {".md", ".json"}
        ):
            continue

        files.append(rel)
    return files


def build_include_list() -> list[str]:
    include = [
        "index.html",
        "overview/index.html",
        "overview/08_GPU_TPU_NPU.html",
        first_match("overview/09_Panoptes_*.html"),
        first_match("overview/11_AI_*.html"),
        "watsonx/index.html",
        "llm_apply/LLM_slide.html",
        "llm_apply/RAG_BUILD_SLIDE.html",
        "llm_apply/AGENT_OPS_SLIDE.html",
    ]
    include.extend(public_blog_files())

    seen: set[str] = set()
    ordered: list[str] = []
    for rel in include:
        rel = rel.replace("\\", "/")
        key = rel.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(rel)
    return ordered


def public_url_for(rel: str) -> str:
    rel = rel.replace("\\", "/")
    if rel.endswith("/index.html"):
        rel = rel[: -len("index.html")]
    elif rel == "index.html":
        rel = ""
    return f"{SITE_URL}/{rel}".rstrip("/") + ("/" if rel.endswith("/") else "")


def read_html_meta(rel: str) -> dict[str, str]:
    text = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
    meta: dict[str, str] = {}

    title_match = TITLE_RE.search(text)
    if title_match:
        meta["title"] = unescape(re.sub(r"\s+", " ", title_match.group(1)).strip())

    for match in META_RE.finditer(text):
        attrs = {key.lower(): unescape(value) for key, value in ATTR_RE.findall(match.group(1))}
        key = attrs.get("name") or attrs.get("property")
        content = attrs.get("content")
        if key and content:
            meta[key.lower()] = content

    h1_match = H1_RE.search(text)
    if h1_match:
        h1_text = re.sub(r"<[^>]+>", " ", h1_match.group(1))
        meta["h1"] = unescape(re.sub(r"\s+", " ", h1_text).strip())

    rt_match = RT_RE.search(text)
    if rt_match:
        rt_text = re.sub(r"<[^>]+>", " ", rt_match.group(1))
        meta["reading_time"] = unescape(re.sub(r"\s+", " ", rt_text).strip())

    return meta


def maybe_rewrite_text(src: Path, dst: Path) -> None:
    text = src.read_text(encoding="utf-8")
    text = text.replace("hello@ai-edu-archive.example.com", SUPPORT_EMAIL)
    for placeholder in PLACEHOLDER_URLS:
        text = text.replace(placeholder, SITE_URL)
    for placeholder in PLACEHOLDER_DOMAINS:
        text = text.replace(placeholder, SITE_HOST)
    dst.write_text(text, encoding="utf-8")


def copy_public_file(rel: str) -> tuple[str, int]:
    src = ROOT / rel
    if not src.is_file():
        sys.exit(f"[ERROR] Missing public file: {src}")

    size = src.stat().st_size
    if size > MAX_FILE_SIZE:
        sys.exit(f"[ERROR] {rel} exceeds 25 MB: {size / 1024 / 1024:.1f} MB")

    dst = DIST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)

    if src.suffix.lower() in TEXT_SUFFIXES:
        maybe_rewrite_text(src, dst)
    else:
        shutil.copy2(src, dst)

    return dst.relative_to(DIST).as_posix(), dst.stat().st_size


def lastmod_for(rel: str) -> str:
    src = ROOT / rel
    dt = datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc)
    return dt.date().isoformat()


def sitemap_priority(rel: str) -> str:
    if rel == "index.html":
        return "1.0"
    if rel in {"blog/index.html", "blog/ko/index.html"}:
        return "0.9"
    if rel.endswith("/index.html"):
        return "0.8"
    if "/articles/" in rel:
        return "0.7"
    return "0.6"


def generate_sitemap(public_files: list[str]) -> int:
    html_files = [rel for rel in public_files if rel.lower().endswith(".html")]
    url_blocks = []
    for rel in sorted(html_files, key=lambda item: public_url_for(item)):
        url_blocks.append(
            "  <url>\n"
            f"    <loc>{public_url_for(rel)}</loc>\n"
            f"    <lastmod>{lastmod_for(rel)}</lastmod>\n"
            "    <changefreq>weekly</changefreq>\n"
            f"    <priority>{sitemap_priority(rel)}</priority>\n"
            "  </url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(url_blocks)
        + "\n</urlset>\n"
    )
    path = DIST / "sitemap.xml"
    path.write_text(xml, encoding="utf-8")
    return path.stat().st_size


def generate_robots() -> int:
    text = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    path = DIST / "robots.txt"
    path.write_text(text, encoding="utf-8")
    return path.stat().st_size


def article_files_for_language(public_files: list[str], lang: str) -> list[str]:
    prefix = "blog/ko/articles/" if lang == "ko" else "blog/articles/"
    articles = [
        rel
        for rel in public_files
        if rel.startswith(prefix)
        and rel.endswith(".html")
        and "backup" not in Path(rel).name.lower()
    ]
    return sorted(articles, key=lambda rel: read_html_meta(rel).get("article:published_time", ""), reverse=True)


def strip_site_suffix(title: str) -> str:
    title = title.replace(" - AI Edu Archive Journal", "")
    title = re.sub(r"\s*-\s*AI Edu Archive.*$", "", title)
    return title.strip()


def article_records(public_files: list[str], lang: str = "en") -> list[dict[str, str]]:
    records = []
    for rel in article_files_for_language(public_files, lang):
        meta = read_html_meta(rel)
        title = title_for_index(meta, rel)
        records.append(
            {
                "title": title,
                "description": meta.get("description") or meta.get("og:description") or "",
                "url": public_url_for(rel),
                "path": rel,
                "published": meta.get("article:published_time") or lastmod_for(rel),
                "section": meta.get("article:section") or "",
            }
        )
    return records


def category_key(section: str, path: str, title: str) -> str:
    section_l = section.lower()
    haystack = f"{section_l} {path.lower()} {title.lower()}"
    keys = []
    if "on-prem" in haystack or "onprem" in haystack or "air-gapped" in haystack:
        keys.append("onprem")
    if "rag" in haystack or "retrieval" in haystack or "embedding" in haystack or "chunk" in haystack:
        keys.append("rag")
    if "agent" in haystack or "mcp" in haystack or "langgraph" in haystack:
        keys.append("agents")
    if "python" in haystack or "langchain" in haystack or "langgraph" in haystack or "module" in haystack:
        keys.append("python")
    if "manufacturing" in haystack or "fab" in haystack or "process" in haystack or "mes" in haystack:
        keys.append("mfg")
    return " ".join(dict.fromkeys(keys)) or "python"


def category_label(section: str, data_cat: str, lang: str) -> str:
    if section:
        if lang == "ko":
            labels = {
                "On-Prem LLM": "온프레미스 LLM",
                "Agents & MCP": "Agent & MCP",
                "Manufacturing AI": "제조 AI",
                "Python Stack": "Python Stack",
                "RAG": "RAG",
            }
            return labels.get(section, section)
        return section

    first = data_cat.split()[0] if data_cat else "python"
    labels_en = {
        "onprem": "On-Prem LLM",
        "rag": "RAG",
        "agents": "Agents & MCP",
        "python": "Python Stack",
        "mfg": "Manufacturing AI",
    }
    labels_ko = {
        "onprem": "온프레미스 LLM",
        "rag": "RAG",
        "agents": "Agent & MCP",
        "python": "Python Stack",
        "mfg": "제조 AI",
    }
    return (labels_ko if lang == "ko" else labels_en).get(first, "Python Stack")


def display_date(value: str, lang: str) -> str:
    try:
        dt = datetime.fromisoformat(value).date()
    except ValueError:
        return value
    if lang == "ko":
        return dt.strftime("%Y.%m.%d")
    return dt.strftime("%b ") + str(dt.day) + dt.strftime(", %Y")


def title_for_index(meta: dict[str, str], rel: str) -> str:
    raw = meta.get("h1") or meta.get("og:title") or meta.get("title") or Path(rel).stem
    return strip_site_suffix(raw)


def clean_inline_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return unescape(re.sub(r"\s+", " ", value).strip())


def existing_index_overrides(lang: str) -> dict[str, dict[str, str]]:
    rel = "blog/ko/index.html" if lang == "ko" else "blog/index.html"
    path = ROOT / rel
    if not path.is_file():
        return {}

    text = path.read_text(encoding="utf-8", errors="ignore")
    overrides = {}
    for match in EXISTING_POST_RE.finditer(text):
        data_cat, href, label, published, display_date_value, reading_time = match.groups()
        overrides[href] = {
            "data_cat": clean_inline_html(data_cat),
            "label": clean_inline_html(label),
            "published": clean_inline_html(published),
            "display_date": clean_inline_html(display_date_value),
            "reading_time": clean_inline_html(reading_time),
        }
    return overrides


def records_for_language(public_files: list[str], lang: str) -> list[dict[str, str]]:
    prefix = "blog/ko/articles/" if lang == "ko" else "blog/articles/"
    overrides = existing_index_overrides(lang)
    records = []
    for rel in public_files:
        if not rel.startswith(prefix) or not rel.endswith(".html"):
            continue
        if "backup" in Path(rel).name.lower():
            continue

        meta = read_html_meta(rel)
        title = title_for_index(meta, rel)
        section = meta.get("article:section") or ""
        published = meta.get("article:published_time") or lastmod_for(rel)
        data_cat = category_key(section, rel, title)
        href = rel.removeprefix("blog/ko/" if lang == "ko" else "blog/")
        reading_time = meta.get("reading_time") or ("10분" if lang == "ko" else "10 min")
        record = {
            "title": title,
            "description": meta.get("description") or meta.get("og:description") or "",
            "href": href,
            "published": published,
            "display_date": display_date(published, lang),
            "reading_time": reading_time,
            "section": section,
            "data_cat": data_cat,
            "label": category_label(section, data_cat, lang),
        }
        record.update(overrides.get(href, {}))
        records.append(record)

    return sorted(records, key=lambda record: record["published"], reverse=True)


def render_article_item(record: dict[str, str], lang: str) -> str:
    cta = "한국어판 읽기" if lang == "ko" else "Read article"
    return (
        f'<li><a class="post" data-cat="{escape(record["data_cat"])}" href="{escape(record["href"])}">\n'
        f'<div class="post-meta"><span class="cat-tag">{escape(record["label"])}</span>'
        f'<span class="post-dot"></span><time datetime="{escape(record["published"])}">{escape(record["display_date"])}</time>'
        f'<span class="post-dot"></span><span class="rt">{escape(record["reading_time"])}</span></div>\n'
        f"<h2>{escape(record['title'])}</h2>\n"
        f'<p class="excerpt">{escape(record["description"])}</p>\n'
        f'<span class="go">{cta} <span aria-hidden="true" class="arw">→</span></span>\n'
        "</a></li>"
    )


def render_article_list(records: list[dict[str, str]], lang: str) -> str:
    items = []
    for index, record in enumerate(records):
        if lang == "en" and index == 11:
            items.append(
                '<li aria-hidden="false"><div aria-label="In-feed advertisement placeholder" '
                'class="ad-slot ad-infeed" role="complementary"><span class="ad-note">'
                "In-feed ad slot — blends with the flow when live.</span></div></li>"
            )
        items.append(render_article_item(record, lang))
    return "\n" + "\n".join(items) + "\n"


def rewrite_blog_index(public_files: list[str], lang: str) -> None:
    rel = "blog/ko/index.html" if lang == "ko" else "blog/index.html"
    path = DIST / rel
    if not path.is_file():
        return

    text = path.read_text(encoding="utf-8")
    records = records_for_language(public_files, lang)
    if not records:
        return

    def replace(match: re.Match[str]) -> str:
        return match.group(1) + render_article_list(records, lang) + match.group(3)

    new_text, count = ARTICLE_INDEX_RE.subn(replace, text, count=1)
    if count != 1:
        sys.exit(f"[ERROR] Could not rewrite article index in {rel}")
    path.write_text(new_text, encoding="utf-8")


def rewrite_blog_indexes(public_files: list[str]) -> None:
    rewrite_blog_index(public_files, "en")
    rewrite_blog_index(public_files, "ko")


def generate_articles_json(public_files: list[str], lang: str, output_rel: str) -> int:
    import json

    records = article_records(public_files, lang)
    text = json.dumps(
        {
            "site": "AI Edu Archive",
            "language": lang,
            "siteUrl": SITE_URL,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "articles": records,
        },
        ensure_ascii=False,
        indent=2,
    )
    path = DIST / output_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    return path.stat().st_size


def rss_date(value: str, rel: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        dt = datetime.fromtimestamp((ROOT / rel).stat().st_mtime, tz=timezone.utc)
    return format_datetime(dt)


def generate_rss(public_files: list[str], lang: str, output_rel: str) -> int:
    records = article_records(public_files, lang)
    channel_title = "AI Edu Archive Journal" if lang == "en" else "AI Edu Archive Korean Journal"
    channel_link = f"{SITE_URL}/blog/" if lang == "en" else f"{SITE_URL}/blog/ko/"
    channel_description = (
        "Applied AI, robotics, manufacturing AI, on-prem LLM, RAG, and agent systems."
        if lang == "en"
        else "Korean articles on applied AI, robotics AI, manufacturing AI, on-prem LLM, RAG, MCP, and agent systems."
    )
    items = []
    for record in records[:30]:
        items.append(
            "    <item>\n"
            f"      <title>{escape(record['title'])}</title>\n"
            f"      <link>{escape(record['url'])}</link>\n"
            f"      <guid>{escape(record['url'])}</guid>\n"
            f"      <description>{escape(record['description'])}</description>\n"
            f"      <category>{escape(record['section'])}</category>\n"
            f"      <pubDate>{rss_date(record['published'], record['path'])}</pubDate>\n"
            "    </item>"
        )

    text = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{escape(channel_title)}</title>\n"
        f"    <link>{escape(channel_link)}</link>\n"
        f"    <description>{escape(channel_description)}</description>\n"
        f"    <language>{lang}</language>\n"
        f"    <lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>\n"
        + "\n".join(items)
        + "\n  </channel>\n"
        "</rss>\n"
    )
    path = DIST / output_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path.stat().st_size


def generate_llms_txt(public_files: list[str]) -> int:
    records = article_records(public_files)
    lines = [
        "# AI Edu Archive",
        "",
        "AI Edu Archive is a static educational archive about applied AI, robotics AI, manufacturing AI, on-prem LLMs, RAG, MCP, and agent systems.",
        "",
        "## Core Pages",
        f"- Home: {SITE_URL}/",
        f"- Journal: {SITE_URL}/blog/",
        f"- Korean Journal: {SITE_URL}/blog/ko/",
        f"- Portfolio: {SITE_URL}/blog/portfolio.html",
        f"- About: {SITE_URL}/blog/about.html",
        f"- RSS: {SITE_URL}/rss.xml",
        f"- Korean RSS: {SITE_URL}/blog/ko/rss.xml",
        f"- Article Index JSON: {SITE_URL}/blog/articles.json",
        f"- Korean Article Index JSON: {SITE_URL}/blog/ko/articles.json",
        "",
        "## Courses",
        f"- Fab AI overview: {SITE_URL}/overview/",
        f"- Air-gapped LLM overview: {SITE_URL}/watsonx/",
        f"- Enterprise LLM slide deck: {SITE_URL}/llm_apply/LLM_slide.html",
        f"- RAG build slide deck: {SITE_URL}/llm_apply/RAG_BUILD_SLIDE.html",
        f"- Agent operations slide deck: {SITE_URL}/llm_apply/AGENT_OPS_SLIDE.html",
        "",
        "## Recent Articles",
    ]

    for record in records[:20]:
        description = f" - {record['description']}" if record["description"] else ""
        lines.append(f"- [{record['title']}]({record['url']}){description}")

    path = DIST / "llms.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path.stat().st_size


def generate_headers() -> int:
    text = (
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
        "\n"
        "/*.html\n"
        "  Cache-Control: public, max-age=0, must-revalidate\n"
        "\n"
        "/assets/*\n"
        "  Cache-Control: public, max-age=31536000, immutable\n"
        "\n"
        "/blog/assets/*\n"
        "  Cache-Control: public, max-age=31536000, immutable\n"
        "\n"
        "/sitemap.xml\n"
        "  Content-Type: application/xml; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
        "\n"
        "/rss.xml\n"
        "  Content-Type: application/rss+xml; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
        "\n"
        "/blog/ko/rss.xml\n"
        "  Content-Type: application/rss+xml; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
        "\n"
        "/llms.txt\n"
        "  Content-Type: text/plain; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
        "\n"
        "/blog/articles.json\n"
        "  Content-Type: application/json; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
        "\n"
        "/blog/ko/articles.json\n"
        "  Content-Type: application/json; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
        "\n"
        "/robots.txt\n"
        "  Content-Type: text/plain; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
    )
    path = DIST / "_headers"
    path.write_text(text, encoding="utf-8")
    return path.stat().st_size


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    include = build_include_list()
    copied = [copy_public_file(rel) for rel in include]
    rewrite_blog_indexes(include)

    generated = [
        ("sitemap.xml", generate_sitemap(include)),
        ("robots.txt", generate_robots()),
        ("rss.xml", generate_rss(include, "en", "rss.xml")),
        ("blog/ko/rss.xml", generate_rss(include, "ko", "blog/ko/rss.xml")),
        ("llms.txt", generate_llms_txt(include)),
        ("blog/articles.json", generate_articles_json(include, "en", "blog/articles.json")),
        ("blog/ko/articles.json", generate_articles_json(include, "ko", "blog/ko/articles.json")),
        ("_headers", generate_headers()),
    ]

    total_size = sum(size for _, size in copied) + sum(size for _, size in generated)

    print("=" * 72)
    print("AI_EDU public build complete -> dist/")
    print(f"Site URL: {SITE_URL}")
    print(f"Support email: {SUPPORT_EMAIL}")
    print("=" * 72)
    for rel, size in copied:
        print(f"  {size / 1024 / 1024:7.2f} MB  {rel}")
    for rel, size in generated:
        print(f"  {size / 1024 / 1024:7.2f} MB  {rel}  (generated)")
    print("-" * 72)
    print(f"  {len(copied) + len(generated)} files, {total_size / 1024 / 1024:.2f} MB")
    print("  Cloudflare Pages limit check: 20,000 files / 25 MB per file")


if __name__ == "__main__":
    main()
