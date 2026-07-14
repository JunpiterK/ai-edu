"""Shared header and footer contract for public blog pages."""

from __future__ import annotations

import argparse
import posixpath
import re
from html import escape
from pathlib import Path
from urllib.parse import quote


SUPPORTED_LANGS = {"en", "ko"}
DEFAULT_SITE_URL = "https://ai-edu-archive.pages.dev"

_HTML_RE = re.compile(r"<html\b([^>]*)>", re.IGNORECASE)
_SKIP_RE = re.compile(r'<a\b[^>]*class=["\'][^"\']*\bskip-link\b[^"\']*["\'][^>]*>.*?</a>', re.IGNORECASE | re.DOTALL)
_HEADER_RE = re.compile(r"<header\b[^>]*>.*?</header>", re.IGNORECASE | re.DOTALL)
_FOOTER_RE = re.compile(r'<footer\b[^>]*class=["\'][^"\']*\bsite-foot\b[^"\']*["\'][^>]*>.*?</footer>', re.IGNORECASE | re.DOTALL)
_MAIN_RE = re.compile(r"<main\b[^>]*>.*?</main>", re.IGNORECASE | re.DOTALL)
_LINK_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_HREFLANG_RE = re.compile(r'\bhreflang\s*=\s*["\'](en|ko|x-default)["\']', re.IGNORECASE)
_ENDCAP_RE = re.compile(
    r'<(?:aside|section)\b[^>]*class=["\'][^"\']*\barticle-endcap\b[^"\']*["\'][^>]*>.*?</(?:aside|section)>\r?\n?',
    re.IGNORECASE | re.DOTALL,
)

THEME_BOOTSTRAP = """<script id="theme-bootstrap">(function(){try{var t=localStorage.getItem('ai-edu-theme');if(t!=='dark'&&t!=='light'){t=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.dataset.theme=t;document.documentElement.style.colorScheme=t}catch(e){}})();</script>"""


UI = {
    "en": {
        "skip": "Skip to content",
        "nav_label": "Primary navigation",
        "language_label": "Language selector",
        "courses": "Courses",
        "articles": "Articles",
        "paths": "Learning Paths",
        "search": "Search",
        "portfolio": "Portfolio",
        "about": "About",
        "footer_lead": "Practical AI education, open to everyone.",
        "footer_copy": "Courses, articles, and field notes for building useful AI systems.",
        "explore": "Explore",
        "site": "Site",
        "contact": "Contact",
        "privacy": "Privacy",
        "terms": "Terms",
        "copyright": "AI education in Korean and English",
    },
    "ko": {
        "skip": "본문으로 건너뛰기",
        "nav_label": "주요 메뉴",
        "language_label": "언어 선택",
        "courses": "강의",
        "articles": "글",
        "paths": "학습 경로",
        "search": "검색",
        "portfolio": "포트폴리오",
        "about": "소개",
        "footer_lead": "누구나 볼 수 있는 실용적인 AI 교육 자료입니다.",
        "footer_copy": "현장에서 쓸 수 있는 AI 시스템을 위한 강의, 글, 실전 기록을 모았습니다.",
        "explore": "둘러보기",
        "site": "사이트",
        "contact": "연락처",
        "privacy": "개인정보 처리방침",
        "terms": "이용약관",
        "copyright": "한국어와 영어로 제공하는 AI 교육",
    },
}


def _normalize_path(blog_relative_path: str) -> str:
    path = blog_relative_path.replace("\\", "/").lstrip("/")
    if path.startswith("blog/"):
        path = path[len("blog/") :]
    path = posixpath.normpath(path)
    if path in {"", "."} or path == ".." or path.startswith("../"):
        raise ValueError("blog_relative_path must point to a file below blog/")
    return path


def _href(blog_relative_path: str, target: str, *, query: str = "", fragment: str = "") -> str:
    source = f"blog/{_normalize_path(blog_relative_path)}"
    href = posixpath.relpath(target, posixpath.dirname(source))
    if fragment:
        href += f"#{fragment}"
    if query:
        href += f"?{query}"
    return href


def language_pair_hrefs(blog_relative_path: str) -> dict[str, str]:
    """Return relative English and Korean hrefs for one logical blog page."""
    path = _normalize_path(blog_relative_path)
    logical_path = path[len("ko/") :] if path.startswith("ko/") else path
    return {
        "en": _href(path, f"blog/{logical_path}"),
        "ko": _href(path, f"blog/ko/{logical_path}"),
    }


