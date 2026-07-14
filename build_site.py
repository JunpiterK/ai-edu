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
import json
import posixpath
import re
import shutil
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape, unescape
from pathlib import Path
from urllib.parse import quote, urlparse

from tools.site_contract import normalize_blog_shell

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
BODY_RE = re.compile(r"<body[^>]*>(.*?)</body>", re.IGNORECASE | re.DOTALL)
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
HTML_OPEN_RE = re.compile(r"<html\b([^>]*)>", re.IGNORECASE)
ARTICLE_INDEX_RE = re.compile(
    r'(<ol[^>]*class=["\'][^"\']*article-index[^"\']*["\'][^>]*id=["\']articleIndex["\'][^>]*>)(.*?)(</ol>)',
    re.IGNORECASE | re.DOTALL,
)
FIGURE_IMAGE_RE = re.compile(
    r'<figure\b[^>]*>.*?<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE | re.DOTALL,
)
JSON_LD_RE = re.compile(
    r'(<script\b[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.IGNORECASE | re.DOTALL,
)

ARTICLE_IMAGE_BY_SLUG = {
    "agent-incident-response-runbook": "blog/assets/visuals/incident-response-flow.svg",
    "ai-policy-control-matrix": "blog/assets/visuals/policy-control-matrix.svg",
    "automotive-ai-vs-fab-ai": "blog/assets/visuals/automotive-robot-cell.svg",
    "consumer-gpu-onprem-llm-agent-lab": "blog/assets/visuals/gpu-lab-architecture.svg",
    "fab-ai-beginner-glossary": "blog/assets/visuals/fab-glossary-map.svg",
    "fab-equipment-data-101": "blog/assets/visuals/fab-equipment-data-sources.svg",
    "fdc-from-first-principles": "blog/assets/visuals/fdc-golden-run.svg",
    "lang-modules-implementation-guide": "blog/assets/visuals/lang-modules-stack.svg",
    "mock-ai-validation-low-spec-pc": "blog/assets/visuals/mock-ai-validation-loop.svg",
    "plant-rag-evaluation-harness": "blog/assets/visuals/rag-eval-scorecard.svg",
    "rag-ingestion-pipeline-manufacturing": "blog/assets/visuals/rag-ingestion-flow.svg",
    "rag-over-sealed-documents": "blog/assets/visuals/sealed-rag-boundary.svg",
    "takt-aware-ai-agents-assembly-lines": "blog/assets/visuals/takt-agent-flow.svg",
    "vin-genealogy-vs-wafer-genealogy": "blog/assets/visuals/vin-wafer-timeline.svg",
}
DEFAULT_ARTICLE_IMAGE = "blog/assets/visuals/article-visual-template.svg"

COURSE_DESCRIPTIONS = {
    "overview/index.html": "반도체와 디스플레이 공정 엔지니어를 위한 AI 입문 허브. 신경망, GPU, 가상 계측, RAG, 모델 계통도를 현장 비유로 연결합니다.",
    "overview/08_GPU_TPU_NPU.html": "GPU, TPU, NPU의 차이를 병렬 처리, 메모리, 추론 가속 관점에서 FAB 엔지니어가 이해하기 쉽게 정리한 강의 페이지입니다.",
    "overview/09_Panoptes_심화.html": "가상 계측과 Panoptes 공개 사례를 통해 공정 계측, 예측 모델, 품질 관리 흐름을 설명하는 심화 학습 페이지입니다.",
    "overview/11_AI_모델_계통도.html": "AI 모델의 40년 진화를 신경망, 트리 모델, 그래프, 생성 모델, LLM 계열로 나눠 한눈에 정리한 계통도입니다.",
    "watsonx/index.html": "폐쇄망 환경에서 사내 LLM과 지식 시스템을 구축할 때 필요한 RAG, 모델 운영, 권한, 거버넌스 개념을 정리한 마스터클래스입니다.",
    "llm_apply/LLM_slide.html": "LLM, RAG, MCP, Agent를 사내 구축 관점에서 학습하는 FAB 엔지니어용 자가학습 슬라이드입니다.",
    "llm_apply/RAG_BUILD_SLIDE.html": "BGE, Vector DB, watsonx, gpt-oss, Agent까지 이어지는 사내 RAG 구축 실전 슬라이드입니다.",
    "llm_apply/AGENT_OPS_SLIDE.html": "SOP, FDC, 이상진단, 승인 게이트를 연결해 폐쇄망 에이전트를 운영하는 방법을 다루는 실전 슬라이드입니다.",
}
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
            or (suffix in {".md", ".json"} and name != "asset_attribution.md")
        ):
            continue

        files.append(rel)
    return files


