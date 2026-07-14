"""Second voice pass: add reader shortcuts to articles and human notes to hubs."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ARTICLE_GROUPS = {
    "rag": {
        "match": ("rag", "chunking", "embedding", "knowledge-graph", "hybrid-retrieval"),
        "en": "The shortcut: do not start from the model. Start from the evidence chain. If source, revision, permission, chunk, and citation are weak, the best model in the room will still sound confident for the wrong reason. Make the retrieval boringly checkable first.",
        "ko": "Shortcut은 이겁니다. model부터 보지 말고 evidence chain부터 보세요. source, revision, permission, chunk, citation이 약하면 아무리 좋은 모델도 그럴듯하게 틀립니다. 먼저 retrieval을 지루할 정도로 확인 가능하게 만들어야 합니다.",
    },
    "agent": {
        "match": ("agent", "mcp", "policy", "incident", "hitl", "langgraph", "tools"),
        "en": "The shortcut: before giving an agent another tool, write down who owns the action, what approval is needed, what gets logged, and how to roll it back. If that sentence is fuzzy, the agent is not ready for production work yet.",
        "ko": "Shortcut은 agent에 tool을 하나 더 붙이기 전에 action owner, approval, log, rollback을 먼저 쓰는 겁니다. 이 문장이 흐릿하면 아직 production에 넣을 준비가 안 된 겁니다.",
    },
    "model": {
        "match": ("onprem", "open-models", "consumer-gpu"),
        "en": "The shortcut: test the ugly operating conditions early. Concurrency, restart, memory pressure, model loading time, and bad prompts reveal more than a clean single-user demo. I would rather find that pain on a lab box than during a plant review.",
        "ko": "Shortcut은 지저분한 운영 조건을 일찍 시험하는 겁니다. 동시 접속, 재시작, memory pressure, model loading time, 이상한 prompt가 단일 사용자 demo보다 더 많은 걸 보여줍니다. 이 고통은 plant review 자리보다 lab box에서 먼저 겪는 게 낫습니다.",
    },
    "fab": {
        "match": ("fab", "fdc", "equipment"),
        "en": "The shortcut: if a trace, wafer, chamber, recipe, metrology result, and maintenance state cannot be joined without hand repair, pause the AI ambition for a moment. The first win is usually not a smarter model; it is a cleaner engineering record.",
        "ko": "Shortcut은 trace, wafer, chamber, recipe, metrology result, maintenance state를 손보정 없이 연결할 수 있는지 먼저 보는 겁니다. 안 된다면 AI 욕심을 잠깐 멈추세요. 첫 승리는 더 똑똑한 모델이 아니라 더 깨끗한 engineering record인 경우가 많습니다.",
    },
    "auto": {
        "match": ("automotive", "vin", "takt"),
        "en": "The shortcut: do not translate fab words directly into automotive words. Start from the moving object, the station rhythm, the safety boundary, and the quality action. VIN logic is not wafer logic wearing a different badge.",
        "ko": "Shortcut은 FAB 단어를 자동차 단어로 그대로 번역하지 않는 겁니다. 움직이는 대상, station rhythm, safety boundary, quality action부터 잡으세요. VIN logic은 이름표만 바꾼 wafer logic이 아닙니다.",
    },
    "python": {
        "match": ("langchain", "lang-modules"),
        "en": "The shortcut: keep the clever part small and the contracts explicit. A clean loader, retriever, prompt, tool schema, state object, and test will save more time than one impressive notebook that nobody wants to debug later.",
        "ko": "Shortcut은 clever한 부분을 작게 두고 contract를 명확히 하는 겁니다. loader, retriever, prompt, tool schema, state object, test가 분리되어 있으면 나중에 아무도 디버깅하기 싫어하는 멋진 notebook보다 훨씬 오래 버팁니다.",
    },
}

DEFAULT_SHORTCUT = {
    "en": "The shortcut: make the work inspectable. If another engineer cannot see the source, assumption, failure mode, and rollback path, the article is not finished and the system is not ready.",
    "ko": "Shortcut은 일을 inspectable하게 만드는 겁니다. 다른 engineer가 source, assumption, failure mode, rollback path를 볼 수 없다면 글도 아직 덜 끝났고 시스템도 아직 준비가 덜 된 겁니다.",
}

HUB_NOTES = {
    "blog/index.html": ("From the field", "I would not read this archive straight through like a textbook. Start with the problem you are actually carrying this week: sealed documents, a noisy tool trace, a nervous agent action, or a local model that needs to run without leaking data. The categories on the left are meant to save you from wandering."),
    "blog/ko/index.html": ("현장식 읽기", "이 아카이브는 교과서처럼 처음부터 끝까지 읽으라고 만든 게 아닙니다. 이번 주에 실제로 들고 있는 문제에서 시작하세요. 폐쇄망 문서, 시끄러운 장비 trace, 불안한 agent action, 밖으로 나가면 안 되는 local model 같은 것들 말입니다. 왼쪽 카테고리는 헤매는 시간을 줄이려고 만든 길잡이입니다."),
    "blog/ai-categories.html": ("How I would use this map", "When a system feels overwhelming, I split it by operational pain: data foundation, trusted retrieval, controlled action, and local serving. That is how this category map is arranged. Pick the pain first; the tool choice becomes much easier afterwards."),
    "blog/ko/ai-categories.html": ("이 지도를 쓰는 법", "시스템이 너무 커 보일 때 저는 운영 고통별로 나눕니다. data foundation, trusted retrieval, controlled action, local serving. 이 카테고리 지도도 그 순서로 읽히게 잡았습니다. 먼저 아픈 지점을 고르면 tool 선택은 그 다음에 훨씬 쉬워집니다."),
    "blog/automotive-ai-robotics.html": ("Field boundary", "I keep this series separate because automotive plants punish lazy analogies. A robot cell, takt window, Andon event, and VIN history create a different rhythm from wafers and chambers. The overlap with FAB AI is useful, but the boundary matters."),
    "blog/ko/automotive-ai-robotics.html": ("현장 경계선", "자동차 제조 AI를 별도 시리즈로 둔 이유는 단순 비유가 금방 틀리기 때문입니다. robot cell, takt window, Andon event, VIN history는 wafer와 chamber와 다른 리듬을 만듭니다. FAB AI와 겹치는 부분은 분명 있지만, 경계선을 잡아야 합니다."),
    "blog/learning-paths.html": ("Reading advice", "Do not try to learn everything before building anything. Read one path, build a small slice, break it, then come back. The archive is designed so the second read makes more sense after the first mistake."),
    "blog/ko/learning-paths.html": ("읽는 방법", "무언가 만들기 전에 전부 공부하려고 하지 마세요. 한 경로를 읽고, 작은 조각을 만들고, 깨뜨려 본 뒤 다시 돌아오면 됩니다. 이 아카이브는 첫 실수 뒤에 두 번째로 읽을 때 더 잘 이해되도록 구성했습니다."),
    "blog/portfolio.html": ("What the cases are for", "These cases are not meant to show that every AI idea works. They show where the design pressure appears: permissions, evidence, evaluation, rollback, and the uncomfortable gap between a demo and a system people can trust."),
    "blog/ko/portfolio.html": ("사례를 보는 법", "이 사례들은 모든 AI 아이디어가 잘 된다고 보여주려는 게 아닙니다. permission, evidence, evaluation, rollback, 그리고 demo와 신뢰 가능한 system 사이의 불편한 간격이 어디서 생기는지 보려는 자료입니다."),
    "blog/about.html": ("Author's stance", "The point of this archive is not to sound futuristic. It is to make AI work boring enough to review, operate, and improve. That usually means more attention to data ownership, validation, and failure handling than the demo video suggests."),
    "blog/ko/about.html": ("작성자의 기준", "이 아카이브의 목표는 미래적으로 들리는 게 아닙니다. AI 작업을 review하고, 운영하고, 개선할 수 있을 만큼 차분하게 만드는 것입니다. 그러려면 demo 영상보다 data ownership, validation, failure handling에 더 오래 머물러야 합니다."),
}


def choose_shortcut(slug: str, lang: str) -> str:
    for group in ARTICLE_GROUPS.values():
        if any(token in slug for token in group["match"]):
            return group[lang]
    return DEFAULT_SHORTCUT[lang]


def block(class_name: str, label: str, text: str) -> str:
    return (
        f'    <div class="{class_name}">\n'
        f'      <span class="note-k">{escape(label)}</span>\n'
        f"      <p>{escape(text)}</p>\n"
        "    </div>\n\n"
    )


def add_reader_shortcut(path: Path, lang: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if "reader-shortcut" in text:
        return False
    story = re.search(r'(<div\b[^>]*class="[^"]*\bfield-story\b[^"]*"[^>]*>.*?</div>\s*)', text, re.DOTALL)
    if not story:
        raise RuntimeError(f"field-story missing: {path}")
    label = "Shortcut I wish I had" if lang == "en" else "제가 먼저 돌아간 길"
    text = text[: story.end()] + block("reader-shortcut", label, choose_shortcut(path.name, lang)) + text[story.end():]
    path.write_text(text, encoding="utf-8")
    return True


def add_hub_voice(path: Path, label: str, note: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if "hub-voice" in text:
        return False

    if "category-archive" in text:
        intro = re.search(r'(<p class="archive-intro">.*?</p>)', text, re.DOTALL)
        if not intro:
            raise RuntimeError(f"archive intro missing: {path}")
        insert_at = intro.end()
    else:
        head = re.search(r'(<section\b[^>]*class="[^"]*\bpage-head\b[^"]*"[^>]*>.*?</section>)', text, re.DOTALL)
        if not head:
            head = re.search(r'(<section\b[^>]*class="[^"]*\bportfolio-hero\b[^"]*"[^>]*>.*?</section>)', text, re.DOTALL)
        if not head:
            raise RuntimeError(f"page head missing: {path}")
        insert_at = head.end()

    text = text[:insert_at] + "\n" + block("hub-voice", label, note) + text[insert_at:]
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    changed = []
    for path in sorted((ROOT / "blog/articles").glob("*.html")):
        if "backup" in path.name:
            continue
        if add_reader_shortcut(path, "en"):
            changed.append(path.relative_to(ROOT).as_posix())
    for path in sorted((ROOT / "blog/ko/articles").glob("*.html")):
        if "backup" in path.name:
            continue
        if add_reader_shortcut(path, "ko"):
            changed.append(path.relative_to(ROOT).as_posix())

    for rel, (label, note) in HUB_NOTES.items():
        path = ROOT / rel
        if add_hub_voice(path, label, note):
            changed.append(rel)

    for category_dir, lang in ((ROOT / "blog/categories", "en"), (ROOT / "blog/ko/categories", "ko")):
        for path in sorted(category_dir.glob("*.html")):
            if "hub-voice" in path.read_text(encoding="utf-8"):
                continue
            if lang == "en":
                label = "Before you pick a post"
                note = "I grouped these posts by the kind of mistake they help avoid. Read the first item for orientation, then jump to the failure mode that resembles your own system. That is usually faster than reading by publish date."
            else:
                label = "글을 고르기 전에"
                note = "이 글 묶음은 피해야 할 실수의 종류별로 나눴습니다. 첫 글로 방향을 잡고, 그 다음에는 지금 본인 시스템의 failure mode와 가장 닮은 글로 바로 이동하세요. 발행일 순서로 읽는 것보다 대개 빠릅니다."
            if add_hub_voice(path, label, note):
                changed.append(path.relative_to(ROOT).as_posix())

    print(f"updated {len(changed)} files")
    for rel in changed:
        print(f"  - {rel}")


if __name__ == "__main__":
    main()
