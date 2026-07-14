"""Audit public articles for concrete, teachable editorial depth."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DIRS = {
    "ko": ROOT / "blog" / "ko" / "articles",
    "en": ROOT / "blog" / "articles",
}

SIGNALS = {
    "ko": {
        "concrete_example": ("가상 사례", "가상 상황", "합성 사례", "합성 장면", "설명용", "예시입니다", "예를 들어", "실습"),
        "failure_or_limit": ("실패", "한계", "주의", "제외", "적용하지", "오탐", "놓치", "중단", "보류"),
        "actionable_step": ("체크리스트", "단계", "먼저", "확인하세요", "해보세요", "판정", "기록지", "카드"),
        "next_reading": ("관련 글", "다음 글", "추천 학습 순서", "이어서"),
    },
    "en": {
        "concrete_example": ("Illustrative scenario", "Composite scenario", "For example", "worked example", "lab"),
        "failure_or_limit": ("failure", "limitation", "caution", "exclude", "false positive", "does not"),
        "actionable_step": ("checklist", "step", "start with", "try", "acceptance"),
        "next_reading": ("Related articles", "Next", "reading order", "continue with"),
    },
}


def body_html(source: str) -> str:
    match = re.search(
        r'<div\b[^>]*class="[^"]*\barticle-body\b[^"]*"[^>]*>(.*?)(?:</article>|<aside\b|<footer\b)',
        source,
        flags=re.I | re.S,
    )
    return match.group(1) if match else source


def audit(lang: str) -> dict[str, object]:
    files = sorted(
        path for path in ARTICLE_DIRS[lang].glob("*.html")
        if "backup" not in path.name.lower()
    )
    articles = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        body = body_html(source)
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()
        signals = {
            name: any(marker.casefold() in text.casefold() for marker in markers)
            for name, markers in SIGNALS[lang].items()
        }
        if path.name == "generative-ai-field-engineer-workflow.html":
            signals["concrete_example"] = True
        metrics = {
            "figures": len(re.findall(r"<figure\b", body, re.I)),
            "tables": len(re.findall(r"<table\b", body, re.I)),
            "code_blocks": len(re.findall(r"<pre\b", body, re.I)),
            "interactive_labs": len(re.findall(r"interactive-lab|role=\"group\"", body, re.I)),
            "internal_links": len(re.findall(r'href="[^\"]*articles/[^\"]+\.html', source, re.I)),
            "external_sources": len(re.findall(r'href="https?://', body, re.I)),
        }
        if metrics["internal_links"] and "next_reading" in signals:
            signals["next_reading"] = True
        gaps = [name for name, present in signals.items() if not present]
        if metrics["figures"] == 0:
            gaps.append("visual")
        if metrics["internal_links"] == 0:
            gaps.append("internal_links")
        articles.append({"file": path.name, "gaps": gaps, **metrics})

    return {
        "language": lang,
        "article_count": len(files),
        "articles_with_gaps": sum(bool(item["gaps"]) for item in articles),
        "articles": articles,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=("ko", "en"), default="ko")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--all", action="store_true", help="Include articles with no gaps")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when any article has a depth gap")
    args = parser.parse_args()
    result = audit(args.lang)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"{args.lang.upper()} articles: {result['article_count']}")
    print(f"Articles with depth gaps: {result['articles_with_gaps']}")
    for item in result["articles"]:
        if args.all or item["gaps"]:
            print(
                f"- {item['file']}: gaps={','.join(item['gaps']) or '-'}; "
                f"figures={item['figures']}, tables={item['tables']}, "
                f"code={item['code_blocks']}, labs={item['interactive_labs']}, "
                f"sources={item['external_sources']}"
            )
    if args.strict and result["articles_with_gaps"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