def public_mock_lab_files() -> list[str]:
    lab_root = ROOT / "labs" / "mock-ai-validation"
    allowed = {".py", ".md", ".json"}
    return [
        normalize_rel(path)
        for path in sorted(lab_root.rglob("*"))
        if path.is_file()
        and path.suffix.lower() in allowed
        and "__pycache__" not in path.parts
    ]


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
    include.extend(public_mock_lab_files())

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
    encoded = "/".join(quote(part) for part in rel.split("/"))
    return f"{SITE_URL}/{encoded}".rstrip("/") + ("/" if rel.endswith("/") else "")


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


def read_plain_text(rel: str, limit: int = 900) -> str:
    text = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
    body_match = BODY_RE.search(text)
    if body_match:
        text = body_match.group(1)
    text = SCRIPT_STYLE_RE.sub(" ", text)
    text = TAG_RE.sub(" ", text)
    text = unescape(text)
    text = text.replace("hello@ai-edu-archive.example.com", SUPPORT_EMAIL)
    for placeholder in PLACEHOLDER_URLS:
        text = text.replace(placeholder, SITE_URL)
    for placeholder in PLACEHOLDER_DOMAINS:
        text = text.replace(placeholder, SITE_HOST)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def meta_description_for(rel: str, text: str) -> str:
    rel = rel.replace("\\", "/")
    meta = read_html_meta(rel)
    description = meta.get("description") or meta.get("og:description") or COURSE_DESCRIPTIONS.get(rel, "")
    if not description:
        plain = read_plain_text(rel, limit=180)
        description = plain or "Applied AI education materials for semiconductor FAB, manufacturing AI, RAG, MCP, agents, and on-prem LLM systems."
    return re.sub(r"\s+", " ", description).strip()[:220]


def ensure_html_lang(text: str, rel: str) -> str:
    if not rel.endswith(".html"):
        return text
    lang = "ko" if rel.startswith(("overview/", "watsonx/", "llm_apply/", "blog/ko/")) else "en"

    def replace(match: re.Match[str]) -> str:
        attrs = match.group(1)
        if re.search(r"\blang\s*=", attrs, re.IGNORECASE):
            return match.group(0)
        return f'<html lang="{lang}"{attrs}>'

    return HTML_OPEN_RE.sub(replace, text, count=1)


def inject_page_metadata(text: str, rel: str) -> str:
    if not rel.endswith(".html"):
        return text

    meta = read_html_meta(rel)
    title = meta.get("title") or meta.get("h1") or "AI Edu Archive"
    description = meta_description_for(rel, text)
    canonical = public_url_for(rel)

    tags = []
    if 'rel="canonical"' not in text and "rel='canonical'" not in text:
        tags.append(f'<link rel="canonical" href="{escape(canonical)}">')
    if 'name="description"' not in text and "name='description'" not in text:
        tags.append(f'<meta name="description" content="{escape(description)}">')
    if 'property="og:type"' not in text and "property='og:type'" not in text:
        tags.append('<meta property="og:type" content="website">')
    if 'property="og:title"' not in text and "property='og:title'" not in text:
        tags.append(f'<meta property="og:title" content="{escape(title)}">')
    if 'property="og:description"' not in text and "property='og:description'" not in text:
        tags.append(f'<meta property="og:description" content="{escape(description)}">')
    if 'property="og:url"' not in text and "property='og:url'" not in text:
        tags.append(f'<meta property="og:url" content="{escape(canonical)}">')
    if 'property="og:site_name"' not in text and "property='og:site_name'" not in text:
        tags.append('<meta property="og:site_name" content="AI Edu Archive">')
    if 'name="twitter:card"' not in text and "name='twitter:card'" not in text:
        tags.append('<meta name="twitter:card" content="summary">')

    if not tags:
        return text
    return re.sub(r"</head>", "\n".join(tags) + "\n</head>", text, count=1, flags=re.IGNORECASE)


