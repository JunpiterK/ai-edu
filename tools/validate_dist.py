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

LOCAL_LINK_RE = re.compile(r"""(?:href|src)=["']([^"']+)["']""", re.IGNORECASE)
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
        "blog/articles.json",
        "blog/ko/articles.json",
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


def check_generated_data(root: Path) -> list[str]:
    errors = []

    try:
        sitemap = ElementTree.parse(root / "sitemap.xml")
        urls = sitemap.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        if not urls:
            errors.append("sitemap.xml has no <url> entries")
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

    for json_rel in ("blog/articles.json", "blog/ko/articles.json"):
        try:
            data = json.loads((root / json_rel).read_text(encoding="utf-8"))
            articles = data.get("articles", [])
            if not articles:
                errors.append(f"{json_rel} has no articles")
            for idx, article in enumerate(articles):
                for key in ("title", "description", "url", "path", "published"):
                    if not article.get(key):
                        errors.append(f"{json_rel} article {idx} missing {key}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{json_rel} parse error: {exc}")

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
    errors.extend(check_local_links(root))
    errors.extend(check_generated_data(root))

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
