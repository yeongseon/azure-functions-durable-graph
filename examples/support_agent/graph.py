from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from azure_functions_durable_graph import ManifestBuilder, RouteDecision


class SupportState(BaseModel):
    user_message: str
    needs_human: bool = False
    approved: bool | None = None
    reviewer: str | None = None
    draft_response: str | None = None
    final_response: str | None = None
    tags: list[str] = Field(default_factory=list)


def classify_request(state: SupportState) -> dict[str, Any]:
    text = state.user_message.lower()
    tags = sorted(
        set(state.tags)
        | {
            "refund" if "refund" in text else "general",
        }
    )
    return {
        "needs_human": "refund" in text or "legal" in text,
        "tags": tags,
    }


def route_after_classify(state: SupportState) -> RouteDecision:
    if state.needs_human and state.approved is not True:
        return RouteDecision.wait_for_event(
            event_name="approval",
            resume_node="draft_reply",
            note="awaiting human approval",
        )
    return RouteDecision.next("draft_reply")


def merge_approval_event(state: SupportState, event_payload: Any) -> dict[str, Any]:
    payload = event_payload if isinstance(event_payload, dict) else {}
    return {
        "approved": bool(payload.get("approved")),
        "reviewer": payload.get("reviewer"),
    }


def draft_reply(state: SupportState) -> dict[str, Any]:
    if state.needs_human and not state.approved:
        return {
            "draft_response": "Your request requires manual review before we can proceed.",
        }

    if "refund" in state.tags:
        message = (
            "We have queued your refund review. "
            "A team member will validate the invoice and confirm next steps."
        )
    else:
        message = "Thanks for reaching out. We have prepared a response for your request."

    return {"draft_response": message}


def finalize_reply(state: SupportState) -> dict[str, Any]:
    suffix = f" Reviewer: {state.reviewer}." if state.reviewer else ""
    return {
        "final_response": f"{state.draft_response}{suffix}".strip(),
    }


builder = ManifestBuilder(
    graph_name="support_agent",
    state_model=SupportState,
    version="0.1.0",
    metadata={"example": True, "profile": "approval"},
)
builder.set_entrypoint("classify_request")
builder.add_node("classify_request", classify_request, route=route_after_classify)
builder.add_event_handler("approval", merge_approval_event)
builder.add_node("draft_reply", draft_reply, next_node="finalize_reply")
builder.add_node("finalize_reply", finalize_reply, terminal=True)

registration = builder.build()