def inject_discovery_links(text: str, rel: str) -> str:
    if not rel.endswith(".html"):
        return text

    links = []
    if 'rel="manifest"' not in text and "rel='manifest'" not in text:
        links.append('<link rel="manifest" href="/site.webmanifest">')
    if 'rel="icon"' not in text and "rel='icon'" not in text:
        links.append('<link rel="icon" href="/favicon.svg" type="image/svg+xml">')
    if "application/opensearchdescription+xml" not in text:
        links.append('<link rel="search" type="application/opensearchdescription+xml" title="AI Edu Archive" href="/opensearch.xml">')
    if "application/rss+xml" not in text:
        rss_href = "/blog/ko/rss.xml" if rel.startswith("blog/ko/") else "/rss.xml"
        links.append(f'<link rel="alternate" type="application/rss+xml" title="AI Edu Archive RSS" href="{rss_href}">')

    if not links:
        return text
    return re.sub(r"</head>", "\n".join(links) + "\n</head>", text, count=1, flags=re.IGNORECASE)


def inject_category_archive_schema(text: str, rel: str) -> str:
    if not rel.endswith(".html"):
        return text
    if "category-archive" not in text or "archive-post-card" not in text:
        return text
    if "CategoryArchiveSchema" in text:
        return text

    meta = read_html_meta(rel)
    title = meta.get("title") or meta.get("h1") or "AI Edu Archive category"
    description = meta_description_for(rel, text)
    page_url = public_url_for(rel)

    item_urls = re.findall(r'<a\s+class=["\']archive-post-card["\']\s+href=["\']([^"\']+)["\']', text, re.IGNORECASE)
    item_list = []
    for position, href in enumerate(item_urls, 1):
        if href.startswith(("http://", "https://", "#", "mailto:")):
            url = href
        else:
            target = (Path(rel).parent / href.split("#", 1)[0].split("?", 1)[0]).as_posix()
            parts: list[str] = []
            for part in target.split("/"):
                if part == "..":
                    if parts:
                        parts.pop()
                elif part and part != ".":
                    parts.append(part)
            url = public_url_for("/".join(parts))
        item_list.append(
            {
                "@type": "ListItem",
                "position": position,
                "url": url,
            }
        )

    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{page_url}#CategoryArchiveSchema",
        "name": title,
        "description": description,
        "url": page_url,
        "isPartOf": {
            "@type": "WebSite",
            "name": "AI Edu Archive",
            "url": SITE_URL,
        },
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(item_list),
            "itemListElement": item_list,
        },
    }
    script = (
        '<script type="application/ld+json" id="CategoryArchiveSchema">'
        + json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )
    return re.sub(r"</head>", script + "\n</head>", text, count=1, flags=re.IGNORECASE)


def theme_script_src(rel: str) -> str:
    current_dir = posixpath.dirname(rel.replace("\\", "/")) or "."
    return posixpath.relpath("blog/assets/theme.js", current_dir)


def inject_theme_script(text: str, rel: str) -> str:
    if not rel.endswith(".html") or not rel.startswith("blog/") or "theme.js" in text:
        return text
    script = f'<script src="{theme_script_src(rel)}"></script>\n'
    return re.sub(r"</body>", script + "</body>", text, count=1, flags=re.IGNORECASE)


