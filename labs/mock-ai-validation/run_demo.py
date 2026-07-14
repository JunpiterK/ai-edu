from __future__ import annotations

import json
from pathlib import Path

from mock_ai_lab import AgentRunner, ApprovalService, AuditLog, ScriptedModel, ToolRegistry


def main() -> None:
    registry = ToolRegistry()
    registry.register(
        "read_alarm",
        {"alarm_id"},
        lambda arguments: {"alarm_id": arguments["alarm_id"], "state": "active"},
    )
    runner = AgentRunner(
        registry,
        ApprovalService(b"local-demo-secret-2026"),
        AuditLog(),
        max_steps=3,
    )
    model = ScriptedModel(
        [{"type": "tool", "name": "read_alarm", "arguments": {"alarm_id": "E-1420"}}],
        repeat_last=True,
    )
    result = runner.run(model)
    output = Path(__file__).parent / "artifacts" / "latest_run.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"artifact: {output}")


if __name__ == "__main__":
    main()

