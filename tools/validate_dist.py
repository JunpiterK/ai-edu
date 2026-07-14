#!/usr/bin/env python
"""Validate the generated dist/ folder before deployment."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

PLACEHOLDER_PATTERNS = (
    "ai-edu.example",
    "ai-edu-archive.example.com",
    "hello@ai-edu-archive.example.com",
)

QUALITY_RISK_PATTERNS = (
    "advertisement placeholder",
    "In-feed ad slot",
    "version will be added later",
    "This document is a general template",
    "Replace <strong>AI Edu Archive</strong>",
    "�",
    "쨌",
    "占?",
    "夷?",
    "移댄뀒",
    "먮룞",
    "蹂몃Ц",
    "怨좊━",
    "紐⑸",
    "湲",
    "濡쒕",
    "LCEL 파이프 리소스도",
    "인싱은 한 번",
    "오직 해 표면에만 답합니다",
    "싸워야 할 수록 VRAM",
    "공극을 가로질러 단방향",
)

REQUIRED_AI_CATEGORY_PAGES = (
    "blog/ai-categories.html",
    "blog/ko/ai-categories.html",
    "blog/categories/automotive-ai-robotics.html",
    "blog/categories/fab-ai-foundations.html",
    "blog/categories/rag-knowledge-systems.html",
    "blog/categories/agents-mcp-controls.html",
    "blog/categories/onprem-llm-operations.html",
    "blog/categories/python-langchain-langgraph.html",
    "blog/categories/generative-ai-field-work.html",
    "blog/ko/categories/automotive-ai-robotics.html",
    "blog/ko/categories/fab-ai-foundations.html",
    "blog/ko/categories/rag-knowledge-systems.html",
    "blog/ko/categories/agents-mcp-controls.html",
    "blog/ko/categories/onprem-llm-operations.html",
    "blog/ko/categories/python-langchain-langgraph.html",
    "blog/ko/categories/generative-ai-field-work.html",
)

REQUIRED_JOURNAL_HOME_PAGES = (
    "blog/index.html",
    "blog/ko/index.html",
)

REQUIRED_HUB_VOICE_PAGES = (
    "blog/ai-categories.html",
    "blog/ko/ai-categories.html",
    "blog/automotive-ai-robotics.html",
    "blog/ko/automotive-ai-robotics.html",
    "blog/learning-paths.html",
    "blog/ko/learning-paths.html",
    "blog/portfolio.html",
    "blog/ko/portfolio.html",
    "blog/about.html",
    "blog/ko/about.html",
    "blog/categories/agents-mcp-controls.html",
    "blog/categories/automotive-ai-robotics.html",
    "blog/categories/fab-ai-foundations.html",
    "blog/categories/onprem-llm-operations.html",
    "blog/categories/python-langchain-langgraph.html",
    "blog/categories/rag-knowledge-systems.html",
    "blog/ko/categories/agents-mcp-controls.html",
    "blog/ko/categories/automotive-ai-robotics.html",
    "blog/ko/categories/fab-ai-foundations.html",
    "blog/ko/categories/onprem-llm-operations.html",
    "blog/ko/categories/python-langchain-langgraph.html",
    "blog/ko/categories/rag-knowledge-systems.html",
)

LOCAL_LINK_RE = re.compile(r"""(?:href|src)=["']([^"']+)["']""", re.IGNORECASE)
HTML_LANG_RE = re.compile(r"<html\b[^>]*\blang\s*=", re.IGNORECASE)
HTML_LANG_VALUE_RE = re.compile(r"<html\b[^>]*\blang\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
HEADER_RE = re.compile(r"<header\b[^>]*class=[\"'][^\"']*\bnav\b[^\"']*[\"'][^>]*>.*?</header>", re.IGNORECASE | re.DOTALL)
FOOTER_RE = re.compile(r"<footer\b[^>]*class=[\"'][^\"']*\bsite-foot\b[^\"']*[\"'][^>]*>.*?</footer>", re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(r"<title>.+?</title>", re.IGNORECASE | re.DOTALL)
FIGURE_RE = re.compile(r"<figure\b(?P<attrs>[^>]*)>(?P<body>.*?)</figure>", re.IGNORECASE | re.DOTALL)
IMG_RE = re.compile(r"<img\b(?P<attrs>[^>]*)>", re.IGNORECASE)
IMG_SRC_RE = re.compile(r"\bsrc\s*=\s*[\"'](?P<src>[^\"']+)[\"']", re.IGNORECASE)
IMG_ALT_RE = re.compile(r"\balt\s*=\s*[\"'](?P<alt>[^\"']*)[\"']", re.IGNORECASE)
REMOTE_IMG_RE = re.compile(r"<img\b[^>]*\bsrc=[\"'](?P<src>https?://[^\"']+|//[^\"']+)[\"']", re.IGNORECASE)
EMPTY_SHARE_URL_RE = re.compile(
    r"https?://(?:twitter\.com/intent/tweet|www\.linkedin\.com/sharing/share-offsite/)\?[^\"']*\burl=(?:[&\"']|$)",
    re.IGNORECASE,
)
KOREAN_MOJIBAKE_RE = re.compile(r"[\uFFFD]|[李吏紐硫留泥戮理]|[蹂媛瑜댄湲곗諛怨洹몃遺]")
EXPOSED_EDITORIAL_MARKER_RE = re.compile(
    r"(?im)^\s*(?:HTML|[∨=\s\u200b]*SEO[\s=\u200b]*|오픈 그래프|JSON-LD:\s*기사 스키마|"
    r"심층적인 데크 링크|공유|저자 바이오 카드(?:\(E-E-A-T\))?|관련된|===\s*\d+[a-z]?[^<]*)\s*$"
)
JSON_LD_RE = re.compile(r"<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(?P<body>.*?)</script>", re.IGNORECASE | re.DOTALL)
HANGUL_RE = re.compile(r"[가-힣]")
ENGLISH_HANGUL_EXEMPTIONS = {
    "blog/articles/consumer-gpu-onprem-llm-agent-lab.html",
    "blog/articles/embeddings-korean-technical.html",
    "blog/articles/rag-over-sealed-documents.html",
}
SKIP_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "data:",
    "javascript:",
    "#",
)


def dist_files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def check_required_files(root: Path) -> list[str]:
    missing = []
    for rel in (
        "index.html",
        "sitemap.xml",
        "robots.txt",
        "rss.xml",
        "blog/ko/rss.xml",
        "llms.txt",
        "search.json",
        "content-audit.json",
        "site.webmanifest",
        "favicon.svg",
        "opensearch.xml",
        "404.html",
        "_redirects",
        "blog/articles.json",
        "blog/ko/articles.json",
        "blog/assets/theme.js",
        "_headers",
    ):
        if not (root / rel).is_file():
            missing.append(rel)
    return missing


def check_placeholders(root: Path) -> list[str]:
    hits = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".json", ".xml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern in text:
                hits.append(f"{path.relative_to(root).as_posix()}: contains {pattern}")
    return hits


def check_quality_risk_patterns(root: Path) -> list[str]:
    hits = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".json", ".xml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in QUALITY_RISK_PATTERNS:
            if pattern in text:
                hits.append(f"{path.relative_to(root).as_posix()}: quality risk pattern {pattern!r}")
        rel = path.relative_to(root).as_posix()
        if rel.startswith("blog/ko/") and KOREAN_MOJIBAKE_RE.search(text):
            hits.append(f"{rel}: likely Korean mojibake")
    return hits


def check_language_separation(root: Path) -> list[str]:
    errors = []
    for html in root.glob("blog/**/*.html"):
        rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        if rel.startswith("blog/ko/"):
            for pattern in (
                '<div class="toc-title">On this page</div>',
                '>Copy</button>',
                'aria-label="Table of contents"',
                'aria-label="Related articles"',
            ):
                if pattern in text:
                    errors.append(f"{rel}: Korean page contains untranslated UI text: {pattern}")
        elif rel.startswith("blog/articles/") and rel not in ENGLISH_HANGUL_EXEMPTIONS:
            normalized = text.replace('title="한국어"', "")
            hangul_count = len(HANGUL_RE.findall(normalized))
            if hangul_count > 5:
                errors.append(f"{rel}: English article contains {hangul_count} Hangul characters outside an approved bilingual example")
    return errors


def check_blog_contract(root: Path) -> list[str]:
    """Enforce the shared bilingual shell and one-to-one content contract."""
    errors = []
    article_sets = {}

    for lang, folder in (("en", root / "blog/articles"), ("ko", root / "blog/ko/articles")):
        article_sets[lang] = {path.name for path in folder.glob("*.html") if "backup" not in path.name.lower()}
    if article_sets["en"] != article_sets["ko"]:
        missing_ko = sorted(article_sets["en"] - article_sets["ko"])
        missing_en = sorted(article_sets["ko"] - article_sets["en"])
        if missing_ko:
            errors.append(f"Korean article mirrors missing: {', '.join(missing_ko)}")
        if missing_en:
            errors.append(f"English article mirrors missing: {', '.join(missing_en)}")

    for html in root.glob("blog/**/*.html"):
        rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        expected_lang = "ko" if rel.startswith("blog/ko/") else "en"
        lang_match = HTML_LANG_VALUE_RE.search(text)
        actual_lang = lang_match.group(1).lower() if lang_match else ""
        if actual_lang != expected_lang:
            errors.append(f"{rel}: html lang must be {expected_lang!r}, found {actual_lang!r}")

        header_match = HEADER_RE.search(text)
        if not header_match:
            errors.append(f"{rel}: missing canonical nav header")
        else:
            header = header_match.group(0)
            if "language-switch" not in header:
                errors.append(f"{rel}: header missing language switch")
            forbidden = (
                (">Courses<", ">Articles<", ">Learning Paths<", ">Search<", ">Portfolio<", ">About<")
                if expected_lang == "ko"
                else (">강의<", ">글<", ">학습 경로<", ">검색<", ">포트폴리오<", ">소개<")
            )
            for token in forbidden:
                if token in header:
                    errors.append(f"{rel}: untranslated header UI token {token}")

        if not FOOTER_RE.search(text):
            errors.append(f"{rel}: missing canonical site footer")

        if "/articles/" in rel:
            if not re.match(r"^\s*<!doctype html>", text, re.IGNORECASE):
                errors.append(f"{rel}: article must begin with <!DOCTYPE html>")
            exposed_marker = EXPOSED_EDITORIAL_MARKER_RE.search(text)
            if exposed_marker:
                errors.append(
                    f"{rel}: exposed editorial marker must be an HTML comment: "
                    f"{exposed_marker.group(0).strip()}"
                )
            for hreflang in ("en", "ko", "x-default"):
                if not re.search(rf'<link\b[^>]*hreflang=[\"\']{re.escape(hreflang)}[\"\']', text, re.IGNORECASE):
                    errors.append(f"{rel}: missing hreflang {hreflang}")
            if 'name="twitter:card" content="summary_large_image"' in text:
                if not re.search(r'<meta\b[^>]*property=["\']og:image["\'][^>]*content=["\'][^"\']+["\']', text, re.IGNORECASE):
                    errors.append(f"{rel}: summary_large_image requires og:image")
                if not re.search(r'<meta\b[^>]*name=["\']twitter:image["\'][^>]*content=["\'][^"\']+["\']', text, re.IGNORECASE):
                    errors.append(f"{rel}: summary_large_image requires twitter:image")

    for category in sorted((root / "blog/categories").glob("*.html")):
        ko_category = root / "blog/ko/categories" / category.name
        if not ko_category.is_file():
            errors.append(f"missing Korean category mirror: {category.name}")
            continue
        en_text = category.read_text(encoding="utf-8", errors="ignore")
        ko_text = ko_category.read_text(encoding="utf-8", errors="ignore")
        pattern = re.compile(r'class=[\"\']archive-post-card[\"\'][^>]*href=[\"\'][^\"\']*/([^/\"\']+\.html)', re.IGNORECASE)
        en_posts = pattern.findall(en_text)
        ko_posts = pattern.findall(ko_text)
        if en_posts != ko_posts:
            errors.append(f"category article order differs between EN/KO: {category.name}")

    return errors


def check_interactive_learning_labs(root: Path) -> list[str]:
    """Keep premium worked examples present in both language editions."""
    required = {
        "blog/articles/fdc-from-first-principles.html": "data-fdc-sim",
        "blog/ko/articles/fdc-from-first-principles.html": "data-fdc-sim",
        "blog/articles/plant-rag-evaluation-harness.html": "data-rag-eval-sim",
        "blog/ko/articles/plant-rag-evaluation-harness.html": "data-rag-eval-sim",
        "blog/articles/takt-aware-ai-agents-assembly-lines.html": "data-takt-sim",
        "blog/ko/articles/takt-aware-ai-agents-assembly-lines.html": "data-takt-sim",
    }
    errors = []
    for rel, marker in required.items():
        path = root / rel
        if not path.exists():
            errors.append(f"interactive lab page missing: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if marker not in text:
            errors.append(f"interactive lab marker missing in {rel}: {marker}")
        if "interactive-labs.js" not in text:
            errors.append(f"interactive lab script missing in {rel}")
    return errors


def check_remote_images(root: Path) -> list[str]:
    errors = []
    for html in root.rglob("*.html"):
        rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        for match in REMOTE_IMG_RE.finditer(text):
            errors.append(f"{rel}: remote image is fragile; use a local asset instead: {match.group('src')}")
    return errors


def check_share_links(root: Path) -> list[str]:
    """Reject visible social-share controls that do not identify a page."""
    errors = []
    for html in root.rglob("*.html"):
        rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        if EMPTY_SHARE_URL_RE.search(text):
            errors.append(f"{rel}: social share link has an empty url parameter")
    return errors


def check_photo_attribution(root: Path) -> list[str]:
    errors = []
    photos_root = root / "blog/assets/photos"
    attribution_path = root / "blog/assets/ASSET_ATTRIBUTION.md"
    photo_files = sorted(path for path in photos_root.rglob("*") if path.is_file()) if photos_root.is_dir() else []

    if photo_files and not attribution_path.is_file():
        return ["blog/assets/ASSET_ATTRIBUTION.md is required when local third-party photos are published"]

    attribution = attribution_path.read_text(encoding="utf-8", errors="ignore") if attribution_path.is_file() else ""
    for photo in photo_files:
        rel_photo = photo.relative_to(root / "blog/assets").as_posix()
        if rel_photo not in attribution:
            errors.append(f"blog/assets/{rel_photo}: missing entry in ASSET_ATTRIBUTION.md")

    used_photos: dict[str, list[str]] = {}
    for html in root.glob("blog/**/*.html"):
        rel_html = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        for figure in FIGURE_RE.finditer(text):
            body = figure.group("body")
            for image in IMG_RE.finditer(body):
                src_match = IMG_SRC_RE.search(image.group("attrs"))
                if not src_match or "assets/photos/" not in src_match.group("src"):
                    continue
                target = local_target(root, html, src_match.group("src"))
                if not target:
                    continue
                used_photos.setdefault(target, []).append(rel_html)
                caption = re.search(r"<figcaption\b[^>]*>(.*?)</figcaption>", body, re.IGNORECASE | re.DOTALL)
                caption_text = caption.group(1) if caption else ""
                if not re.search(r"wikimedia|source|photo:|사진:|출처|license|라이선스", caption_text, re.IGNORECASE):
                    errors.append(f"{rel_html}: local third-party photo needs source/license text in its figcaption")

    for photo in photo_files:
        target = photo.relative_to(root).as_posix()
        if target not in used_photos:
            errors.append(f"{target}: published photo is not used by any HTML figure")

    return errors


def check_structured_data_images(root: Path) -> list[str]:
    errors = []
    for html in root.rglob("*.html"):
        rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        for match in JSON_LD_RE.finditer(text):
            try:
                data = json.loads(match.group("body"))
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict) or "image" not in item:
                    continue
                images = item["image"] if isinstance(item["image"], list) else [item["image"]]
                for image in images:
                    if not isinstance(image, str):
                        continue
                    parsed = urlsplit(image)
                    if parsed.scheme in {"http", "https"}:
                        path = unquote(parsed.path).lstrip("/")
                        if parsed.netloc and path.startswith("blog/") and not (root / path).is_file():
                            errors.append(f"{rel}: JSON-LD image target missing in dist: {image}")
                    elif image and not image.startswith("data:"):
                        target = local_target(root, html, image)
                        if target and not (root / target).is_file():
                            errors.append(f"{rel}: JSON-LD image target missing in dist: {image}")
    return errors


def local_target(root: Path, source: Path, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(SKIP_PREFIXES):
        return None

    parsed = urlsplit(href)
    path = unquote(parsed.path)
    if not path or path.startswith(SKIP_PREFIXES) or path.startswith("//"):
        return None

    target_path = root / path.lstrip("/") if path.startswith("/") else source.parent / path
    try:
        target = target_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return "outside dist"

    if target in ("", "."):
        return "index.html"
    if target.endswith("/"):
        return f"{target}index.html"
    if (root / target).is_dir():
        return f"{target}/index.html"
    return target


def check_local_links(root: Path) -> list[str]:
    files = dist_files(root)
    missing = []
    for html in root.rglob("*.html"):
        source_rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        for href in LOCAL_LINK_RE.findall(text):
            target = local_target(root, html, href)
            if target and target not in files:
                missing.append(f"{source_rel}: {href} -> {target}")
    return missing


def redirect_target_exists(root: Path, target: str) -> bool:
    parsed = urlsplit(target)
    path = unquote(parsed.path)
    if not path or path.startswith(("http://", "https://", "//")):
        return True

    if ":splat" in path:
        parent = path.split(":splat", 1)[0].rstrip("/")
        return (root / parent.lstrip("/")).is_dir()

    target_path = root / path.lstrip("/")
    if path.endswith("/"):
        return (target_path / "index.html").is_file()
    if target_path.is_dir():
        return (target_path / "index.html").is_file()
    return target_path.is_file()


def check_redirects(root: Path) -> list[str]:
    errors = []
    redirects_path = root / "_redirects"
    if not redirects_path.is_file():
        return ["_redirects is missing"]

    for line_no, raw_line in enumerate(redirects_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) < 2:
            errors.append(f"_redirects:{line_no} has fewer than source and target columns")
            continue

        source, target = parts[0], parts[1]
        status = parts[2] if len(parts) >= 3 else ""

        if not source.startswith("/"):
            errors.append(f"_redirects:{line_no} source must start with /")
        if not (target.startswith("/") or target.startswith(("http://", "https://"))):
            errors.append(f"_redirects:{line_no} target must be absolute path or URL")
        if status and not re.fullmatch(r"[1234]\d\d", status):
            errors.append(f"_redirects:{line_no} invalid status code {status}")
        if target.startswith("/") and not redirect_target_exists(root, target):
            errors.append(f"_redirects:{line_no} target does not exist: {target}")

    return errors


def check_generated_data(root: Path) -> list[str]:
    errors = []

    try:
        sitemap = ElementTree.parse(root / "sitemap.xml")
        urls = sitemap.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        if not urls:
            errors.append("sitemap.xml has no <url> entries")
        for idx, url in enumerate(urls):
            loc = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            loc_text = (loc.text or "").strip() if loc is not None else ""
            if not loc_text:
                errors.append(f"sitemap.xml url {idx} missing <loc>")
                continue
            parsed = urlsplit(loc_text)
            if " " in loc_text:
                errors.append(f"sitemap.xml loc contains a raw space: {loc_text}")
            try:
                parsed.path.encode("ascii")
            except UnicodeEncodeError:
                errors.append(f"sitemap.xml loc path is not percent-encoded: {loc_text}")
    except Exception as exc:  # noqa: BLE001 - validator should report parse failures plainly.
        errors.append(f"sitemap.xml parse error: {exc}")

    for rss_rel in ("rss.xml", "blog/ko/rss.xml"):
        try:
            rss = ElementTree.parse(root / rss_rel)
            items = rss.findall("./channel/item")
            if not items:
                errors.append(f"{rss_rel} has no <item> entries")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{rss_rel} parse error: {exc}")

    try:
        opensearch = ElementTree.parse(root / "opensearch.xml")
        if opensearch.getroot().tag.split("}")[-1] != "OpenSearchDescription":
            errors.append("opensearch.xml root is not OpenSearchDescription")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"opensearch.xml parse error: {exc}")

    for json_rel in (
        "blog/articles.json",
        "blog/ko/articles.json",
        "search.json",
        "content-audit.json",
        "site.webmanifest",
    ):
        try:
            data = json.loads((root / json_rel).read_text(encoding="utf-8"))
            if json_rel.endswith("articles.json"):
                articles = data.get("articles", [])
                if not articles:
                    errors.append(f"{json_rel} has no articles")
                for idx, article in enumerate(articles):
                    for key in ("title", "description", "url", "path", "published"):
                        if not article.get(key):
                            errors.append(f"{json_rel} article {idx} missing {key}")
            elif json_rel == "search.json":
                documents = data.get("documents", [])
                if not documents:
                    errors.append("search.json has no documents")
                for idx, document in enumerate(documents):
                    for key in ("title", "url", "path", "language", "type", "text"):
                        if not document.get(key):
                            errors.append(f"search.json document {idx} missing {key}")
            elif json_rel == "content-audit.json":
                totals = data.get("totals", {})
                if not totals.get("html"):
                    errors.append("content-audit.json totals.html is empty")
                if not totals.get("articles"):
                    errors.append("content-audit.json totals.articles is empty")
                if "translationPairs" not in data:
                    errors.append("content-audit.json missing translationPairs")
                if "metadataGaps" not in data:
                    errors.append("content-audit.json missing metadataGaps")
            elif json_rel == "site.webmanifest":
                for key in ("name", "short_name", "start_url", "display", "theme_color"):
                    if not data.get(key):
                        errors.append(f"site.webmanifest missing {key}")
                icons = data.get("icons", [])
                if not icons:
                    errors.append("site.webmanifest missing icons")
                for idx, icon in enumerate(icons):
                    src = icon.get("src", "")
                    if not src:
                        errors.append(f"site.webmanifest icon {idx} missing src")
                    elif src.startswith("/") and not (root / src.lstrip("/")).is_file():
                        errors.append(f"site.webmanifest icon {idx} target missing: {src}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{json_rel} parse error: {exc}")

    try:
        favicon = ElementTree.parse(root / "favicon.svg")
        if favicon.getroot().tag.split("}")[-1] != "svg":
            errors.append("favicon.svg root is not svg")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"favicon.svg parse error: {exc}")

    return errors


def check_static_hardening(root: Path) -> list[str]:
    errors = []

    search_page = root / "blog/search.html"
    if search_page.is_file():
        search_text = search_page.read_text(encoding="utf-8", errors="ignore")
        if ".innerHTML" in search_text or "innerHTML=" in search_text:
            errors.append("blog/search.html uses innerHTML; render search results with DOM text nodes")

    llms_path = root / "llms.txt"
    if llms_path.is_file():
        llms_text = llms_path.read_text(encoding="utf-8", errors="ignore")
        for required in ("blog/learning-paths.html", "blog/ko/learning-paths.html"):
            if required not in llms_text:
                errors.append(f"llms.txt missing core page: {required}")

    return errors


def check_theme_support(root: Path) -> list[str]:
    errors = []
    css_path = root / "blog/assets/blog.css"
    js_path = root / "blog/assets/theme.js"

    if not css_path.is_file():
        return ["blog/assets/blog.css is missing"]
    if not js_path.is_file():
        return ["blog/assets/theme.js is missing"]

    css_text = css_path.read_text(encoding="utf-8", errors="ignore")
    js_text = js_path.read_text(encoding="utf-8", errors="ignore")
    for token in (
        ':root[data-theme="dark"]',
        "--paper:#08131E",
        "--accent-warm:#D96B57",
        ".theme-toggle",
        ".theme-toggle-knob",
    ):
        if token not in css_text:
            errors.append(f"blog/assets/blog.css missing theme token: {token}")
    for token in ("data-theme-toggle", "localStorage", "prefers-color-scheme", "setAttribute('data-theme'"):
        if token not in js_text:
            errors.append(f"blog/assets/theme.js missing behavior token: {token}")

    for html in root.glob("blog/**/*.html"):
        rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        if "theme.js" not in text:
            errors.append(f"{rel} missing theme toggle script")

    return errors


def check_media_figures(root: Path) -> list[str]:
    errors = []
    for html in list((root / "blog/articles").glob("*.html")) + list((root / "blog/ko/articles").glob("*.html")):
        rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        non_code_figures = []
        for figure in FIGURE_RE.finditer(text):
            attrs = figure.group("attrs")
            body = figure.group("body")
            if "code-figure" in attrs:
                continue
            non_code_figures.append(figure)
            if "<figcaption" not in body.lower():
                errors.append(f"{rel} has a non-code figure without figcaption")

        if not non_code_figures:
            errors.append(f"{rel} must include at least one non-code visual figure")

        for image in IMG_RE.finditer(text):
            attrs = image.group("attrs")
            alt_match = IMG_ALT_RE.search(attrs)
            if not alt_match:
                errors.append(f"{rel} has an image without alt text")
            elif not alt_match.group("alt").strip():
                errors.append(f"{rel} has an image with empty alt text")
            if "article-body" in text[: image.start()] and not re.search(r"\bloading\s*=\s*[\"']lazy[\"']", attrs, re.IGNORECASE):
                errors.append(f"{rel} article image should use loading=\"lazy\"")

    return errors


def check_human_voice(root: Path) -> list[str]:
    errors = []
    for html in list((root / "blog/articles").glob("*.html")) + list((root / "blog/ko/articles").glob("*.html")):
        rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        voice_markers = (
            "field-story", "field-note", "sim-badge", "Illustrative scenario",
            "Illustrative fab example", "Threat and control matrix", "Minimum evidence attached",
        )
        if not any(marker in text for marker in voice_markers):
            errors.append(f"{rel} missing a concrete engineering scenario or field note")
        takeaway_markers = (
            "reader-shortcut", "takeaway-note", "field-note", "field-story", "sim-note",
            "<blockquote>", "Common misconception",
        )
        if not any(marker in text for marker in takeaway_markers):
            errors.append(f"{rel} missing a concrete reader takeaway")
    for rel in REQUIRED_HUB_VOICE_PAGES:
        path = root / rel
        if not path.is_file():
            errors.append(f"missing hub voice page: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "hub-voice" not in text:
            errors.append(f"{rel} missing hub-voice field-practice note")
    return errors


def check_ai_category_archives(root: Path) -> list[str]:
    errors = []
    required_classes = (
        "category-archive",
        "archive-layout",
        "archive-post-list",
        "archive-post-card",
        "archive-sidebar",
        "sidebar-children",
        "reading-order",
    )

    for rel in REQUIRED_AI_CATEGORY_PAGES:
        path = root / rel
        if not path.is_file():
            errors.append(f"missing AI category archive page: {rel}")
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        for class_name in required_classes:
            if class_name not in text:
                errors.append(f"{rel} missing category archive class: {class_name}")

        if '<a class="article-card"' in text or "article-card-grid" in text:
            errors.append(f"{rel} regressed to legacy card-grid category layout")
        if 'aria-current="page"' not in text:
            errors.append(f"{rel} missing current category marker")
        minimum_rows = 1 if "generative-ai-field-work.html" in rel else 3
        if text.count('class="archive-post-card"') < minimum_rows:
            errors.append(f"{rel} has too few archive post rows")
        if 'id="CategoryArchiveSchema"' not in text or '"@type":"CollectionPage"' not in text:
            errors.append(f"{rel} missing CollectionPage JSON-LD")

    return errors


def check_journal_home_layout(root: Path) -> list[str]:
    errors = []
    css_path = root / "blog/assets/blog.css"
    css_text = css_path.read_text(encoding="utf-8", errors="ignore") if css_path.is_file() else ""
    for selector in (
        ".journal-shell>.wrap.journal-layout",
        ".category-archive>.wrap.archive-layout",
    ):
        selector_pos = css_text.find(selector)
        if selector_pos == -1:
            errors.append(f"blog/assets/blog.css missing full-width layout selector: {selector}")
            continue
        rule_end = css_text.find("}", selector_pos)
        rule_text = css_text[selector_pos:rule_end]
        if "width:100%" not in rule_text or "max-width:none" not in rule_text:
            errors.append(f"blog/assets/blog.css must keep {selector} free from the global wrap width cap")

    required_tokens = (
        "journal-shell",
        "journal-layout",
        "journal-rail",
        "rail-tree",
        "rail-sub",
        "journal-main",
        "articleIndex",
    )

    for rel in REQUIRED_JOURNAL_HOME_PAGES:
        path = root / rel
        if not path.is_file():
            errors.append(f"missing journal home page: {rel}")
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in required_tokens:
            if token not in text:
                errors.append(f"{rel} missing journal home layout token: {token}")
        for token in ("rail-category-title", "rail-topic"):
            if token not in text:
                errors.append(f"{rel} missing hierarchical rail token: {token}")
        rail_pos = text.find("journal-rail")
        head_pos = text.find("page-head")
        if rail_pos == -1 or head_pos == -1 or rail_pos > head_pos:
            errors.append(f"{rel} must show the category rail before the main page-head")
        if text.count('class="rail-topic"') < 6:
            errors.append(f"{rel} must expose at least six subcategory titles in the left rail")
        for required_link in (
            "categories/automotive-ai-robotics.html",
            "categories/fab-ai-foundations.html",
            "categories/rag-knowledge-systems.html",
            "categories/agents-mcp-controls.html",
            "categories/onprem-llm-operations.html",
            "categories/python-langchain-langgraph.html",
        ):
            if required_link not in text:
                errors.append(f"{rel} missing category rail link: {required_link}")

    return errors


def check_html_metadata(root: Path) -> list[str]:
    errors = []
    required_patterns = {
        "title": TITLE_RE,
        "html lang": HTML_LANG_RE,
        "description": re.compile(r"<meta\b[^>]*\bname=[\"']description[\"']", re.IGNORECASE),
        "canonical": re.compile(r"<link\b[^>]*\brel=[\"']canonical[\"']", re.IGNORECASE),
        "og:type": re.compile(r"<meta\b[^>]*\bproperty=[\"']og:type[\"']", re.IGNORECASE),
        "og:title": re.compile(r"<meta\b[^>]*\bproperty=[\"']og:title[\"']", re.IGNORECASE),
        "og:description": re.compile(r"<meta\b[^>]*\bproperty=[\"']og:description[\"']", re.IGNORECASE),
        "og:url": re.compile(r"<meta\b[^>]*\bproperty=[\"']og:url[\"']", re.IGNORECASE),
        "twitter:card": re.compile(r"<meta\b[^>]*\bname=[\"']twitter:card[\"']", re.IGNORECASE),
    }

    for html in root.rglob("*.html"):
        rel = html.relative_to(root).as_posix()
        text = html.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"<meta\b[^>]*\bname=[\"']robots[\"'][^>]*\bnoindex\b", text, re.IGNORECASE):
            continue
        for label, pattern in required_patterns.items():
            if not pattern.search(text):
                errors.append(f"{rel} missing {label}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", default="dist", help="dist directory to validate")
    args = parser.parse_args()

    root = Path(args.dist)
    if not root.is_dir():
        print(f"[ERROR] Missing dist directory: {root}")
        return 1

    errors = []
    errors.extend(f"missing required file: {rel}" for rel in check_required_files(root))
    errors.extend(check_placeholders(root))
    errors.extend(check_quality_risk_patterns(root))
    errors.extend(check_language_separation(root))
    errors.extend(check_blog_contract(root))
    errors.extend(check_interactive_learning_labs(root))
    errors.extend(check_remote_images(root))
    errors.extend(check_share_links(root))
    errors.extend(check_photo_attribution(root))
    errors.extend(check_structured_data_images(root))
    errors.extend(check_local_links(root))
    errors.extend(check_redirects(root))
    errors.extend(check_generated_data(root))
    errors.extend(check_static_hardening(root))
    errors.extend(check_theme_support(root))
    errors.extend(check_media_figures(root))
    errors.extend(check_human_voice(root))
    errors.extend(check_ai_category_archives(root))
    errors.extend(check_journal_home_layout(root))
    errors.extend(check_html_metadata(root))

    if errors:
        print("[ERROR] dist validation failed")
        for error in errors[:300]:
            print(f"  - {error}")
        if len(errors) > 300:
            print(f"  ... {len(errors) - 300} more")
        return 1

    html_count = len(list(root.rglob("*.html")))
    file_count = len(dist_files(root))
    print(f"dist validation passed: {file_count} files, {html_count} HTML pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
