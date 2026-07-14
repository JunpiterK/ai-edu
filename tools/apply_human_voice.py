"""Add field-story blocks so technical articles read like lived engineering notes."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


STORIES: dict[str, tuple[str, str]] = {
    "why-air-gapped-llm-manufacturing.html": (
        "I did not start by thinking every model had to live inside the plant. At first, cloud APIs felt faster and honestly more convenient. The problem showed up when the examples stopped being toy examples: alarm history, process notes, recipe context, and engineer comments were exactly the things that made the answer useful, and exactly the things I did not want leaving the network. That is when the architecture changed from \"nice demo\" to \"keep the knowledge inside first, optimize later.\" Please let me be the one who learned that the slow way.",
        "처음부터 모든 모델을 공장 안에 넣어야 한다고 생각한 건 아닙니다. 솔직히 처음에는 cloud API가 빠르고 편했습니다. 그런데 예제가 toy가 아니게 되는 순간 문제가 보였습니다. alarm history, process note, recipe context, engineer comment가 답변을 쓸모 있게 만드는 핵심인데, 바로 그 데이터가 밖으로 나가면 안 되는 데이터였습니다. 그때부터 구조가 바뀌었습니다. 먼저 지식을 안에 두고, 속도와 편의성은 그 다음에 최적화하자. 이 실수는 제가 먼저 했으니 여러분은 조금 덜 돌아가셔도 됩니다.",
    ),
    "rag-over-sealed-documents.html": (
        "The first time I built this kind of RAG, I cared too much about the model and not enough about the documents. I thought a better embedding model would magically clean up messy SOPs. It did not. The turning point was boring but powerful: source ownership, revision labels, chunk boundaries, and citations. Once those were right, even a modest local model started giving answers engineers could actually inspect.",
        "처음 RAG를 만들 때는 저도 model과 embedding에 너무 신경을 썼습니다. 좋은 embedding model을 쓰면 지저분한 SOP도 알아서 잘 찾겠지 싶었죠. 아니었습니다. 전환점은 의외로 재미없는 것들이었습니다. source owner, revision label, chunk boundary, citation. 이게 맞아지니까 아주 화려한 모델이 아니어도 engineer가 확인 가능한 답변이 나오기 시작했습니다.",
    ),
    "rag-ingestion-pipeline-manufacturing.html": (
        "At first I treated ingestion like a one-time import job. Put the PDFs in, build the index, done. Then the plant did what plants always do: a revision changed, an old file survived in a shared folder, and two teams had different permission views. After that I stopped calling ingestion a script and started treating it like a production line with inspection, hold, release, and rollback.",
        "처음에는 ingestion을 한 번 하는 import 작업처럼 봤습니다. PDF 넣고, index 만들고, 끝. 그런데 현장은 늘 현장답게 움직입니다. revision이 바뀌고, shared folder에는 옛 파일이 살아 있고, 팀마다 permission view가 달랐습니다. 그 뒤로 ingestion을 script라고 부르지 않게 됐습니다. 검사, hold, release, rollback이 있는 하나의 생산라인처럼 다루는 게 맞았습니다.",
    ),
    "chunking-technical-docs.html": (
        "My first chunking mistake was cutting documents by size and feeling productive because the index built quickly. The retrieval looked fine until a warning table and its exception note landed in different chunks. That is the kind of bug that does not crash anything, but quietly teaches the model the wrong operating condition. Now I chunk around engineering meaning first, token size second.",
        "제가 처음 한 chunking 실수는 문서를 크기 기준으로 잘라놓고 index가 빨리 만들어졌다고 좋아한 겁니다. 검색도 얼핏 괜찮아 보였습니다. 그러다 warning table과 exception note가 서로 다른 chunk로 갈라진 걸 봤습니다. 이런 문제는 에러를 내지 않습니다. 대신 모델에게 조용히 잘못된 운전 조건을 가르칩니다. 그래서 지금은 token size보다 engineering meaning을 먼저 봅니다.",
    ),
    "embeddings-korean-technical.html": (
        "Korean-English technical text humbled me a bit. I expected a multilingual model to understand fab shorthand, mixed units, and half-English maintenance notes just because it was multilingual. It found words, but not always the right intent. The fix was not one magic model. It was test questions, domain phrases, metadata filters, and a willingness to admit that retrieval quality has to be measured in the language engineers actually use.",
        "한영 혼합 기술 문서는 생각보다 사람을 겸손하게 만듭니다. multilingual model이면 FAB 약어, 단위, 반쯤 영어로 적힌 maintenance note도 알아서 잘 이해할 줄 알았습니다. 단어는 찾는데 의도가 어긋나는 경우가 있더군요. 해결은 마법 같은 모델 하나가 아니었습니다. test question, domain phrase, metadata filter, 그리고 engineer가 실제로 쓰는 언어 기준으로 retrieval quality를 재는 습관이었습니다.",
    ),
    "choosing-open-models.html": (
        "I used to start model selection from leaderboard scores. It feels objective, so it is tempting. In a closed plant, that order is backwards. License, deployment footprint, GPU memory, update path, and operational support come before a benchmark win. A model that cannot be legally or practically operated inside your constraints is not a candidate; it is just an interesting screenshot.",
        "예전에는 model selection을 leaderboard score부터 봤습니다. 숫자가 있으니 객관적으로 느껴지거든요. 그런데 폐쇄망 현장에서는 순서가 반대였습니다. license, deployment footprint, GPU memory, update path, operational support가 benchmark보다 먼저입니다. 제약 안에서 합법적으로, 현실적으로 운영할 수 없는 모델은 후보가 아닙니다. 그냥 흥미로운 screenshot일 뿐입니다.",
    ),
    "onprem-llm-serving.html": (
        "Serving looked simple until more than one person used the endpoint. One user felt fast, three users felt different, and a batch job made the GPU look like it had changed personality. That was the moment I stopped asking only \"does it run?\" and started asking \"what happens under concurrency, restart, health check, and a bad prompt at 2 a.m.?\"",
        "Serving은 한 명이 쓸 때는 단순해 보입니다. 한 명은 빠르고, 세 명은 느낌이 달라지고, batch job 하나가 들어오면 GPU가 갑자기 다른 성격이 된 것처럼 보입니다. 그때부터 질문이 바뀌었습니다. '돌아가나요?'가 아니라 '동시 접속, 재시작, health check, 새벽 2시의 이상한 prompt에서도 버티나요?'를 봐야 했습니다.",
    ),
    "consumer-gpu-onprem-llm-agent-lab.html": (
        "A consumer GPU lab is where I like to make mistakes cheaply. The first setup is rarely elegant: drivers complain, model sizes are optimistic, ports collide, and the agent happily discovers files you forgot existed. That is good. Break it at home, write down the failure modes, and take only the hardened pattern into a serious plant network.",
        "개인 GPU lab은 싸게 실수하기 좋은 곳입니다. 처음 세팅은 대개 우아하지 않습니다. driver가 투덜대고, model size 계산은 낙관적이고, port는 충돌하고, agent는 내가 잊고 있던 파일까지 열심히 찾아냅니다. 오히려 좋습니다. 집에서 깨뜨리고, failure mode를 적고, 단단해진 pattern만 현장망으로 가져가면 됩니다.",
    ),
    "agents-mcp-mes.html": (
        "The first agent demo usually feels magical because it can call a tool. The second thought should be less magical: which tool, under whose permission, with what input schema, and where is the audit trail? I learned to treat MCP not as a convenience layer, but as the place where the plant says, \"you may read this, you may not write that, and every action leaves a trace.\"",
        "첫 agent demo는 tool을 호출하는 순간 꽤 마법처럼 보입니다. 그런데 두 번째 생각은 훨씬 덜 마법적이어야 합니다. 어떤 tool인지, 누구 권한인지, input schema는 무엇인지, audit trail은 어디 남는지 봐야 합니다. 그래서 MCP를 편의 layer로만 보지 않게 됐습니다. 현장이 '이건 읽어도 되고, 저건 쓰면 안 되고, 모든 action은 trace를 남긴다'고 말하는 경계로 봐야 합니다.",
    ),
    "langchain-tools-agents.html": (
        "I used to get excited when an agent picked the right tool once. Then I watched the same pattern fail when the tool description was vague, the input was underspecified, or the result needed human approval. The real work is not making the agent clever for one demo. It is making the tool contract boring enough that the agent cannot improvise around safety.",
        "예전에는 agent가 tool을 한 번 제대로 고르면 꽤 신났습니다. 그런데 tool description이 애매하거나, input이 덜 정의됐거나, 결과에 human approval이 필요한 순간 같은 패턴이 무너졌습니다. 진짜 일은 demo 한 번을 똑똑하게 만드는 게 아니었습니다. agent가 safety를 즉흥적으로 우회하지 못하도록 tool contract를 지루할 정도로 명확하게 만드는 일이었습니다.",
    ),
    "langgraph-stateful-workflows.html": (
        "Statefulness did not feel important until I had to pause an agent for approval and resume it without losing why it made the recommendation. Stateless demos are clean; real workflows are interrupted. LangGraph started to make sense when I stopped thinking about chains and started thinking about shift handoff, review queues, and unfinished decisions.",
        "상태 저장은 approval 때문에 agent를 멈췄다가, 왜 그런 추천을 했는지 잃지 않고 다시 이어가야 할 때 중요해졌습니다. Stateless demo는 깔끔합니다. 실제 workflow는 중간에 끊깁니다. LangGraph는 chain이 아니라 shift handoff, review queue, 아직 끝나지 않은 decision으로 생각할 때 이해가 빨라졌습니다.",
    ),
    "langchain-core-explained.html": (
        "At first LCEL felt like syntax to memorize. It became useful only after I mapped it to a very plain habit: take input, shape it, retrieve context, call the model, parse the result, and test the edges. Once I stopped treating it as framework magic, the code got smaller and the debugging got less dramatic.",
        "처음 LCEL은 외워야 할 syntax처럼 느껴졌습니다. 그런데 input을 받고, 모양을 맞추고, context를 찾고, model을 호출하고, result를 parsing하고, edge case를 test한다는 평범한 습관으로 보면 훨씬 쉬워졌습니다. framework magic으로 보지 않으니 코드도 줄고 debugging도 덜 요란해졌습니다.",
    ),
    "langchain-rag-components.html": (
        "RAG components looked modular on the diagram, but in practice each part leaks assumptions into the next one. Loader choices affect chunks, chunks affect retrieval, retrieval affects prompts, prompts affect evaluation. I stopped swapping components casually after realizing one small parser change could make yesterday's good answer disappear.",
        "RAG component는 그림으로 보면 깔끔하게 modular합니다. 실제로는 각 부품의 가정이 다음 단계로 새어 나갑니다. loader 선택이 chunk에 영향을 주고, chunk가 retrieval에, retrieval이 prompt에, prompt가 evaluation에 영향을 줍니다. 작은 parser 변경 하나로 어제 잘 나오던 답이 사라지는 걸 보고 나서는 component를 가볍게 바꾸지 않게 됐습니다.",
    ),
    "lang-modules-implementation-guide.html": (
        "The codebase got better when I stopped putting everything into one impressive notebook. Notebooks are great for learning, but production memory needs modules: loaders, retrievers, prompts, tools, policies, and tests. The boring file boundaries are what let you fix one part without shaking the whole system.",
        "모든 것을 멋진 notebook 하나에 넣는 걸 멈추고 나서 코드가 좋아졌습니다. notebook은 학습에는 좋지만, 운영되는 지식 시스템에는 module이 필요합니다. loader, retriever, prompt, tool, policy, test. 지루한 파일 경계가 있어야 한 부분을 고쳐도 전체가 흔들리지 않습니다.",
    ),
    "hybrid-retrieval-vector-graph.html": (
        "I wanted vector search to be enough. It is elegant and it feels modern. But plant questions often ask for relationships: this chamber, that recipe, this time window, that failure family. Vector search finds similar language; graph and filters keep the answer inside the right engineering boundary.",
        "처음에는 vector search 하나로 충분하길 바랐습니다. 우아하고 modern해 보이니까요. 그런데 현장 질문은 관계를 묻는 경우가 많습니다. 이 chamber, 저 recipe, 이 time window, 그 failure family. Vector search는 비슷한 언어를 찾고, graph와 filter는 답을 올바른 engineering boundary 안에 붙잡아 둡니다.",
    ),
    "knowledge-graph-process.html": (
        "Knowledge graphs sounded abstract until I tried to answer a simple excursion question: which lots, tools, recipes, wafers, alarms, and metrology results are actually connected? The graph is not there to look academic. It is there because engineers investigate by following edges, even when they do not call them edges.",
        "Knowledge graph는 처음엔 추상적으로 들립니다. 그런데 excursion 질문 하나만 해도 바로 현실이 됩니다. 어떤 lot, tool, recipe, wafer, alarm, metrology result가 실제로 연결되어 있나? Graph는 학술적으로 보이려고 있는 게 아닙니다. Engineer는 이름만 edge라고 안 부를 뿐, 늘 연결을 따라 조사합니다.",
    ),
    "knowledge-asset-roadmap.html": (
        "The roadmap changed after I saw teams try to jump straight to agents. Agents are attractive, but if the documents are stale, ownership is unclear, and evaluation is missing, the agent only automates confusion. The order that worked better was humbler: inventory, retrieval, evaluation, governance, then action.",
        "팀들이 바로 agent로 뛰어드는 걸 보면서 roadmap 생각이 바뀌었습니다. Agent는 매력적입니다. 하지만 문서가 오래됐고, owner가 불분명하고, evaluation이 없으면 agent는 혼란을 자동화할 뿐입니다. 더 잘 맞았던 순서는 훨씬 겸손했습니다. inventory, retrieval, evaluation, governance, 그리고 그 다음 action입니다.",
    ),
    "hitl-mlops-onprem.html": (
        "Human-in-the-loop sounded like a checkbox until the first real disagreement. The model recommended one thing, the engineer knew the tool history said another, and the question became: who can override, what gets logged, and how do we learn from that override? HITL is not slowing AI down. It is how the system earns permission to keep running.",
        "Human-in-the-loop는 처음엔 체크박스처럼 들립니다. 그런데 실제 disagreement가 나오면 달라집니다. 모델은 한 가지를 추천하고, engineer는 tool history 때문에 다르게 봅니다. 그때 질문은 누가 override할 수 있는지, 무엇이 log로 남는지, 그 override에서 어떻게 배울지입니다. HITL은 AI를 느리게 하는 장치가 아닙니다. 시스템이 계속 운영될 자격을 얻는 방법입니다.",
    ),
    "plant-rag-evaluation-harness.html": (
        "I learned not to trust a RAG system just because five hand-picked questions looked good. The sixth question, the stale revision, or the question that should be refused is where the truth appears. A harness is not paperwork. It is the little test bench that saves you from finding the bug in front of a process owner.",
        "저는 hand-picked 질문 다섯 개가 잘 나온다고 RAG를 믿으면 안 된다는 걸 배웠습니다. 여섯 번째 질문, 오래된 revision, 거절해야 하는 질문에서 진짜 실력이 드러납니다. Harness는 문서작업이 아닙니다. process owner 앞에서 버그를 발견하지 않게 해주는 작은 test bench입니다.",
    ),
    "ai-policy-control-matrix.html": (
        "Policy work felt vague until I forced each sentence to become a control. \"Protect confidential data\" is a wish. \"This role can retrieve these sources, this action requires approval, this log is retained for review\" is a system. The matrix is where nice principles either become operational or quietly stay decorative.",
        "Policy 문장은 control로 바꾸기 전까지는 꽤 모호합니다. '기밀 데이터를 보호한다'는 바람입니다. '이 role은 이 source만 retrieve하고, 이 action은 approval이 필요하며, 이 log는 review를 위해 보관한다'는 시스템입니다. Matrix는 좋은 원칙이 실제 운영이 되는지, 아니면 장식으로 남는지 갈리는 곳입니다.",
    ),
    "agent-incident-response-runbook.html": (
        "The uncomfortable part of agent work is admitting that incidents will happen. A tool call will be wrong, a permission rule will be too loose, or a prompt will route the case badly. The runbook is not pessimism. It is respect for production. If we know how to contain and learn from failure, we can build more confidently.",
        "Agent 작업에서 불편하지만 인정해야 하는 부분은 incident가 생긴다는 겁니다. tool call이 틀릴 수 있고, permission rule이 느슨할 수 있고, prompt routing이 빗나갈 수 있습니다. Runbook은 비관론이 아닙니다. 운영 환경에 대한 예의입니다. 실패를 contain하고 배울 방법이 있으면 오히려 더 자신 있게 만들 수 있습니다.",
    ),
    "fdc-from-first-principles.html": (
        "FDC taught me that a beautiful chart can still be operationally useless. If the trace is not aligned to recipe step, if the golden run is poorly chosen, or if every deviation has the same severity, the engineer gets noise. The fix was not a fancier model first. It was better context, better baselines, and fewer careless alarms.",
        "FDC를 하다 보면 예쁜 chart가 운영에는 쓸모없을 수 있다는 걸 배웁니다. trace가 recipe step에 맞지 않거나, golden run 선정이 엉성하거나, 모든 deviation이 같은 severity로 뜨면 engineer는 noise를 받습니다. 먼저 필요했던 건 더 멋진 모델이 아니라 context, baseline, 그리고 부주의한 alarm을 줄이는 일이었습니다.",
    ),
    "fab-equipment-data-101.html": (
        "The first surprise with equipment data is how often \"we have the data\" does not mean \"we can join the data.\" Tool traces, alarms, recipes, maintenance notes, and metrology may all exist, but not in a shape one question can use. Most successful AI work starts with unglamorous joining work. Sorry, but the spreadsheet pain was real.",
        "장비 데이터에서 처음 놀라는 지점은 '데이터가 있다'와 '데이터를 연결할 수 있다'가 다르다는 겁니다. tool trace, alarm, recipe, maintenance note, metrology가 다 있어도 하나의 질문에 쓸 수 있는 모양이 아닐 때가 많습니다. 성공하는 AI 작업은 대개 화려하지 않은 join 작업에서 시작합니다. 아쉽지만 Excel 고통은 실제였습니다.",
    ),
    "fab-ai-beginner-glossary.html": (
        "I wrote this kind of glossary because beginners often get lost before the hard part even begins. The words sound familiar, but RAG, agents, guardrails, evaluation, and audit mean very specific things in a plant. If you learn the words with factory examples first, the architecture stops feeling like alphabet soup.",
        "이런 glossary가 필요한 이유는 초심자가 어려운 부분에 들어가기 전에 용어에서 먼저 길을 잃기 때문입니다. RAG, agent, guardrail, evaluation, audit이라는 말은 익숙해 보여도 공장에서는 꽤 구체적인 의미를 가집니다. 공장 예시로 먼저 익히면 구조가 알파벳 수프처럼 보이지 않습니다.",
    ),
    "automotive-ai-vs-fab-ai.html": (
        "I initially tried to reuse fab mental models too aggressively for automotive AI. That helped a little, then started to mislead. A wafer does not move like a VIN, a chamber does not behave like a station, and takt time changes the urgency of every decision. The lesson was simple: borrow discipline from fabs, but respect the physics of the line.",
        "처음에는 FAB에서 쓰던 사고방식을 자동차 AI에 너무 많이 가져오려 했습니다. 조금은 도움이 됐지만 곧 헷갈리기 시작했습니다. wafer는 VIN처럼 움직이지 않고, chamber는 station처럼 행동하지 않으며, takt time은 모든 decision의 긴급도를 바꿉니다. 교훈은 단순했습니다. FAB의 discipline은 빌리되, 라인의 물리를 존중해야 합니다.",
    ),
    "takt-aware-ai-agents-assembly-lines.html": (
        "The mistake I want you to avoid is designing the agent as if the line can wait. It usually cannot. Some decisions must happen inside takt, some must escalate through Andon, and some should wait for engineering review. If the agent does not understand that timing difference, it will either be too timid or dangerously eager.",
        "피하셨으면 하는 실수는 line이 기다려줄 거라고 생각하고 agent를 설계하는 겁니다. 대개 기다려주지 않습니다. 어떤 decision은 takt 안에서 일어나야 하고, 어떤 것은 Andon으로 escalate되어야 하며, 어떤 것은 engineering review까지 기다려야 합니다. 이 timing 차이를 모르면 agent는 너무 소심하거나, 반대로 위험하게 성급해집니다.",
    ),
    "vin-genealogy-vs-wafer-genealogy.html": (
        "Genealogy looked like a database problem until I had to answer a quality question quickly. Then it became an investigation problem. The hard part was not storing events. It was making sure the timeline could explain why this VIN or wafer belongs in the suspect set and why that other one does not.",
        "Genealogy는 처음엔 database 문제처럼 보입니다. 그런데 품질 질문에 빨리 답해야 하는 순간 investigation 문제가 됩니다. 어려운 건 event를 저장하는 일이 아니었습니다. 왜 이 VIN 또는 wafer가 suspect set에 들어가고, 왜 저 대상은 빠지는지를 timeline이 설명할 수 있어야 했습니다.",
    ),
}


def story_block(text: str, lang: str) -> str:
    label = "Field story" if lang == "en" else "현장 시행착오"
    return (
        '    <div class="field-story">\n'
        f'      <span class="note-k">{label}</span>\n'
        f"      <p>{escape(text)}</p>\n"
        "    </div>\n\n"
    )


def insert_story(path: Path, text: str, lang: str) -> bool:
    html = path.read_text(encoding="utf-8")
    if "field-story" in html:
        return False

    visual = re.search(r'(<figure\b[^>]*class="[^"]*\bvisual-figure\b[^"]*"[^>]*>.*?</figure>\s*)', html, re.DOTALL)
    if visual:
        insert_at = visual.end()
    else:
        body = re.search(r'(<div\b[^>]*class="[^"]*\barticle-body\b[^"]*"[^>]*>\s*)', html)
        if not body:
            raise RuntimeError(f"article body marker missing: {path}")
        insert_at = body.end()

    html = html[:insert_at] + story_block(text, lang) + html[insert_at:]
    path.write_text(html, encoding="utf-8")
    return True


def main() -> None:
    changed = []
    for slug, (en_text, ko_text) in STORIES.items():
        en_path = ROOT / "blog" / "articles" / slug
        ko_path = ROOT / "blog" / "ko" / "articles" / slug
        if insert_story(en_path, en_text, "en"):
            changed.append(en_path.relative_to(ROOT).as_posix())
        if insert_story(ko_path, ko_text, "ko"):
            changed.append(ko_path.relative_to(ROOT).as_posix())

    print(f"updated {len(changed)} articles")
    for rel in changed:
        print(f"  - {rel}")


if __name__ == "__main__":
    main()