def article_image_url(text: str, rel: str) -> str:
    match = FIGURE_IMAGE_RE.search(text)
    image_path = ""
    if match:
        src = unescape(match.group(1)).split("#", 1)[0].split("?", 1)[0]
        if not src.startswith(("http://", "https://", "//", "data:")):
            if src.startswith("/"):
                candidate = posixpath.normpath(src.lstrip("/"))
            else:
                candidate = posixpath.normpath(posixpath.join(posixpath.dirname(rel), src))
            if not candidate.startswith("../") and (ROOT / Path(candidate)).is_file():
                image_path = candidate
    if not image_path:
        image_path = ARTICLE_IMAGE_BY_SLUG.get(Path(rel).stem, DEFAULT_ARTICLE_IMAGE)
    encoded = "/".join(quote(part) for part in image_path.split("/"))
    return f"{SITE_URL}/{encoded}"


def _replace_article_json_image(match: re.Match[str], image_url: str) -> str:
    try:
        data = json.loads(match.group(2))
    except json.JSONDecodeError:
        return match.group(0)

    changed = False

    def update(value: object) -> None:
        nonlocal changed
        if isinstance(value, dict):
            article_type = value.get("@type")
            types = article_type if isinstance(article_type, list) else [article_type]
            if "Article" in types or "BlogPosting" in types:
                value["image"] = image_url
                changed = True
            for child in value.values():
                update(child)
        elif isinstance(value, list):
            for child in value:
                update(child)

    update(data)
    if not changed:
        return match.group(0)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"{match.group(1)}{payload}{match.group(3)}"


