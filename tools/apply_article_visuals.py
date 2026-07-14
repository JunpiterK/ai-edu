"""Add reusable concept visuals to blog articles that lack non-code figures."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VISUAL_DIR = ROOT / "blog" / "assets" / "visuals"


VISUALS = {
    "article-visual-template": {
        "title": "Article concept map",
        "subtitle": "Replace this starter schematic with a topic-specific photo, flowchart, architecture diagram, or scorecard.",
        "nodes": ["Problem", "Context", "Signal", "Decision", "Action", "Validation"],
    },
    "incident-response-flow": {
        "title": "Agent incident response loop",
        "subtitle": "Classify, contain, preserve, rollback, notify, prevent repeat failures.",
        "nodes": ["Detect", "Classify", "Contain", "Preserve trace", "Rollback tool", "Prevent repeat"],
    },
    "policy-control-matrix": {
        "title": "AI policy to plant controls",
        "subtitle": "Policy language becomes operational gates, owners, logs, and release evidence.",
        "nodes": ["Policy", "Risk", "Control", "Owner", "Evidence", "Review"],
    },
    "gpu-lab-architecture": {
        "title": "One-PC on-prem LLM lab",
        "subtitle": "A local GPU box can host models, RAG indexes, MCP tools, and agent experiments.",
        "nodes": ["Gaming GPU", "Local model", "RAG index", "MCP tools", "Agent loop", "Audit logs"],
    },
    "fab-glossary-map": {
        "title": "FAB AI vocabulary map",
        "subtitle": "Beginner terms connect equipment, wafers, recipes, traces, metrology, and actions.",
        "nodes": ["Tool", "Recipe", "Wafer", "Trace", "Metrology", "Action"],
    },
    "fab-equipment-data-sources": {
        "title": "FAB equipment data sources",
        "subtitle": "Useful AI starts by joining tool context, sensor traces, recipes, alarms, and metrology.",
        "nodes": ["Tool state", "Sensor traces", "Recipe step", "Alarms", "Metrology", "Engineer note"],
    },
    "fdc-golden-run": {
        "title": "Golden run vs fault trace",
        "subtitle": "FDC compares aligned sensor behavior against a healthy baseline and action bands.",
        "nodes": ["Recipe step", "Golden band", "Live trace", "Deviation", "Review", "Action level"],
    },
    "lang-modules-stack": {
        "title": "Lang implementation stack",
        "subtitle": "A maintainable app separates loaders, retrievers, prompts, tools, state, and tests.",
        "nodes": ["Loaders", "Retrievers", "Prompts", "Tools", "State graph", "Tests"],
    },
    "rag-eval-scorecard": {
        "title": "Plant RAG evaluation scorecard",
        "subtitle": "A release gate should measure retrieval, citation, refusal, freshness, and safety.",
        "nodes": ["Retrieval", "Citation", "Refusal", "Freshness", "Safety", "Regression"],
    },
    "rag-ingestion-flow": {
        "title": "Manufacturing RAG ingestion flow",
        "subtitle": "Documents move from source inventory to permission sync, parsing, chunking, indexing, and rollback.",
        "nodes": ["Inventory", "Permissions", "Parse", "Chunk", "Index", "Rollback"],
    },
    "sealed-rag-boundary": {
        "title": "Sealed RAG trust boundary",
        "subtitle": "Documents, embeddings, retrieval, generation, citations, and audit remain inside the plant network.",
        "nodes": ["Plant docs", "Parser", "Vector index", "Retriever", "Local LLM", "Citations"],
    },
    "takt-agent-flow": {
        "title": "Takt-aware agent escalation",
        "subtitle": "Assembly-line agents must respect cadence, Andon, approval, containment, and rework paths.",
        "nodes": ["Station event", "Takt check", "Andon", "Approval", "Containment", "Rework"],
    },
    "vin-wafer-timeline": {
        "title": "VIN genealogy vs wafer genealogy",
        "subtitle": "Both systems need a timeline, but the evidence objects and control actions differ.",
        "nodes": ["Product ID", "Station/tool", "Process event", "Inspection", "Quality action", "History query"],
    },
}


ARTICLE_VISUALS = {
    "agent-incident-response-runbook.html": (
        "incident-response-flow",
        "Incident response is easiest to follow as a loop: detect the event, classify severity, contain the tool action, preserve traces, roll back safely, and feed the lesson back into controls.",
        "Incident response를 loop로 보면 이해가 쉽습니다. event를 감지하고, 심각도를 분류하고, tool action을 contain하고, trace를 보존한 뒤 rollback과 재발 방지 control로 이어집니다.",
    ),
    "ai-policy-control-matrix.html": (
        "policy-control-matrix",
        "A useful AI policy is not just a document. It becomes a matrix of risks, controls, accountable owners, evidence, and review cadence.",
        "쓸모 있는 AI policy는 문서에서 끝나지 않습니다. risk, control, 담당 owner, evidence, review cadence가 연결된 matrix가 되어야 현장에서 작동합니다.",
    ),
    "consumer-gpu-onprem-llm-agent-lab.html": (
        "gpu-lab-architecture",
        "A home or lab GPU box is a miniature version of the plant stack: local model serving, private files, RAG indexes, MCP tools, agent loops, and audit logs.",
        "개인 PC나 lab GPU box는 작은 공장 AI stack입니다. local model serving, private files, RAG index, MCP tools, agent loop, audit log가 한 장비 안에서 연결됩니다.",
    ),
    "fab-ai-beginner-glossary.html": (
        "fab-glossary-map",
        "The beginner vocabulary becomes easier when every term is tied to a physical object, a data trail, or an engineering action.",
        "초심자 용어는 물리적 object, data trail, engineering action에 붙여서 보면 훨씬 빨리 익숙해집니다.",
    ),
    "fab-equipment-data-101.html": (
        "fab-equipment-data-sources",
        "Equipment AI gets useful only after tool state, traces, recipe steps, alarms, metrology, and engineer notes are joined with context.",
        "장비 AI는 tool state, trace, recipe step, alarm, metrology, engineer note가 context와 함께 연결될 때 비로소 쓸모가 생깁니다.",
    ),
    "fdc-from-first-principles.html": (
        "fdc-golden-run",
        "FDC is a comparison discipline: align the run by recipe step, compare live behavior to a golden band, and separate review signals from action signals.",
        "FDC는 비교의 기술입니다. run을 recipe step 기준으로 맞추고, live behavior를 golden band와 비교한 뒤 review signal과 action signal을 분리합니다.",
    ),
    "lang-modules-implementation-guide.html": (
        "lang-modules-stack",
        "The implementation guide is easier to navigate when the stack is seen as layers: loaders, retrievers, prompts, tools, state, and tests.",
        "구현 가이드는 loader, retriever, prompt, tool, state, test의 layer로 보면 훨씬 읽기 쉽습니다.",
    ),
    "plant-rag-evaluation-harness.html": (
        "rag-eval-scorecard",
        "A plant RAG release gate should score more than answer quality. Retrieval, citation, refusal, freshness, safety, and regression all need a seat at the table.",
        "현장 RAG release gate는 답변 품질만 보면 부족합니다. retrieval, citation, refusal, freshness, safety, regression을 함께 봐야 합니다.",
    ),
    "rag-ingestion-pipeline-manufacturing.html": (
        "rag-ingestion-flow",
        "RAG ingestion is the document supply chain: source inventory, permission sync, parsing, chunking, indexing, and rollback must be designed before launch.",
        "RAG ingestion은 문서의 supply chain입니다. source inventory, permission sync, parsing, chunking, indexing, rollback이 출시 전에 설계되어야 합니다.",
    ),
    "rag-over-sealed-documents.html": (
        "sealed-rag-boundary",
        "For sealed-document RAG, the key picture is the trust boundary: documents, embeddings, retrieval, generation, citations, and audit stay inside the network.",
        "폐쇄망 RAG의 핵심 그림은 trust boundary입니다. document, embedding, retrieval, generation, citation, audit가 모두 내부망에 머물러야 합니다.",
    ),
    "takt-aware-ai-agents-assembly-lines.html": (
        "takt-agent-flow",
        "A takt-aware agent is not just an LLM with tools. It must respect station cadence, Andon state, approval gates, containment, and rework paths.",
        "Takt-aware agent는 tool이 붙은 LLM이 아닙니다. station cadence, Andon state, approval gate, containment, rework path를 존중해야 합니다.",
    ),
    "vin-genealogy-vs-wafer-genealogy.html": (
        "vin-wafer-timeline",
        "Genealogy is a timeline of evidence. The FAB and automotive versions rhyme, but the IDs, events, inspections, and quality actions are different.",
        "Genealogy는 evidence timeline입니다. FAB과 자동차는 구조가 비슷하지만 ID, event, inspection, quality action은 다르게 설계해야 합니다.",
    ),
}


def svg_for(key: str, data: dict[str, object]) -> str:
    nodes = list(data["nodes"])
    x_positions = [100, 280, 460, 640, 820, 1000]
    y_positions = [325, 205, 325, 205, 325, 205]
    node_markup = []
    arrow_markup = []
    for idx, label in enumerate(nodes):
        x = x_positions[idx]
        y = y_positions[idx]
        node_markup.append(
            f'<g><rect class="node" x="{x - 74}" y="{y - 34}" width="148" height="68" rx="16"/>'
            f'<text class="node-text" x="{x}" y="{y + 5}">{escape(label)}</text></g>'
        )
        if idx < len(nodes) - 1:
            x2 = x_positions[idx + 1] - 92
            y2 = y_positions[idx + 1]
            arrow_markup.append(f'<path class="arrow" d="M{x + 92} {y} C{x + 130} {y}, {x2 - 38} {y2}, {x2} {y2}"/>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{key}-title {key}-desc" viewBox="0 0 1200 675">
  <title id="{key}-title">{escape(str(data["title"]))}</title>
  <desc id="{key}-desc">{escape(str(data["subtitle"]))}</desc>
  <style>
    svg {{ color-scheme: light dark; }}
    .bg {{ fill: #FAF9F5; }}
    .panel {{ fill: #FFFFFF; stroke: #DBD5C8; stroke-width: 1.5; }}
    .lane {{ fill: #F3F0E8; }}
    .node {{ fill: #FCFBF8; stroke: #D97757; stroke-width: 2; }}
    .arrow {{ fill: none; stroke: #6B6862; stroke-width: 3; marker-end: url(#arrowhead); opacity: .8; }}
    .title {{ fill: #1F1E1C; font: 600 38px Inter, Arial, sans-serif; }}
    .subtitle {{ fill: #6B6862; font: 400 21px Inter, Arial, sans-serif; }}
    .eyebrow {{ fill: #C15F3C; font: 700 14px Inter, Arial, sans-serif; letter-spacing: 3px; }}
    .node-text {{ fill: #1F1E1C; font: 700 18px Inter, Arial, sans-serif; text-anchor: middle; }}
    .chip {{ fill: #F6EAE1; stroke: #E5B69F; }}
    .chip-text {{ fill: #C15F3C; font: 700 13px Inter, Arial, sans-serif; text-anchor: middle; }}
    @media (prefers-color-scheme: dark) {{
      .bg {{ fill: #07111F; }}
      .panel {{ fill: #101D31; stroke: #344A68; }}
      .lane {{ fill: #0A1627; }}
      .node {{ fill: #0D1A2D; stroke: #F0A07F; }}
      .arrow {{ stroke: #91A4C0; }}
      .title {{ fill: #EEF4FF; }}
      .subtitle {{ fill: #C7D4E7; }}
      .eyebrow {{ fill: #FFBE9B; }}
      .node-text {{ fill: #EEF4FF; }}
      .chip {{ fill: #392335; stroke: #684A55; }}
      .chip-text {{ fill: #FFBE9B; }}
    }}
  </style>
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="currentColor"/>
    </marker>
  </defs>
  <rect class="bg" width="1200" height="675"/>
  <rect class="panel" x="42" y="42" width="1116" height="591" rx="32"/>
  <rect class="lane" x="76" y="158" width="1048" height="360" rx="28"/>
  <text class="eyebrow" x="94" y="104">AI EDU ARCHIVE VISUAL FIELD NOTE</text>
  <text class="title" x="94" y="145">{escape(str(data["title"]))}</text>
  <text class="subtitle" x="94" y="562">{escape(str(data["subtitle"]))}</text>
  {''.join(arrow_markup)}
  {''.join(node_markup)}
  <rect class="chip" x="94" y="584" width="190" height="34" rx="17"/>
  <text class="chip-text" x="189" y="606">schematic, not photo</text>
</svg>
"""


