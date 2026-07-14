"""Rank article pairs by practical depth, evidence, and visual substance."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DIRS = {
    "ko": ROOT / "blog" / "ko" / "articles",
    "en": ROOT / "blog" / "articles",
}
REPORT_PATH = ROOT / "CONTENT_UPGRADE_BACKLOG.md"

CASE_MARKERS = (
    "field-story",
    "field-note",
    "beginner-example",
    "reader-shortcut",
    "interactive-lab",
    "fab-voice",
)

PASS_MARKERS = {
    "ko": ("통과", "합격", "검증 기준", "acceptance", "pass"),
    "en": ("pass", "acceptance", "validation gate", "exit criteria"),
}

STOP_MARKERS = {
    "ko": ("중단", "보류", "배포 금지", "stop", "fail-closed"),
    "en": ("stop", "withhold", "suspend", "fail closed", "fail-closed"),
}

FAILURE_MARKERS = {
    "ko": ("실패", "한계", "오탐", "누락", "중단", "보류", "깨지", "원인 증명"),
    "en": ("failure", "limit", "false positive", "missing", "stop", "withhold", "break", "causation"),
}

ACTION_MARKERS = {
    "ko": ("먼저", "다음", "확인", "기록", "실행", "설치", "조회", "검증", "승인"),
    "en": ("first", "next", "check", "record", "run", "install", "query", "verify", "approve"),
}


@dataclass
class ArticleAudit:
    slug: str
    title: str
    language: str
    risk_score: int
    tier: str
    gaps: list[str]
    text_units: int
    h2: int
    figures: int
    photos: int
    diagrams: int
    tables: int
    code_blocks: int
    interactive_labs: int
    case_blocks: int
    external_sources: int
    numeric_tokens: int


def article_body(source: str) -> str:
    match = re.search(
        r'<div\b[^>]*class="[^"]*\barticle-body\b[^"]*"[^>]*>(.*?)(?:<div\b[^>]*class="share"|<aside\b|</article>)',
        source,
        flags=re.I | re.S,
    )
    return match.group(1) if match else source


def plain_text(fragment: str) -> str:
    without_code = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", without_code))).strip()


def title_from(source: str, fallback: str) -> str:
    match = re.search(r'<h1\b[^>]*>(.*?)</h1>', source, flags=re.I | re.S)
    return plain_text(match.group(1)) if match else fallback


def tier_for(score: int) -> str:
    if score >= 10:
        return "P0-critical"
    if score >= 7:
        return "P1-high"
    if score >= 4:
        return "P2-medium"
    return "P3-strong"


def audit_article(path: Path, lang: str) -> ArticleAudit:
    source = path.read_text(encoding="utf-8")
    body = article_body(source)
    text = plain_text(body)
    folded = text.casefold()
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", text)
    korean_chars = re.findall(r"[가-힣]", text)
    text_units = len(korean_chars) if lang == "ko" else len(words)

    h2 = len(re.findall(r"<h2\b", body, re.I))
    figures = len(re.findall(r"<figure\b", body, re.I))
    photos = len(re.findall(r'<img\b[^>]*src="[^"]*/photos/', body, re.I))
    diagrams = len(re.findall(r'<img\b[^>]*src="[^"]*/visuals/', body, re.I))
    tables = len(re.findall(r"<table\b", body, re.I))
    code_blocks = len(re.findall(r"<pre\b", body, re.I))
    interactive_labs = len(re.findall(r"interactive-lab|role=\"group\"", body, re.I))
    case_blocks = sum(len(re.findall(marker, body, re.I)) for marker in CASE_MARKERS)
    external_sources = len(
        re.findall(
            r'href="https?://(?!twitter\.com|www\.linkedin\.com|ai-edu-archive\.pages\.dev)[^"]+"',
            body,
            re.I,
        )
    )
    numeric_tokens = len(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:%|ms|s|min|초|분|시간|GB|MB|개|건)?", text))

    gaps: list[str] = []
    score = 0

    if lang == "ko":
        if text_units < 2200:
            gaps.append("본문 설명량이 매우 적음")
            score += 3
        elif text_units < 3300:
            gaps.append("본문 설명량이 얕음")
            score += 2
        elif text_units < 4500:
            gaps.append("장문 심화 설명이 부족함")
            score += 1
    else:
        if text_units < 1100:
            gaps.append("very short body")
            score += 3
        elif text_units < 1600:
            gaps.append("short body")
            score += 2
        elif text_units < 2100:
            gaps.append("limited long-form depth")
            score += 1

    if h2 < 4:
        gaps.append("핵심 논점 전개가 4개 미만" if lang == "ko" else "fewer than four developed sections")
        score += 2
    elif h2 < 6:
        gaps.append("심화 섹션이 적음" if lang == "ko" else "few deep-dive sections")
        score += 1

    if figures == 0:
        gaps.append("시각 자료 없음" if lang == "ko" else "no visual")
        score += 3
    elif figures == 1:
        gaps.append("대표 도표 한 장에 의존" if lang == "ko" else "relies on one lead visual")
        score += 2
    elif figures == 2:
        gaps.append("시각 자료 다양성 제한" if lang == "ko" else "limited visual variety")
        score += 1

    if case_blocks == 0:
        gaps.append("현장 사례·실습 블록 없음" if lang == "ko" else "no field case or exercise block")
        score += 3
    elif case_blocks == 1:
        gaps.append("현장 사례가 한 장면에 그침" if lang == "ko" else "only one field case")
        score += 1

    if tables + code_blocks + interactive_labs == 0:
        gaps.append("표·코드·시뮬레이션 산출물 없음" if lang == "ko" else "no table, code, or simulation artifact")
        score += 2

    if external_sources == 0:
        gaps.append("본문 근거 문헌 링크 없음" if lang == "ko" else "no in-body research source")
        score += 2
    elif external_sources == 1:
        gaps.append("외부 근거가 한 출처에 의존" if lang == "ko" else "single external source")
        score += 1

    has_pass = any(marker.casefold() in folded for marker in PASS_MARKERS[lang])
    has_stop = any(marker.casefold() in folded for marker in STOP_MARKERS[lang])
    if not (has_pass and has_stop):
        gaps.append("통과·중단 기준 없음" if lang == "ko" else "no pass/stop criteria")
        score += 2
    if not any(marker.casefold() in folded for marker in FAILURE_MARKERS[lang]):
        gaps.append("실패 모드·한계 설명 부족" if lang == "ko" else "failure modes or limits missing")
        score += 1
    if not any(marker.casefold() in folded for marker in ACTION_MARKERS[lang]):
        gaps.append("독자가 따라 할 절차 부족" if lang == "ko" else "few reader actions")
        score += 1
    if numeric_tokens < 3:
        gaps.append("수치가 있는 worked example 부족" if lang == "ko" else "no numerical worked example")
        score += 1
    if photos == 0:
        gaps.append("실물 맥락 사진 없음(필요성 검토)" if lang == "ko" else "no physical-context photo; review need")

    return ArticleAudit(
        slug=path.name,
        title=title_from(source, path.stem),
        language=lang,
        risk_score=score,
        tier=tier_for(score),
        gaps=gaps,
        text_units=text_units,
        h2=h2,
        figures=figures,
        photos=photos,
        diagrams=diagrams,
        tables=tables,
        code_blocks=code_blocks,
        interactive_labs=interactive_labs,
        case_blocks=case_blocks,
        external_sources=external_sources,
        numeric_tokens=numeric_tokens,
    )


def scan(lang: str) -> list[ArticleAudit]:
    return sorted(
        (
            audit_article(path, lang)
            for path in ARTICLE_DIRS[lang].glob("*.html")
            if "backup" not in path.name.casefold() and "template" not in path.name.casefold()
        ),
        key=lambda item: (-item.risk_score, item.slug),
    )


def render_report(ko_items: list[ArticleAudit], en_items: list[ArticleAudit]) -> str:
    en_by_slug = {item.slug: item for item in en_items}
    lines = [
        "# Content Upgrade Backlog",
        "",
        "This report is generated by `tools/audit_content_substance.py`. It ranks article pairs by practical depth rather than file existence or minimum word count.",
        "",
        "## Scoring Contract",
        "",
        "Risk rises when an article is short, has fewer than four developed sections, depends on one lead visual, lacks field cases, has no table/code/simulation artifact, cites no research source, or omits pass/stop criteria and failure modes. A missing real photo is a review flag, not an automatic defect; some abstract topics are better served by original diagrams.",
        "",
        "## Upgrade Order",
        "",
        "| Rank | Tier | Korean title | KO / EN risk | Visuals KO | Cases KO | Sources KO | Priority gaps |",
        "|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for index, ko in enumerate(ko_items, start=1):
        en = en_by_slug.get(ko.slug)
        pair_score = f"{ko.risk_score} / {en.risk_score}" if en else f"{ko.risk_score} / missing"
        top_gaps = "; ".join(ko.gaps[:4]) or "-"
        lines.append(
            f"| {index} | {ko.tier} | [{ko.title}](blog/ko/articles/{ko.slug}) | {pair_score} | "
            f"{ko.figures} ({ko.photos} photo) | {ko.case_blocks} | {ko.external_sources} | {top_gaps} |"
        )

    lines.extend(
        [
            "",
            "## Per-Article Upgrade Definition",
            "",
            "Each upgraded article should normally include: a clearly bounded field problem; at least two distinct worked cases; inputs and source systems; a failure or misleading first hypothesis; a diagram that explains the decision path; a table, query, manifest, checklist, or simulation readers can reuse; explicit pass, stop, and limitation statements; authoritative references; and a local licensed photo when physical context materially improves understanding.",
            "",
            "## Pairing Exceptions",
            "",
        ]
    )
    ko_slugs = {item.slug for item in ko_items}
    en_slugs = {item.slug for item in en_items}
    missing_en = sorted(ko_slugs - en_slugs)
    missing_ko = sorted(en_slugs - ko_slugs)
    lines.append(f"- Missing English pairs: {', '.join(missing_en) if missing_en else 'none'}")
    lines.append(f"- Missing Korean pairs: {', '.join(missing_ko) if missing_ko else 'none'}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=("ko", "en", "both"), default="both")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    ko_items = scan("ko")
    en_items = scan("en")
    selected = {"ko": ko_items, "en": en_items}
    if args.write_report:
        REPORT_PATH.write_text(render_report(ko_items, en_items), encoding="utf-8")
        print(f"wrote {REPORT_PATH}")
    if args.json:
        payload = selected if args.lang == "both" else {args.lang: selected[args.lang]}
        print(json.dumps({key: [asdict(item) for item in value] for key, value in payload.items()}, ensure_ascii=False, indent=2))
        return
    languages = ("ko", "en") if args.lang == "both" else (args.lang,)
    for lang in languages:
        print(f"{lang.upper()} substance ranking ({len(selected[lang])} articles)")
        for item in selected[lang][: args.top]:
            print(
                f"- {item.tier} score={item.risk_score:02d} {item.slug}: "
                f"fig={item.figures}, photo={item.photos}, cases={item.case_blocks}, "
                f"sources={item.external_sources}; {', '.join(item.gaps[:5])}"
            )


if __name__ == "__main__":
    main()