def inject_article_image_metadata(text: str, rel: str) -> str:
    if not rel.endswith(".html") or not rel.startswith(("blog/articles/", "blog/ko/articles/")):
        return text
    image_url = article_image_url(text, rel)

    def remove_image_meta(match: re.Match[str]) -> str:
        tag = match.group(0)
        is_og = re.search(r'\bproperty\s*=\s*["\']og:image["\']', tag, re.IGNORECASE)
        is_twitter = re.search(r'\bname\s*=\s*["\']twitter:image["\']', tag, re.IGNORECASE)
        return "" if is_og or is_twitter else tag

    text = META_RE.sub(remove_image_meta, text)
    image_tags = (
        f'<meta property="og:image" content="{escape(image_url)}">\n'
        f'<meta name="twitter:image" content="{escape(image_url)}">'
    )
    text = re.sub(r"</head>", f"{image_tags}\n</head>", text, count=1, flags=re.IGNORECASE)

    updated = False

    def replace_json(match: re.Match[str]) -> str:
        nonlocal updated
        result = _replace_article_json_image(match, image_url)
        if result != match.group(0):
            updated = True
        return result

    text = JSON_LD_RE.sub(replace_json, text)
    if not updated:
        schema = json.dumps(
            {"@context": "https://schema.org", "@type": "Article", "image": image_url},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        text = re.sub(
            r"</head>",
            f'<script type="application/ld+json">{schema}</script>\n</head>',
            text,
            count=1,
            flags=re.IGNORECASE,
        )
    return text


def localize_korean_blog_ui(text: str, rel: str) -> str:
    if not rel.startswith("blog/ko/") or not rel.endswith(".html"):
        return text

    replacements = (
        ('aria-label="Table of contents"', 'aria-label="글 목차"'),
        ('<div class="toc-title">On this page</div>', '<div class="toc-title">이 글의 목차</div>'),
        ('aria-label="Related articles"', 'aria-label="관련 글"'),
        ('>Copy</button>', '>복사</button>'),
        ('>Copied!</button>', '>복사됨</button>'),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def inject_field_ai_category_link(text: str, rel: str) -> str:
    if "sidebar-children" not in text or "generative-ai-field-work.html" in text:
        return text
    is_ko = rel.startswith("blog/ko/")
    href = "generative-ai-field-work.html" if "/categories/" in rel else "categories/generative-ai-field-work.html"
    label = "생성형 AI 현장 활용" if is_ko else "Generative AI at Work"
    item = f'<li><a href="{href}"><span>{label}</span><small>2</small></a></li>'
    return re.sub(
        r'(<ul class="sidebar-children">.*?)(</ul>)',
        lambda match: match.group(1) + item + match.group(2),
        text,
        count=1,
        flags=re.DOTALL,
    )


def maybe_rewrite_text(src: Path, dst: Path, rel: str) -> None:
    text = src.read_text(encoding="utf-8")
    text = text.replace("hello@ai-edu-archive.example.com", SUPPORT_EMAIL)
    for placeholder in PLACEHOLDER_URLS:
        text = text.replace(placeholder, SITE_URL)
    for placeholder in PLACEHOLDER_DOMAINS:
        text = text.replace(placeholder, SITE_HOST)
    text = ensure_html_lang(text, rel)
    if rel.startswith("blog/") and rel.endswith(".html"):
        blog_rel = rel.removeprefix("blog/")
        blog_lang = "ko" if blog_rel.startswith("ko/") else "en"
        logical = blog_rel.removeprefix("ko/")
        pair_exists = (ROOT / "blog" / logical).is_file() and (ROOT / "blog" / "ko" / logical).is_file()
        text = normalize_blog_shell(
            text,
            blog_rel,
            blog_lang,
            site_url=SITE_URL,
            language_pair_exists=pair_exists,
        )
    text = localize_korean_blog_ui(text, rel)
    text = inject_field_ai_category_link(text, rel)
    text = inject_page_metadata(text, rel)
    text = inject_article_image_metadata(text, rel)
    text = inject_discovery_links(text, rel)
    text = inject_category_archive_schema(text, rel)
    text = inject_theme_script(text, rel)
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
        maybe_rewrite_text(src, dst, rel)
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
    if "generative ai at work" in haystack or "generative-ai-field" in haystack:
        keys.append("fieldai")
    if "on-prem" in haystack or "onprem" in haystack or "air-gapped" in haystack:
        keys.append("onprem")
    if "rag" in haystack or "retrieval" in haystack or "embedding" in haystack or "chunk" in haystack:
        keys.append("rag")
    if "agent" in haystack or "mcp" in haystack or "langgraph" in haystack:
        keys.append("agents")
    if "automotive" in haystack or "robot cell" in haystack or "vin genealogy" in haystack or "takt" in haystack:
        keys.append("auto")
    if "python" in haystack or "langchain" in haystack or "langgraph" in haystack or "module" in haystack:
        keys.append("python")
    if "manufacturing" in haystack or "fab" in haystack or "process" in haystack or "mes" in haystack:
        keys.append("mfg")
    return " ".join(dict.fromkeys(keys)) or "python"


def category_label(section: str, data_cat: str, lang: str) -> str:
    if section:
        if section == "Automotive AI & Robotics" and lang == "ko":
            return "자동차 AI & 로봇"
        if lang == "ko":
            labels = {
                "Generative AI at Work": "생성형 AI 현장 활용",
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
        "fieldai": "Generative AI at Work",
        "onprem": "On-Prem LLM",
        "rag": "RAG",
        "agents": "Agents & MCP",
        "auto": "Automotive AI & Robotics",
        "python": "Python Stack",
        "mfg": "Manufacturing AI",
    }
    labels_ko = {
        "fieldai": "생성형 AI 현장 활용",
        "onprem": "온프레미스 LLM",
        "rag": "RAG",
        "agents": "Agent & MCP",
        "auto": "자동차 AI & 로봇",
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
    raw = meta.get("title") or meta.get("og:title") or meta.get("h1") or Path(rel).stem
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
    for record in records:
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
        f"- Learning Paths: {SITE_URL}/blog/learning-paths.html",
        f"- Korean Learning Paths: {SITE_URL}/blog/ko/learning-paths.html",
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


def generate_search_json(public_files: list[str]) -> int:
    searchable = []
    for rel in public_files:
        if not rel.endswith(".html"):
            continue
        if "backup" in Path(rel).name.lower():
            continue

        meta = read_html_meta(rel)
        lang = "ko" if rel.startswith(("overview/", "watsonx/", "llm_apply/", "blog/ko/")) else "en"
        page_type = "article" if "/articles/" in rel else "page"
        title = title_for_index(meta, rel)
        description = meta.get("description") or meta.get("og:description") or meta_description_for(rel, "")
        section = meta.get("article:section") or ""

        searchable.append(
            {
                "title": title,
                "description": description,
                "url": public_url_for(rel),
                "path": rel,
                "language": lang,
                "type": page_type,
                "section": section,
                "published": meta.get("article:published_time") or "",
                "text": read_plain_text(rel),
            }
        )

    searchable.sort(key=lambda item: (item["type"] != "article", item["language"], item["title"].lower()))
    text = json.dumps(
        {
            "site": "AI Edu Archive",
            "siteUrl": SITE_URL,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "documents": searchable,
        },
        ensure_ascii=False,
        indent=2,
    )
    path = DIST / "search.json"
    path.write_text(text + "\n", encoding="utf-8")
    return path.stat().st_size


def generate_content_audit(public_files: list[str]) -> int:
    en_articles = article_records(public_files, "en")
    ko_articles = article_records(public_files, "ko")
    html_files = [rel for rel in public_files if rel.endswith(".html")]

    article_paths = [record["path"] for record in en_articles + ko_articles]
    missing_descriptions = [record["path"] for record in en_articles + ko_articles if not record["description"]]
    missing_published = [
        rel
        for rel in article_paths
        if not read_html_meta(rel).get("article:published_time")
    ]

    en_slugs = {Path(record["path"]).name for record in en_articles}
    ko_slugs = {Path(record["path"]).name for record in ko_articles}
    section_names = {
        "fieldai": "Generative AI at Work",
        "agents": "Agents & MCP",
        "mfg": "Manufacturing AI",
        "onprem": "On-Prem LLM",
        "python": "Python Stack",
        "rag": "RAG",
    }
    sections: dict[str, int] = {}
    for record in en_articles + ko_articles:
        normalized = category_key(record["section"], record["path"], record["title"]).split()[0]
        key = section_names.get(normalized, "Uncategorized")
        sections[key] = sections.get(key, 0) + 1

    payload = {
        "site": "AI Edu Archive",
        "siteUrl": SITE_URL,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "files": len(public_files),
            "html": len(html_files),
            "articles": len(en_articles) + len(ko_articles),
            "englishArticles": len(en_articles),
            "koreanArticles": len(ko_articles),
        },
        "sections": dict(sorted(sections.items())),
        "translationPairs": {
            "paired": len(en_slugs & ko_slugs),
            "englishOnly": sorted(en_slugs - ko_slugs),
            "koreanOnly": sorted(ko_slugs - en_slugs),
        },
        "metadataGaps": {
            "missingDescriptions": sorted(missing_descriptions),
            "missingPublishedTime": sorted(missing_published),
        },
    }

    path = DIST / "content-audit.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.stat().st_size


def generate_webmanifest() -> int:
    manifest = {
        "name": "AI Edu Archive",
        "short_name": "AI Edu",
        "description": "Applied AI, robotics AI, manufacturing AI, on-prem LLM, RAG, MCP, and agent systems.",
        "start_url": "/",
        "scope": "/",
        "display": "minimal-ui",
        "background_color": "#FAF9F5",
        "theme_color": "#FAF9F5",
        "lang": "en",
        "categories": ["education", "productivity", "technology"],
        "icons": [
            {
                "src": "/favicon.svg",
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any maskable",
            }
        ],
    }
    path = DIST / "site.webmanifest"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.stat().st_size


def generate_favicon() -> int:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#111827"/>
<path d="M14 44 28 12h8l14 32h-8l-3-8H25l-3 8h-8Zm14-15h8l-4-10-4 10Z" fill="#f9fafb"/>
<circle cx="48" cy="16" r="5" fill="#22c55e"/>
</svg>
"""
    path = DIST / "favicon.svg"
    path.write_text(svg, encoding="utf-8")
    return path.stat().st_size


def generate_opensearch() -> int:
    text = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">\n'
        "  <ShortName>AI Edu Archive</ShortName>\n"
        "  <Description>Search AI Edu Archive articles and courses.</Description>\n"
        '  <InputEncoding>UTF-8</InputEncoding>\n'
        f'  <Url type="text/html" template="{escape(SITE_URL)}/blog/search.html?q={{searchTerms}}"/>\n'
        f'  <Url type="application/json" template="{escape(SITE_URL)}/search.json"/>\n'
        "</OpenSearchDescription>\n"
    )
    path = DIST / "opensearch.xml"
    path.write_text(text, encoding="utf-8")
    return path.stat().st_size


def generate_404(public_files: list[str]) -> int:
    recent = article_records(public_files, "en")[:5]
    recent_links = "\n".join(
        f'<li><a href="{escape(record["url"])}">{escape(record["title"])}</a></li>' for record in recent
    )
    text = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,follow">
<title>Page not found - AI Edu Archive</title>
<link rel="stylesheet" href="/blog/assets/blog.css">
<link rel="manifest" href="/site.webmanifest">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="search" type="application/opensearchdescription+xml" title="AI Edu Archive" href="/opensearch.xml">
<link rel="alternate" type="application/rss+xml" title="AI Edu Archive RSS" href="/rss.xml">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="nav" id="nav">
  <div class="wrap">
    <a class="brand" href="/" aria-label="AI Edu Archive home"><span class="brand-name">AI Edu <em>Archive</em></span></a>
    <nav class="nav-links" aria-label="Primary">
      <a href="/#courses">Courses</a>
      <a href="/blog/">Articles</a>
      <a href="/blog/search.html">Search</a>
      <a href="/blog/portfolio.html">Portfolio</a>
      <a href="/blog/about.html">About</a>
    </nav>
  </div>
</header>
<main id="main">
  <section class="page-head">
    <div class="wrap">
      <span class="eyebrow">404</span>
      <h1>This page moved, or never existed.</h1>
      <p class="lede">Try the archive search, return to the hub, or start with a recent article.</p>
      <div class="hero-cta" style="margin-top:30px">
        <a class="btn btn-primary" href="/blog/search.html">Search the archive</a>
        <a class="btn btn-ghost" href="/">Go home</a>
      </div>
    </div>
  </section>
  <section class="section">
    <div class="wrap">
      <div class="prose">
        <h2>Recent articles</h2>
        <ul>
          {recent_links}
        </ul>
      </div>
    </div>
  </section>
</main>
</body>
</html>
"""
    path = DIST / "404.html"
    path.write_text(text, encoding="utf-8")
    return path.stat().st_size


def generate_redirects() -> int:
    text = (
        "/journal /blog/ 301\n"
        "/articles/* /blog/articles/:splat 301\n"
        "/ko/articles/* /blog/ko/articles/:splat 301\n"
        "/search /blog/search.html 301\n"
        "/feed.xml /rss.xml 301\n"
        "/rss /rss.xml 301\n"
        "/ko/rss.xml /blog/ko/rss.xml 301\n"
    )
    path = DIST / "_redirects"
    path.write_text(text, encoding="utf-8")
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
        "/search.json\n"
        "  Content-Type: application/json; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
        "\n"
        "/content-audit.json\n"
        "  Content-Type: application/json; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
        "\n"
        "/site.webmanifest\n"
        "  Content-Type: application/manifest+json; charset=utf-8\n"
        "  Cache-Control: public, max-age=3600\n"
        "\n"
        "/favicon.svg\n"
        "  Content-Type: image/svg+xml; charset=utf-8\n"
        "  Cache-Control: public, max-age=31536000, immutable\n"
        "\n"
        "/opensearch.xml\n"
        "  Content-Type: application/opensearchdescription+xml; charset=utf-8\n"
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
        ("search.json", generate_search_json(include)),
        ("content-audit.json", generate_content_audit(include)),
        ("site.webmanifest", generate_webmanifest()),
        ("favicon.svg", generate_favicon()),
        ("opensearch.xml", generate_opensearch()),
        ("404.html", generate_404(include)),
        ("_redirects", generate_redirects()),
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