def _nav_items(blog_relative_path: str, lang: str) -> list[tuple[str, str, str]]:
    section = "blog/ko" if lang == "ko" else "blog"
    labels = UI[lang]
    return [
        ("courses", labels["courses"], _href(blog_relative_path, "index.html", fragment="courses")),
        ("articles", labels["articles"], _href(blog_relative_path, f"{section}/index.html")),
        ("paths", labels["paths"], _href(blog_relative_path, f"{section}/learning-paths.html")),
        ("search", labels["search"], _href(blog_relative_path, f"{section}/search.html")),
        ("portfolio", labels["portfolio"], _href(blog_relative_path, f"{section}/portfolio.html")),
        ("about", labels["about"], _href(blog_relative_path, f"{section}/about.html")),
    ]


def _current_section(blog_relative_path: str) -> str:
    path = _normalize_path(blog_relative_path)
    logical = path[len("ko/") :] if path.startswith("ko/") else path
    if logical == "learning-paths.html":
        return "paths"
    if logical == "search.html":
        return "search"
    if logical == "portfolio.html":
        return "portfolio"
    if logical == "about.html":
        return "about"
    if logical == "index.html" or logical.startswith(("articles/", "categories/")) or logical == "ai-categories.html":
        return "articles"
    return ""


def render_skip_link(lang: str) -> str:
    _validate_lang(lang)
    return f'<a class="skip-link" href="#main">{UI[lang]["skip"]}</a>'


def render_header(blog_relative_path: str, lang: str) -> str:
    _validate_lang(lang)
    path = _normalize_path(blog_relative_path)
    labels = UI[lang]
    current = _current_section(path)
    links = []
    for key, label, href in _nav_items(path, lang):
        current_attr = ' aria-current="page"' if key == current else ""
        links.append(f'      <a href="{href}"{current_attr}>{label}</a>')
    pair = language_pair_hrefs(path)
    en_current = ' aria-current="true"' if lang == "en" else ""
    ko_current = ' aria-current="true"' if lang == "ko" else ""
    links.extend(
        [
            f'      <div class="language-switch" aria-label="{labels["language_label"]}">',
            f'        <a href="{pair["en"]}" lang="en"{en_current} title="English">EN</a>',
            f'        <a href="{pair["ko"]}" lang="ko"{ko_current} title="한국어">KO</a>',
            "      </div>",
        ]
    )
    home = _href(path, "index.html")
    return "\n".join(
        [
            '<header class="nav" id="nav">',
            '  <div class="wrap">',
            f'    <a class="brand" href="{home}" aria-label="AI Edu Archive home">',
            '      <span class="brand-name">AI Edu <em>Archive</em></span>',
            "    </a>",
            f'    <nav class="nav-links" aria-label="{labels["nav_label"]}">',
            *links,
            "    </nav>",
            "  </div>",
            "</header>",
        ]
    )


def render_footer(blog_relative_path: str, lang: str) -> str:
    _validate_lang(lang)
    path = _normalize_path(blog_relative_path)
    labels = UI[lang]
    nav = {key: (label, href) for key, label, href in _nav_items(path, lang)}
    section = "blog/ko" if lang == "ko" else "blog"
    contact = _href(path, f"{section}/contact.html")
    privacy = _href(path, f"{section}/privacy.html")
    terms = _href(path, f"{section}/terms.html")
    return f'''<footer class="site-foot">
  <div class="wrap">
    <div class="foot-top">
      <div class="foot-lead">
        <h2>{labels["footer_lead"]}</h2>
        <p>{labels["footer_copy"]}</p>
      </div>
      <div class="foot-nav-cols">
        <div class="foot-col">
          <h4>{labels["explore"]}</h4>
          <a href="{nav["courses"][1]}">{nav["courses"][0]}</a>
          <a href="{nav["articles"][1]}">{nav["articles"][0]}</a>
          <a href="{nav["paths"][1]}">{nav["paths"][0]}</a>
          <a href="{nav["search"][1]}">{nav["search"][0]}</a>
          <a href="{nav["portfolio"][1]}">{nav["portfolio"][0]}</a>
        </div>
        <div class="foot-col">
          <h4>{labels["site"]}</h4>
          <a href="{nav["about"][1]}">{nav["about"][0]}</a>
          <a href="{contact}">{labels["contact"]}</a>
          <a href="{privacy}">{labels["privacy"]}</a>
          <a href="{terms}">{labels["terms"]}</a>
        </div>
      </div>
    </div>
    <div class="foot-bottom">
      <div class="foot-brand"><span class="brand-name">AI Edu <em>Archive</em></span></div>
      <span class="copyright">&copy; 2026 AI Edu Archive · {labels["copyright"]}</span>
    </div>
  </div>
</footer>'''


