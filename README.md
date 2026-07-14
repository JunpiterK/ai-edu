# AI_EDU

Static educational site for applied AI, robotics AI, manufacturing AI, on-prem LLM,
RAG, MCP, and agent systems — written from hands-on factory-floor experience,
in English and Korean. Live site: https://ai-edu-archive.pages.dev

**Contributions welcome** — error fixes, EN↔KO translation polish, worked
examples, and topic suggestions. See [CONTRIBUTING.md](CONTRIBUTING.md).
All technical claims cite public sources only.

The repository is intentionally simple: hand-authored HTML lives in the source
folders, and `build_site.py` creates the public `dist/` folder for Cloudflare Pages.

## Structure

- `index.html` - public home page
- `overview/` - Fab AI overview deck and selected standalone lessons
- `watsonX/` - air-gapped LLM overview
- `LLM_apply/` - enterprise LLM, RAG, and agent operations slide decks
- `blog/` - English and Korean journal pages
- `tools/` - build, validation, and article helper scripts
- `dist/` - generated deploy output

## Build

```powershell
python build_site.py
```

The build generates:

- `dist/sitemap.xml`
- `dist/robots.txt`
- `dist/rss.xml`
- `dist/blog/ko/rss.xml`
- `dist/llms.txt`
- `dist/search.json`
- `dist/content-audit.json`
- `dist/site.webmanifest`
- `dist/favicon.svg`
- `dist/opensearch.xml`
- `dist/404.html`
- `dist/_redirects`
- `dist/blog/articles.json`
- `dist/blog/ko/articles.json`
- `dist/_headers`

Default public URL:

```text
https://ai-edu-archive.pages.dev
```

Use a real domain at build time:

```powershell
$env:SITE_URL = "https://your-domain.com"
$env:SUPPORT_EMAIL = "hello@your-domain.com"
python build_site.py
```

## Validate

```powershell
python tools\validate_dist.py
```

The validator checks required generated files, placeholder domains, local links,
redirect rules, RSS XML, OpenSearch XML, sitemap XML, the search index, content
audit JSON, web manifest, favicon SVG, and the English/Korean article JSON
indexes.

## Deploy Check

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy_check.ps1
```

With a custom domain:

```powershell
powershell -ExecutionPolicy Bypass -File tools\deploy_check.ps1 `
  -SiteUrl "https://your-domain.com" `
  -SupportEmail "hello@your-domain.com"
```

If validation passes, deploy:

```powershell
wrangler pages deploy dist --project-name=ai-edu-archive
```

## New Article Draft

```powershell
python tools\new_article.py "Article title" `
  --description "One concise SEO description." `
  --category "On-Prem LLM" `
  --minutes 10 `
  --with-ko
```

Then build and validate. The build refreshes the English and Korean article
indexes from article metadata automatically.
