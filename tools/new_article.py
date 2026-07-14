#!/usr/bin/env python
"""Create a starter blog article with complete SEO metadata."""

from __future__ import annotations

import argparse
import html
import re
from datetime import date
from pathlib import Path

try:
    from tools.site_contract import normalize_blog_shell
except ModuleNotFoundError:  # Direct execution: python tools/new_article.py
    from site_contract import normalize_blog_shell

SITE_URL = "https://ai-edu-archive.pages.dev"
AUTHOR = "AI Edu Archive"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    if not value:
        raise ValueError("slug cannot be empty")
    return value


def article_html(
    *,
    lang: str,
    slug: str,
    title: str,
    description: str,
    category: str,
    published: str,
    minutes: int,
) -> str:
    is_ko = lang == "ko"
    prefix = "../../.." if is_ko else "../.."
    journal_href = "../index.html" if not is_ko else "../index.html"
    about_href = "../about.html"
    css_href = "../../assets/blog.css" if is_ko else "../assets/blog.css"
    visual_href = "../../assets/visuals/article-visual-template.svg" if is_ko else "../assets/visuals/article-visual-template.svg"
    theme_href = "../../assets/theme.js" if is_ko else "../assets/theme.js"
    article_path = f"/blog/{'ko/' if is_ko else ''}articles/{slug}.html"
    canonical = f"{SITE_URL}{article_path}"
    en_url = f"{SITE_URL}/blog/articles/{slug}.html"
    ko_url = f"{SITE_URL}/blog/ko/articles/{slug}.html"
    locale = "ko_KR" if is_ko else "en_US"
    alt_locale = "en_US" if is_ko else "ko_KR"
    label_read = "Read time" if not is_ko else "읽는 시간"
    back_label = "Articles" if not is_ko else "글"
    home_label = "Home" if not is_ko else "홈"
    breadcrumb_label = "Breadcrumb" if not is_ko else "현재 위치"
    byline_role = "Applied AI, robotics, manufacturing systems" if not is_ko else "응용 AI, 로보틱스, 제조 시스템"
    draft_lead = "Draft lead." if not is_ko else "초안 도입부."
    draft_copy = (
        "Replace this opening with the field problem, the constraint, and the promise of the article."
        if not is_ko
        else "현장의 문제, 제약 조건, 이 글에서 얻을 수 있는 내용을 적으세요."
    )

    safe_title = html.escape(title)
    safe_description = html.escape(description)
    safe_category = html.escape(category)

    document = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title} - AI Edu Archive Journal</title>
<meta name="description" content="{safe_description}">
<meta name="author" content="{AUTHOR}">
<meta name="theme-color" content="#FAF9F5">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{en_url}">
<link rel="alternate" hreflang="ko" href="{ko_url}">
<link rel="alternate" hreflang="x-default" href="{en_url}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="article">
<meta property="og:title" content="{safe_title} - AI Edu Archive Journal">
<meta property="og:description" content="{safe_description}">
<meta property="og:site_name" content="AI Edu Archive">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="{locale}">
<meta property="og:locale:alternate" content="{alt_locale}">
<meta property="og:image" content="{SITE_URL}/blog/assets/visuals/article-visual-template.svg">
<meta property="article:published_time" content="{published}">
<meta property="article:author" content="{AUTHOR}">
<meta property="article:section" content="{safe_category}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{safe_title} - AI Edu Archive Journal">
<meta name="twitter:description" content="{safe_description}">
<meta name="twitter:image" content="{SITE_URL}/blog/assets/visuals/article-visual-template.svg">
<script type="application/ld+json">{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{safe_title}",
  "description": "{safe_description}",
  "inLanguage": "{lang}",
  "image": "{SITE_URL}/blog/assets/visuals/article-visual-template.svg",
  "datePublished": "{published}",
  "dateModified": "{published}",
  "author": {{
    "@type": "Person",
    "name": "{AUTHOR}",
    "url": "{SITE_URL}/blog/about.html"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "AI Edu Archive",
    "url": "{SITE_URL}/blog/about.html"
  }},
  "mainEntityOfPage": {{
    "@type": "WebPage",
    "@id": "{canonical}"
  }}
}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400&family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css_href}">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="nav" id="nav">
  <div class="wrap">
    <a class="brand" href="{prefix}/index.html" aria-label="AI Edu Archive home">
      <span class="brand-name">AI Edu <em>Archive</em></span>
    </a>
    <nav class="nav-links" aria-label="Primary">
      <a href="{prefix}/index.html#courses">Courses</a>
      <a href="{journal_href}">{back_label}</a>
      <a href="{about_href}">About</a>
    </nav>
  </div>
