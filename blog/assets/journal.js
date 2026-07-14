(function(){
  var index = document.getElementById('articleIndex');
  if(!index) return;

  var isKo = document.documentElement.lang === 'ko';
  var categories = {
    all: {
      match: null,
      ko: ['전체 아카이브', '모든 실무 글', '왼쪽에서 카테고리를 선택하면 해당 분야의 글만 모아 볼 수 있습니다.'],
      en: ['Complete archive', 'All field articles', 'Choose a category on the left to focus the archive on that field.']
    },
    automotive: {
      match: ['automotive-ai-vs-fab-ai.html', 'vin-genealogy-vs-wafer-genealogy.html', 'takt-aware-ai-agents-assembly-lines.html'],
      ko: ['자동차 제조', '자동차 AI와 로봇', 'VIN 이력, 로봇 셀, 택트 타임, 비전 검사와 안전 제어를 자동차 생산 흐름에 맞춰 다룹니다.'],
      en: ['Automotive manufacturing', 'Automotive AI & Robotics', 'VIN genealogy, robot cells, takt time, vision inspection, and safety controls for vehicle production.']
    },
    fab: {
      match: ['fab-equipment-data-101.html', 'fdc-from-first-principles.html', 'fab-ai-beginner-glossary.html', 'knowledge-asset-roadmap.html'],
      ko: ['반도체와 디스플레이 FAB', 'FAB AI 기초', '장비 데이터와 FDC부터 레시피 맥락, 계측, 현장 용어와 지식 자산화까지 기초를 다집니다.'],
      en: ['Semiconductor and display fabs', 'FAB AI Foundations', 'Build the foundation from equipment data and FDC to recipe context, metrology, field vocabulary, and knowledge assets.']
    },
    rag: {
      match: ['rag-over-sealed-documents.html', 'rag-ingestion-pipeline-manufacturing.html', 'chunking-technical-docs.html', 'plant-rag-evaluation-harness.html', 'knowledge-graph-process.html', 'hybrid-retrieval-vector-graph.html', 'embeddings-korean-technical.html'],
      ko: ['검색과 지식화', 'RAG와 지식 시스템', 'SOP, 매뉴얼, 로그와 기술 노트를 출처가 있는 답변으로 바꾸는 수집·검색·평가 방법을 정리합니다.'],
      en: ['Retrieval and knowledge', 'RAG & Knowledge Systems', 'Turn SOPs, manuals, logs, and engineering notes into cited answers with disciplined ingestion, retrieval, and evaluation.']
    },
    agents: {
      match: ['agents-mcp-mes.html', 'ai-policy-control-matrix.html', 'agent-incident-response-runbook.html', 'hitl-mlops-onprem.html'],
      ko: ['행동하는 AI의 통제', 'Agent, MCP와 현장 제어', '답변을 넘어 행동하는 AI에 필요한 권한, 사람의 승인, 감사 기록, 복구와 사고 대응을 다룹니다.'],
      en: ['Control for acting AI', 'Agents, MCP & Plant Controls', 'Permissions, human approval, audit trails, rollback, and incident response for AI that moves beyond answers.']
    },
    onprem: {
      match: ['why-air-gapped-llm-manufacturing.html', 'onprem-llm-serving.html', 'choosing-open-models.html', 'consumer-gpu-onprem-llm-agent-lab.html'],
      ko: ['보안 제조 인프라', '온프렘 LLM 운영', '공정 데이터가 외부로 나가지 않는 환경에서 모델 선택, GPU 용량 산정, 서빙과 운영 통제를 연결합니다.'],
      en: ['Secure manufacturing infrastructure', 'On-Prem LLM Operations', 'Connect model choice, GPU sizing, serving, and governance where process data cannot leave the plant.']
    },
    python: {
      match: ['lang-modules-implementation-guide.html', 'langchain-core-explained.html', 'langchain-rag-components.html', 'langchain-tools-agents.html', 'langgraph-stateful-workflows.html'],
      ko: ['실행 가능한 구현', 'Python, LangChain과 LangGraph', '프롬프트와 검색기부터 도구, 상태 그래프와 Agent 흐름까지 실제 코드로 구현하는 순서를 다룹니다.'],
      en: ['Runnable implementation', 'Python, LangChain & LangGraph', 'Move from prompts and retrievers to tools, state graphs, and agent workflows in runnable code.']
    },
    fieldai: {
      match: ['generative-ai-field-engineer-workflow.html', 'mock-ai-validation-low-spec-pc.html'],
      ko: ['비개발 엔지니어의 실전', '생성형 AI 현장 활용', '공정 엔지니어가 보안 경계를 지키면서 생성형 AI와 Python을 업무 도구로 만든 과정을 기록합니다.'],
      en: ['Field practice for non-developers', 'Generative AI at Work', 'How a process engineer turned generative AI and Python into work tools while respecting security boundaries.']
    }
  };

  var routeMap = {
    'automotive-ai-robotics.html': 'automotive',
    'fab-ai-foundations.html': 'fab',
    'rag-knowledge-systems.html': 'rag',
    'agents-mcp-controls.html': 'agents',
    'onprem-llm-operations.html': 'onprem',
    'python-langchain-langgraph.html': 'python',
    'generative-ai-field-work.html': 'fieldai',
    'ai-categories.html': 'all'
  };
  var filterKeys = {
    auto: 'automotive',
    mfg: 'fab',
    rag: 'rag',
    agents: 'agents',
    onprem: 'onprem',
    python: 'python',
    fieldai: 'fieldai',
    all: 'all'
  };
  var legacyKeys = {
    automotive: 'auto',
    fab: 'mfg',
    rag: 'rag',
    agents: 'agents',
    onprem: 'onprem',
    python: 'python',
    fieldai: 'fieldai',
    all: 'all'
  };

  var posts = Array.prototype.slice.call(index.querySelectorAll('.post'));
  if(!posts.length) return;

  var title = document.getElementById('catalogTitle');
  var eyebrow = document.getElementById('catalogEyebrow');
  var description = document.getElementById('catalogDescription');
  var count = document.getElementById('catalogCount');
  var empty = document.getElementById('emptyNote');
  var railLinks = document.querySelectorAll('.journal-rail a');
  var chips = document.querySelectorAll('.chip');

  function categoryForLink(link){
    var href = (link.getAttribute('href') || '').split('/').pop().split('?')[0];
    return routeMap[href] || null;
  }

  function applyCategory(key, updateUrl){
    var category = categories[key] || categories.all;
    var copy = isKo ? category.ko : category.en;
    var shown = 0;

    posts.forEach(function(post){
      var href = (post.getAttribute('href') || '').split('/').pop().split('?')[0];
      var visible = !category.match || category.match.indexOf(href) !== -1;
      post.closest('li').hidden = !visible;
      if(visible) shown++;
    });

    eyebrow.textContent = copy[0];
    title.textContent = copy[1];
    description.textContent = copy[2];
    count.textContent = isKo ? shown + '개 글' : shown + (shown === 1 ? ' article' : ' articles');
    empty.style.display = shown ? 'none' : 'block';

    railLinks.forEach(function(link){
      var linkKey = categoryForLink(link);
      if(!linkKey) return;
      if(linkKey === key) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });

    chips.forEach(function(chip){
      chip.setAttribute('aria-pressed', chip.getAttribute('data-filter') === legacyKeys[key] ? 'true' : 'false');
    });

    if(updateUrl && window.history && window.history.replaceState){
      var url = new URL(window.location.href);
      if(key === 'all') url.searchParams.delete('category');
      else url.searchParams.set('category', key);
      window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
  }

  railLinks.forEach(function(link){
    var key = categoryForLink(link);
    if(!key) return;
    link.addEventListener('click', function(event){
      event.preventDefault();
      applyCategory(key, true);
      title.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
  });

  chips.forEach(function(chip){
    var key = filterKeys[chip.getAttribute('data-filter')];
    if(!key) return;
    chip.addEventListener('click', function(){ applyCategory(key, true); });
  });

  var initial = new URL(window.location.href).searchParams.get('category');
  applyCategory(categories[initial] ? initial : 'all', false);
})();