def render_article_endcap(blog_relative_path: str, lang: str) -> str:
    _validate_lang(lang)
    path = _normalize_path(blog_relative_path)
    section = "blog/ko" if lang == "ko" else "blog"
    journal_href = _href(path, f"{section}/index.html")
    categories_href = _href(path, f"{section}/ai-categories.html")
    if lang == "ko":
        aria = "글 안내"
        note = "현장 경험을 바탕으로 작성하고, 명확성과 기술적 정확성을 검토했습니다."
        journal = "글 목록으로 돌아가기"
        categories = "AI 카테고리 보기"
    else:
        aria = "Article information"
        note = "Written from practical engineering experience and reviewed for clarity and technical accuracy."
        journal = "Back to Journal"
        categories = "Browse AI categories"
    return f'''<aside class="article-endcap" aria-label="{aria}">
  <p>{note}</p>
  <div class="article-endcap-actions">
    <a href="{journal_href}">{journal}</a>
    <a href="{categories_href}">{categories}</a>
  </div>
</aside>'''


def inject_article_endcap(html: str, blog_relative_path: str, lang: str) -> str:
    if not re.search(r"<article\b", html, re.IGNORECASE):
        return html
    for class_name in ("article-endcap", "related", "share", "author-card"):
        if re.search(rf'class=["\'][^"\']*\b{re.escape(class_name)}\b', html, re.IGNORECASE):
            return html
    closing = html.lower().rfind("</article>")
    if closing < 0:
        return html
    endcap = render_article_endcap(blog_relative_path, lang)
    return f"{html[:closing]}{endcap}\n{html[closing:]}"


def inject_theme_bootstrap(html: str) -> str:
    if 'id="theme-bootstrap"' in html or "id='theme-bootstrap'" in html:
        return html
    return re.sub(r"(<head\b[^>]*>)", rf"\1\n{THEME_BOOTSTRAP}", html, count=1, flags=re.IGNORECASE)


_EDITORIAL_MARKER_LINE_RE = re.compile(
    r"(?im)^(?P<indent>[ \t]*)(?P<label>[∨=\s\u200b]*SEO[\s=\u200b]*|오픈 그래프|"
    r"JSON-LD:\s*기사 스키마|심층적인 데크 링크|공유|"
    r"저자 바이오 카드(?:\(E-E-A-T\))?|관련된|===\s*\d+[a-z]?[^<]*)[ \t]*\r?$"
)


def normalize_editorial_markers(html: str) -> str:
    """Restore editor labels that lost their HTML comment delimiters."""
    if re.match(r"^\s*HTML\s*\r?\n", html, re.IGNORECASE):
        html = re.sub(r"^\s*HTML\s*\r?\n", "<!DOCTYPE html>\n", html, count=1, flags=re.IGNORECASE)

    def replace_marker(match: re.Match[str]) -> str:
        label = re.sub(r"^[∨=\s\u200b]+|[=\s\u200b]+$", "", match.group("label")).strip()
        return f'{match.group("indent")}<!-- {label} -->'

    return _EDITORIAL_MARKER_LINE_RE.sub(replace_marker, html)


def normalize_blog_shell(
    html: str,
    blog_relative_path: str,
    lang: str,
    *,
    site_url: str | None = None,
    language_pair_exists: bool = False,
) -> str:
    """Normalize shell-only markup while preserving page content inside ``main``."""
    _validate_lang(lang)
    path = _normalize_path(blog_relative_path)
    html = normalize_editorial_markers(html)

    def replace_html(match: re.Match[str]) -> str:
        attrs = re.sub(r"\s+lang\s*=\s*([\"']).*?\1", "", match.group(1), flags=re.IGNORECASE)
        return f'<html lang="{lang}"{attrs}>'

    html = _HTML_RE.sub(replace_html, html, count=1)
    html = inject_theme_bootstrap(html)
    skip = render_skip_link(lang)
    if _SKIP_RE.search(html):
        html = _SKIP_RE.sub(skip, html, count=1)
    else:
        html = re.sub(r"(<body\b[^>]*>)", rf"\1\n{skip}", html, count=1, flags=re.IGNORECASE)

    header = render_header(path, lang)
    if _HEADER_RE.search(html):
        html = _HEADER_RE.sub(header, html, count=1)
    else:
        html = html.replace(skip, f"{skip}\n{header}", 1)

    footer = render_footer(path, lang)
    if _FOOTER_RE.search(html):
        html = _FOOTER_RE.sub(footer, html, count=1)
    else:
        html = re.sub(r"</main>", f"</main>\n{footer}", html, count=1, flags=re.IGNORECASE)
    html = inject_article_endcap(html, path, lang)
    if language_pair_exists:
        html = normalize_hreflang_alternates(html, path, site_url or DEFAULT_SITE_URL)
    return html


