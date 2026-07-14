"""Report repeated prose and experience-claim risks in Korean articles."""

from __future__ import annotations

import argparse
import collections
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DIRS = {
    "ko": ROOT / "blog" / "ko" / "articles",
    "en": ROOT / "blog" / "articles",
}
EXPERIENCE_MARKERS = {
    "ko": (
    "현장 시행착오",
    "제가 먼저 돌아간 길",
    "현장 경험을 바탕으로 작성",
    "제가 처음",
    "저도 여기서",
    "제가 구축 과정에서",
    ),
    "en": (
        "Field story",
        "Shortcut I wish I had",
        "Written from practical engineering experience",
        "I learned",
        "I used to",
        "I first assumed",
    ),
}
AI_RHETORIC = {
    "ko": (
    "마법이 아닙니다",
    "핵심은",
    "단순히",
    "결국",
    "할 수 있습니다",
    "해야 합니다",
    ),
    "en": (
        "The key is",
        "not magic",
        "magic",
        "quietly fails",
        "game changer",
        "production-ready",
    ),
}

PERSONAL_CLAIM_PATTERNS = {
    "ko": re.compile(r"(?:(?<![가-힣])(?:저는|제가|저도)(?![가-힣])|직접\s.{0,20}(?:해봤|사용했|겪었)|(?:해봤|겪었)습니다)"),
    "en": re.compile(r"\b(?:I|we)\s+(?:built|deployed|used|learned|tried|experienced|ran)\b", re.I),
}
VERIFIED_PERSONAL_EXPERIENCE = {
    "ko": {"generative-ai-field-engineer-workflow.html"},
    "en": {"generative-ai-field-engineer-workflow.html"},
}
FORMULAIC_PHRASES = {
    "ko": (),
    "en": ("first hypothesis", "failed first hypothesis"),
}


class ArticleBodyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active = False
        self.div_depth = 0
        self.suppressed_depth = 0
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.active and tag in {"pre", "code", "script", "style"}:
            self.suppressed_depth += 1
        if tag != "div":
            return
        classes = dict(attrs).get("class", "") or ""
        if not self.active and "article-body" in classes.split():
            self.active = True
            self.div_depth = 1
        elif self.active:
            self.div_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.active and tag in {"pre", "code", "script", "style"} and self.suppressed_depth:
            self.suppressed_depth -= 1
        if self.active and tag == "div":
            self.div_depth -= 1
            if self.div_depth == 0:
                self.active = False

    def handle_data(self, data: str) -> None:
        if self.active and self.suppressed_depth == 0:
            self.text.append(data)


def visible_text(source: str) -> str:
    parser = ArticleBodyParser()
    parser.feed(source)
    if parser.text:
        source = " ".join(parser.text)
    source = re.sub(r"<(script|style)\b.*?</\1>", " ", source, flags=re.I | re.S)
    source = re.sub(r"<[^>]+>", " ", source)
    return re.sub(r"\s+", " ", html.unescape(source)).strip()


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?다요죠])\s+", text)
    return [part.strip() for part in parts if len(part.strip()) >= 32]


def audit(lang: str) -> dict[str, object]:
    files = sorted(
        path for path in ARTICLE_DIRS[lang].glob("*.html")
        if "backup" not in path.name.lower()
    )
    texts = {path.name: visible_text(path.read_text(encoding="utf-8")) for path in files}
    marker_counts = {
        name: {marker: text.count(marker) for marker in EXPERIENCE_MARKERS[lang] if marker in text}
        for name, text in texts.items()
    }
    rhetoric_counts = {
        name: {marker: text.count(marker) for marker in AI_RHETORIC[lang] if marker in text}
        for name, text in texts.items()
    }
    personal_claims = {}
    for name, text in texts.items():
        if name in VERIFIED_PERSONAL_EXPERIENCE[lang]:
            continue
        matches = sorted(set(PERSONAL_CLAIM_PATTERNS[lang].findall(text)))
        if matches:
            personal_claims[name] = matches

    sentence_docs: dict[str, set[str]] = collections.defaultdict(set)
    for name, text in texts.items():
        for sentence in set(sentences(text)):
            sentence_docs[sentence].add(name)
    repeated = [
        {"sentence": sentence, "files": sorted(names)}
        for sentence, names in sentence_docs.items()
        if len(names) >= 2
    ]
    repeated.sort(key=lambda item: (-len(item["files"]), item["sentence"]))

    formulaic_phrase_docs = {
        phrase: sorted(name for name, text in texts.items() if phrase.casefold() in text.casefold())
        for phrase in FORMULAIC_PHRASES[lang]
    }
    formulaic_phrase_docs = {
        phrase: names for phrase, names in formulaic_phrase_docs.items() if names
    }

    return {
        "article_count": len(files),
        "experience_markers": {k: v for k, v in marker_counts.items() if v},
        "unverified_personal_claims": personal_claims,
        "ai_rhetoric": {k: v for k, v in rhetoric_counts.items() if v},
        "repeated_sentences": repeated,
        "formulaic_phrase_docs": formulaic_phrase_docs,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", choices=("ko", "en"), default="ko")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--top", type=int, default=20, help="Repeated sentences to show")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on publish-blocking voice risks")
    args = parser.parse_args()
    result = audit(args.lang)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"{args.lang.upper()} articles: {result['article_count']}")
    print(f"Articles with experience-risk markers: {len(result['experience_markers'])}")
    print(f"Articles with unverified first-person claims: {len(result['unverified_personal_claims'])}")
    print(f"Articles with common AI rhetoric: {len(result['ai_rhetoric'])}")
    print(f"Common AI rhetoric occurrences: {sum(sum(v.values()) for v in result['ai_rhetoric'].values())}")
    repeats = result["repeated_sentences"]
    print(f"Sentences repeated across articles: {len(repeats)}")
    for item in repeats[: args.top]:
        files = ", ".join(item["files"])
        print(f"- [{files}] {item['sentence']}")
    formulaic = result["formulaic_phrase_docs"]
    for phrase, files in formulaic.items():
        print(f"Formulaic phrase {phrase!r}: {len(files)} articles")

    formulaic_limit = max(4, (result["article_count"] + 4) // 5)
    has_formulaic_risk = any(len(files) >= formulaic_limit for files in formulaic.values())
    if args.strict and (
        result["experience_markers"]
        or result["unverified_personal_claims"]
        or result["repeated_sentences"]
        or has_formulaic_risk
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
