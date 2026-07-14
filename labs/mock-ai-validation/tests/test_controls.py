from __future__ import annotations

import unittest

from mock_ai_lab import (
    AgentRunner,
    ApprovalContext,
    ApprovalService,
    AuditLog,
    Document,
    MockRetriever,
    ScriptedModel,
    ToolRegistry,
    payload_hash,
)
from mock_ai_lab.core import ApprovalRejected, AuditUnavailable, ToolContractError


NOW = 1_700_000_000


def approval_context(arguments: dict[str, str], **overrides: str) -> ApprovalContext:
    values = {
        "thread_id": "thread-17",
        "interrupt_id": "interrupt-3",
        "requester": "engineer-42",
        "resource": "ticket-system/module-a",
        "action": "create_ticket",
        "payload_sha256": payload_hash(arguments),
        "reviewer": "shift-lead-7",
        "expires_at": NOW + 300,
    }
    values.update(overrides)
    return ApprovalContext(**values)


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.retriever = MockRetriever(
            [
                Document("sop-r7", "E-1420 chamber pressure response", 7, "superseded", frozenset({"engineer"})),
                Document("sop-r8", "E-1420 chamber pressure response purge check", 8, "current", frozenset({"engineer"})),
                Document("admin-note", "E-1420 chamber pressure security note", 2, "current", frozenset({"admin"})),
            ]
        )

    def test_only_current_authorized_documents_are_returned(self) -> None:
        hits = self.retriever.search("E-1420 chamber pressure", "engineer")
        self.assertEqual([item.doc_id for item in hits], ["sop-r8"])

    def test_missing_authorized_source_withholds_result(self) -> None:
        hits = self.retriever.search("security note", "engineer")
        self.assertEqual(hits, [])


class ControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actions: list[dict[str, str]] = []
        self.arguments = {"module": "A", "summary": "Inspect pressure trace"}
        self.registry = ToolRegistry()
        self.registry.register(
            "create_ticket",
            {"module", "summary"},
            lambda arguments: self.actions.append(arguments) or "TICKET-001",
            state_changing=True,
        )
        self.registry.register(
            "read_alarm",
            {"alarm_id"},
            lambda arguments: {"alarm_id": arguments["alarm_id"], "state": "active"},
        )
        self.approvals = ApprovalService(b"local-lab-secret-2026")

    def test_tool_contract_rejects_unknown_arguments(self) -> None:
        with self.assertRaises(ToolContractError):
            self.registry.invoke("read_alarm", {"alarm_id": "E-1420", "sql": "select *"})

    def test_approval_cannot_move_to_another_thread(self) -> None:
        issued_context = approval_context(self.arguments)
        token = self.approvals.issue(issued_context)
        transferred = approval_context(self.arguments, thread_id="thread-99")
        with self.assertRaises(ApprovalRejected):
            self.approvals.verify(token, transferred, NOW)

    def test_audit_outage_blocks_state_change(self) -> None:
        context = approval_context(self.arguments)
        runner = AgentRunner(self.registry, self.approvals, AuditLog(available=False))
        model = ScriptedModel([{"type": "tool", "name": "create_ticket", "arguments": self.arguments}])
        with self.assertRaises(AuditUnavailable):
            runner.run(model, approval=self.approvals.issue(context), approval_context=context, now=NOW)
        self.assertEqual(self.actions, [])

    def test_consumed_approval_cannot_execute_twice(self) -> None:
        context = approval_context(self.arguments)
        token = self.approvals.issue(context)
        runner = AgentRunner(self.registry, self.approvals, AuditLog())
        first = ScriptedModel([{"type": "tool", "name": "create_ticket", "arguments": self.arguments}])
        runner.run(first, approval=token, approval_context=context, now=NOW)
        replay = ScriptedModel([{"type": "tool", "name": "create_ticket", "arguments": self.arguments}])
        with self.assertRaises(ApprovalRejected):
            runner.run(replay, approval=token, approval_context=context, now=NOW)
        self.assertEqual(len(self.actions), 1)

    def test_step_limit_escalates_instead_of_returning_tool_output(self) -> None:
        runner = AgentRunner(self.registry, self.approvals, AuditLog(), max_steps=3)
        model = ScriptedModel(
            [{"type": "tool", "name": "read_alarm", "arguments": {"alarm_id": "E-1420"}}],
            repeat_last=True,
        )
        result = runner.run(model, now=NOW)
        self.assertEqual(result["status"], "escalated")
        self.assertEqual(result["reason"], "step_limit_reached")
        self.assertNotIn("answer", result)

    def test_bound_approval_executes_once_and_records_receipt(self) -> None:
        audit = AuditLog()
        context = approval_context(self.arguments)
        runner = AgentRunner(self.registry, self.approvals, audit)
        model = ScriptedModel(
            [
                {"type": "tool", "name": "create_ticket", "arguments": self.arguments},
                {"type": "final", "answer": "Ticket draft submitted through the approved route."},
            ]
        )
        result = runner.run(model, approval=self.approvals.issue(context), approval_context=context, now=NOW)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(self.actions), 1)
        self.assertEqual(result["observations"][0]["approval_receipt"], "audit-0001")
        self.assertEqual(audit.records[0]["event"], "action_authorized")


if __name__ == "__main__":
    unittest.main()