</header>
<main id="main">
<article itemscope itemtype="https://schema.org/Article">
  <div class="article-hero">
    <div class="wrap">
      <nav class="breadcrumb" aria-label="{breadcrumb_label}">
        <a href="{prefix}/index.html">{home_label}</a>
        <span class="sep" aria-hidden="true">/</span>
        <a href="{journal_href}">{back_label}</a>
        <span class="sep" aria-hidden="true">/</span>
        <span aria-current="page">{safe_title}</span>
      </nav>
      <div class="post-meta">
        <span class="cat-tag">{safe_category}</span>
        <span class="post-dot"></span>
        <time datetime="{published}" itemprop="datePublished">{published}</time>
        <span class="post-dot"></span>
        <span class="rt">{label_read}: {minutes} min</span>
      </div>
      <h1 itemprop="headline">{safe_title}</h1>
      <div class="byline">
        <span class="avatar" aria-hidden="true">AE</span>
        <span class="who">
          <b itemprop="author">{AUTHOR}</b>
          <span>{byline_role}</span>
        </span>
      </div>
    </div>
  </div>
  <div class="article-body" itemprop="articleBody">
    <p><span class="lead-in">{draft_lead}</span> {draft_copy}</p>
    <figure class="visual-figure media-figure media-figure--diagram">
      <img src="{visual_href}" alt="Starter article concept map" loading="lazy" decoding="async">
      <figcaption><span class="figure-label">Figure.</span> Replace this starter schematic with the article's real visual: a field photo with source credit, a process flowchart, an architecture diagram, a comparison schematic, or an evaluation matrix.</figcaption>
    </figure>
    <div class="field-story">
      <span class="note-k">Field story</span>
      <p>Replace this with the lived engineering moment: what you expected at first, where the build or operation became harder than expected, what you changed, and what mistake the reader can avoid.</p>
    </div>
    <div class="reader-shortcut">
      <span class="note-k">Shortcut I wish I had</span>
      <p>Replace this with the reader's shortcut: the practical rule, test, or design habit that would have saved you time before you learned it the hard way.</p>
    </div>
    <h2 id="problem">Problem</h2>
    <p>Write the practical context here.</p>
    <h2 id="implementation">Implementation</h2>
    <p>Show the steps, commands, diagrams, or code.</p>
    <h2 id="checklist">Checklist</h2>
    <ul>
      <li>Operational constraint.</li>
      <li>Validation method.</li>
      <li>Failure mode to watch.</li>
    </ul>
  </div>
</article>
</main>
<script src="{theme_href}"></script>
</body>
</html>
"""
    blog_path = f"{'ko/' if is_ko else ''}articles/{slug}.html"
    return normalize_blog_shell(document, blog_path, lang)


def write_article(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"target already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="article title")
    parser.add_argument("--slug", help="URL slug; defaults to slugified title")
    parser.add_argument("--description", required=True, help="SEO description")
    parser.add_argument("--category", default="On-Prem LLM", help="article category")
    parser.add_argument("--date", default=date.today().isoformat(), help="publish date")
    parser.add_argument("--minutes", type=int, default=10, help="reading time in minutes")
    parser.add_argument("--with-ko", action="store_true", help="also create a Korean mirror draft")
    args = parser.parse_args()

    slug = slugify(args.slug or args.title)
    en_path = Path("blog/articles") / f"{slug}.html"
    write_article(
        en_path,
        article_html(
            lang="en",
            slug=slug,
            title=args.title,
            description=args.description,
            category=args.category,
            published=args.date,
            minutes=args.minutes,
        ),
    )
    print(f"created {en_path}")

    if args.with_ko:
        ko_path = Path("blog/ko/articles") / f"{slug}.html"
        write_article(
            ko_path,
            article_html(
                lang="ko",
                slug=slug,
                title=args.title,
                description=args.description,
                category=args.category,
                published=args.date,
                minutes=args.minutes,
            ),
        )
        print(f"created {ko_path}")

    print("next: add the article to blog/index.html and blog/ko/index.html, then run python build_site.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
