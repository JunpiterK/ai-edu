"""Deterministic controls that can be tested without an LLM runtime."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable


class ApprovalRejected(RuntimeError):
    """Raised when approval does not match the pending action."""


class AuditUnavailable(RuntimeError):
    """Raised when a required durable audit record cannot be written."""


class ToolContractError(ValueError):
    """Raised when tool arguments do not match the declared contract."""


def payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ApprovalContext:
    thread_id: str
    interrupt_id: str
    requester: str
    resource: str
    action: str
    payload_sha256: str
    reviewer: str
    expires_at: int


@dataclass(frozen=True)
class ApprovalToken:
    approval_id: str
    context: ApprovalContext
    signature: str


class ApprovalService:
    def __init__(self, secret: bytes) -> None:
        if len(secret) < 16:
            raise ValueError("approval secret must be at least 16 bytes")
        self._secret = secret
        self._issued = 0
        self._consumed: set[str] = set()

    def _signature(self, approval_id: str, context: ApprovalContext) -> str:
        claims = {"approval_id": approval_id, "context": asdict(context)}
        message = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()

    def issue(self, context: ApprovalContext) -> ApprovalToken:
        self._issued += 1
        approval_id = f"approval-{self._issued:04d}"
        return ApprovalToken(
            approval_id=approval_id,
            context=context,
            signature=self._signature(approval_id, context),
        )

    def verify(self, token: ApprovalToken, expected: ApprovalContext, now: int) -> None:
        if now >= token.context.expires_at:
            raise ApprovalRejected("approval expired")
        if token.context != expected:
            raise ApprovalRejected("approval is not bound to this pending action")
        if not hmac.compare_digest(token.signature, self._signature(token.approval_id, token.context)):
            raise ApprovalRejected("approval signature is invalid")

    def consume(self, token: ApprovalToken) -> None:
        if token.signature in self._consumed:
            raise ApprovalRejected("approval has already been consumed")
        self._consumed.add(token.signature)


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str
    revision: int
    status: str
    allowed_roles: frozenset[str]


class MockRetriever:
    """Small lexical fixture that tests filtering and withholding behavior."""

    def __init__(self, documents: Iterable[Document]) -> None:
        self._documents = tuple(documents)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[0-9A-Za-z가-힣_-]+", text.casefold()))

    def search(self, query: str, role: str, limit: int = 3) -> list[Document]:
        query_tokens = self._tokens(query)
        candidates = []
        for document in self._documents:
            if document.status != "current" or role not in document.allowed_roles:
                continue
            score = len(query_tokens & self._tokens(document.text))
            if score:
                candidates.append((score, document.revision, document.doc_id, document))
        candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return [item[3] for item in candidates[:limit]]


@dataclass(frozen=True)
class ToolSpec:
    required_args: frozenset[str]
    handler: Callable[[dict[str, Any]], Any]
    state_changing: bool = False


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        required_args: Iterable[str],
        handler: Callable[[dict[str, Any]], Any],
        *,
        state_changing: bool = False,
    ) -> None:
        self._tools[name] = ToolSpec(frozenset(required_args), handler, state_changing)

    def spec(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolContractError(f"unknown tool: {name}") from exc

    def invoke(self, name: str, arguments: dict[str, Any]) -> Any:
        spec = self.spec(name)
        supplied = frozenset(arguments)
        missing = spec.required_args - supplied
        unknown = supplied - spec.required_args
        if missing or unknown:
            raise ToolContractError(
                f"tool contract mismatch: missing={sorted(missing)}, unknown={sorted(unknown)}"
            )
        return spec.handler(arguments)


class AuditLog:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.records: list[dict[str, Any]] = []

    def write(self, event: dict[str, Any]) -> str:
        if not self.available:
            raise AuditUnavailable("durable audit sink unavailable")
        receipt = f"audit-{len(self.records) + 1:04d}"
        self.records.append({"receipt": receipt, **event})
        return receipt


class ScriptedModel:
    """A deterministic stand-in for model decisions, not model language quality."""

    def __init__(self, decisions: Iterable[dict[str, Any]], *, repeat_last: bool = False) -> None:
        self._decisions = tuple(decisions)
        if not self._decisions:
            raise ValueError("at least one scripted decision is required")
        self._repeat_last = repeat_last
        self._index = 0

    def next(self, observations: list[dict[str, Any]]) -> dict[str, Any]:
        del observations
        if self._index < len(self._decisions):
            decision = self._decisions[self._index]
            self._index += 1
            return decision
        if self._repeat_last:
            return self._decisions[-1]
        return {"type": "final", "answer": "SCRIPT_COMPLETE"}


class AgentRunner:
    def __init__(
        self,
        registry: ToolRegistry,
        approvals: ApprovalService,
        audit: AuditLog,
        *,
        max_steps: int = 4,
    ) -> None:
        self.registry = registry
        self.approvals = approvals
        self.audit = audit
        self.max_steps = max_steps

    def run(
        self,
        model: ScriptedModel,
        *,
        approval: ApprovalToken | None = None,
        approval_context: ApprovalContext | None = None,
        now: int = 0,
    ) -> dict[str, Any]:
        observations: list[dict[str, Any]] = []
        for step in range(1, self.max_steps + 1):
            decision = model.next(observations)
            if decision.get("type") == "final":
                return {
                    "status": "completed",
                    "steps": step,
                    "answer": decision.get("answer", ""),
                    "observations": observations,
                }
            if decision.get("type") != "tool":
                raise ValueError(f"unknown decision type: {decision.get('type')}")

            name = str(decision["name"])
            arguments = dict(decision.get("arguments", {}))
            spec = self.registry.spec(name)
            approval_receipt = None
            if spec.state_changing:
                if approval is None or approval_context is None:
                    raise ApprovalRejected("state-changing tool requires bound approval")
                if approval_context.action != name or approval_context.payload_sha256 != payload_hash(arguments):
                    raise ApprovalRejected("pending action does not match approval context")
                self.approvals.verify(approval, approval_context, now)
                approval_receipt = self.audit.write(
                    {
                        "event": "action_authorized",
                        "thread_id": approval_context.thread_id,
                        "interrupt_id": approval_context.interrupt_id,
                        "action": name,
                        "payload_sha256": approval_context.payload_sha256,
                        "reviewer": approval_context.reviewer,
                        "approval_id": approval.approval_id,
                    }
                )
                self.approvals.consume(approval)

            result = self.registry.invoke(name, arguments)
            observations.append(
                {"tool": name, "result": result, "approval_receipt": approval_receipt}
            )

        return {
            "status": "escalated",
            "steps": self.max_steps,
            "reason": "step_limit_reached",
            "observations": observations,
        }
