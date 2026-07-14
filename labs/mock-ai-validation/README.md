# Mock AI Validation Lab

This lab validates AI workflow controls on a low-spec PC without downloading a model or installing third-party packages.

It tests:

- current-revision and role filtering before retrieval;
- exact tool argument contracts;
- approval binding to thread, interrupt, requester, resource, action, and payload;
- fail-closed behavior when the durable audit sink is unavailable;
- explicit escalation when an agent loop reaches its step limit;
- one successful, approved state-changing action.

It does **not** test model quality, hallucination rate, embedding quality, GPU throughput, or real LangChain/LangGraph integration.

## Requirements

- Python 3.10 or newer
- No GPU
- No network connection
- No `pip install`

## Run

From this directory:

```powershell
python -m unittest discover -s tests -v
python run_demo.py
```

The demo writes `artifacts/latest_run.json`. Delete or archive that file before a new controlled run if your procedure requires a clean evidence folder.

## Reading the result

`completed` means the scripted workflow satisfied the control path under test. `escalated` means the bounded loop stopped without pretending that its last tool observation was a final answer. An exception in a negative test is an expected pass only when the test names the rejection condition.