def normalize_hreflang_alternates(html: str, blog_relative_path: str, site_url: str) -> str:
    """Replace the canonical en/ko/x-default alternates for an existing page pair."""
    path = _normalize_path(blog_relative_path)
    logical_path = path[len("ko/") :] if path.startswith("ko/") else path

    def remove_canonical_alternate(match: re.Match[str]) -> str:
        return "" if _HREFLANG_RE.search(match.group(0)) else match.group(0)

    html = _LINK_RE.sub(remove_canonical_alternate, html)
    head_end = html.lower().find("</head>")
    if head_end >= 0:
        head = re.sub(r"(?:\r?\n[ \t]*){3,}", "\n\n", html[:head_end])
        html = head + html[head_end:]
    base = site_url.rstrip("/")
    encoded = quote(logical_path, safe="/")
    en_url = f"{base}/blog/{encoded}"
    ko_url = f"{base}/blog/ko/{encoded}"
    links = "\n".join(
        [
            f'<link rel="alternate" hreflang="en" href="{escape(en_url, quote=True)}">',
            f'<link rel="alternate" hreflang="ko" href="{escape(ko_url, quote=True)}">',
            f'<link rel="alternate" hreflang="x-default" href="{escape(en_url, quote=True)}">',
        ]
    )
    return re.sub(r"</head>", f"{links}\n</head>", html, count=1, flags=re.IGNORECASE)


def _validate_lang(lang: str) -> None:
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"unsupported language: {lang!r}")


def normalize_public_blog_sources(blog_dir: Path, *, check: bool = False) -> tuple[int, int]:
    """Normalize every public blog HTML file and return ``(visited, changed)``."""
    blog_dir = blog_dir.resolve()
    public_paths = [
        path
        for path in sorted(blog_dir.rglob("*.html"))
        if "backup" not in path.name.lower() and path.name.lower() != "article-template.html"
    ]
    public_relatives = {path.relative_to(blog_dir).as_posix() for path in public_paths}
    visited = 0
    changed = 0
    for path in public_paths:
        name = path.name.lower()
        relative = path.relative_to(blog_dir).as_posix()
        lang = "ko" if relative.startswith("ko/") else "en"
        logical = relative[len("ko/") :] if relative.startswith("ko/") else relative
        pair_exists = logical in public_relatives and f"ko/{logical}" in public_relatives
        raw = path.read_bytes()
        has_bom = raw.startswith(b"\xef\xbb\xbf")
        before = raw.decode("utf-8-sig" if has_bom else "utf-8")
        after = normalize_blog_shell(
            before,
            relative,
            lang,
            site_url=DEFAULT_SITE_URL,
            language_pair_exists=pair_exists,
        )
        before_main = _MAIN_RE.search(normalize_editorial_markers(before))
        after_main = _MAIN_RE.search(after)
        before_content = _ENDCAP_RE.sub("", before_main.group(0)) if before_main else None
        after_content = _ENDCAP_RE.sub("", after_main.group(0)) if after_main else None
        if before_content is None or after_content is None or before_content != after_content:
            raise RuntimeError(f"refusing to alter page content in {path}")
        visited += 1
        if before == after:
            continue
        changed += 1
        if not check:
            encoded = after.encode("utf-8")
            path.write_bytes((b"\xef\xbb\xbf" if has_bom else b"") + encoded)
    return visited, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize public blog HTML shell markup.")
    parser.add_argument(
        "--blog-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "blog",
        help="blog source directory (defaults to this repository's blog directory)",
    )
    parser.add_argument("--check", action="store_true", help="report files that would change without writing them")
    args = parser.parse_args()
    visited, changed = normalize_public_blog_sources(args.blog_dir, check=args.check)
    action = "would change" if args.check else "changed"
    print(f"checked {visited} public blog HTML files; {action} {changed}")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
