#!/usr/bin/env python
"""Create a starter blog article with complete SEO metadata."""

from __future__ import annotations

import argparse
import html
import re
from datetime import date
from pathlib import Path

SITE_URL = "https://ai-edu-archive.example.com"
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
    article_path = f"/blog/{'ko/' if is_ko else ''}articles/{slug}.html"
    canonical = f"{SITE_URL}{article_path}"
    en_url = f"{SITE_URL}/blog/articles/{slug}.html"
    ko_url = f"{SITE_URL}/blog/ko/articles/{slug}.html"
    locale = "ko_KR" if is_ko else "en_US"
    alt_locale = "en_US" if is_ko else "ko_KR"
    label_read = "Read time" if not is_ko else "Read time"
    back_label = "Journal" if not is_ko else "Journal"

    safe_title = html.escape(title)
    safe_description = html.escape(description)
    safe_category = html.escape(category)

    return f"""<!DOCTYPE html>
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
<meta property="article:published_time" content="{published}">
<meta property="article:author" content="{AUTHOR}">
<meta property="article:section" content="{safe_category}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{safe_title} - AI Edu Archive Journal">
<meta name="twitter:description" content="{safe_description}">
<script type="application/ld+json">{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{safe_title}",
  "description": "{safe_description}",
  "inLanguage": "{lang}",
  "image": "{SITE_URL}/blog/assets/og-default.png",
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
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="{prefix}/index.html">Home</a>
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
          <span>Applied AI, robotics, manufacturing systems</span>
        </span>
      </div>
    </div>
  </div>
  <div class="article-body" itemprop="articleBody">
    <p><span class="lead-in">Draft lead.</span> Replace this opening with the field problem, the constraint, and the promise of the article.</p>
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
</body>
</html>
"""


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