def figure_markup(filename: str, visual_key: str, caption: str, language: str) -> str:
    src = "../assets/visuals/" + visual_key + ".svg"
    if language == "ko":
        src = "../../assets/visuals/" + visual_key + ".svg"
    title = VISUALS[visual_key]["title"]
    label = "Figure." if language == "en" else "그림."
    return (
        '    <figure class="visual-figure media-figure media-figure--diagram">\n'
        f'      <img src="{src}" alt="{escape(str(title))}" loading="lazy" decoding="async">\n'
        f'      <figcaption><span class="figure-label">{label}</span> {escape(caption)}</figcaption>\n'
        "    </figure>\n\n"
    )


def update_article(path: Path, visual_key: str, caption: str, language: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if "visual-figure" in text:
        return False
    match = re.search(r'(<div\b[^>]*class="[^"]*\barticle-body\b[^"]*"[^>]*>\s*)', text)
    if not match:
        raise RuntimeError(f"article body marker missing: {path}")
    insert_at = match.end()
    text = text[:insert_at] + "\n" + figure_markup(path.name, visual_key, caption, language) + text[insert_at:]
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)
    for key, data in VISUALS.items():
        (VISUAL_DIR / f"{key}.svg").write_text(svg_for(key, data), encoding="utf-8")

    changed = []
    for slug, (visual_key, en_caption, ko_caption) in ARTICLE_VISUALS.items():
        en_path = ROOT / "blog" / "articles" / slug
        ko_path = ROOT / "blog" / "ko" / "articles" / slug
        if update_article(en_path, visual_key, en_caption, "en"):
            changed.append(en_path.relative_to(ROOT).as_posix())
        if update_article(ko_path, visual_key, ko_caption, "ko"):
            changed.append(ko_path.relative_to(ROOT).as_posix())

    print(f"wrote {len(VISUALS)} visuals")
    print(f"updated {len(changed)} articles")
    for rel in changed:
        print(f"  - {rel}")


if __name__ == "__main__":
    main()
