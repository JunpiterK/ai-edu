# Contributing

Thanks for helping improve AI Edu Archive. The project is intentionally small:
plain HTML sources, a Python build script, and generated static output in `dist/`.

## Good Contributions

- Fix factual or code errors in articles.
- Improve Korean/English wording while preserving technical meaning.
- Add runnable examples, diagrams, checklists, or operational caveats.
- Suggest articles about applied AI, robotics AI, manufacturing AI, on-prem LLMs,
  RAG, MCP, or agent systems.
- Improve build, validation, metadata, accessibility, or deployment tooling.

## Ground Rules

- Use public sources only. Do not include private company data, proprietary fab
  process data, internal network details, unreleased customer information, or
  confidential screenshots.
- Keep articles practical: explain constraints, failure modes, validation, and
  operating procedure.
- Preserve the bilingual direction. Korean and English pages should cover the
  same technical scope, not summary vs. full version.
- Do not add generated filler pages for SEO.
- Keep `dist/` reproducible through `python build_site.py`.

## Local Checks

```powershell
python -m py_compile build_site.py tools\validate_dist.py tools\new_article.py
powershell -ExecutionPolicy Bypass -File tools\deploy_check.ps1
```

The deploy check builds `dist/`, validates internal links and generated metadata,
and prints the Cloudflare Pages deploy command.

## Adding An Article

```powershell
python tools\new_article.py "Article title" `
  --description "One concise SEO description." `
  --category "On-Prem LLM" `
  --minutes 10 `
  --with-ko
```

Then edit the generated article files, add the article links to the source journal
pages if needed, and run the deploy check.

Generated public indexes include:

- `sitemap.xml`
- `rss.xml`
- `blog/ko/rss.xml`
- `llms.txt`
- `search.json`
- `blog/articles.json`
- `blog/ko/articles.json`
