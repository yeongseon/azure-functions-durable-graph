"""Smoke tests for the support_agent example."""

from __future__ import annotations

import pytest

from azure_functions_durable_graph import RouteDecision
from azure_functions_durable_graph.registry import GraphRegistry
from examples.support_agent.graph import (
    SupportState,
    registration,
    route_after_classify,
)


def test_support_agent_registration_builds() -> None:
    """The support_agent example should produce a valid registration."""
    assert registration.manifest.graph_name == "support_agent"
    assert registration.manifest.entrypoint == "classify_request"
    assert "classify_request" in registration.manifest.nodes
    assert "draft_reply" in registration.manifest.nodes
    assert "finalize_reply" in registration.manifest.nodes
    assert registration.manifest.graph_hash


def test_support_agent_route_needs_human() -> None:
    """Route handler should return wait_for_event when needs_human=True."""
    state = SupportState(user_message="I need a refund", needs_human=True)
    decision = route_after_classify(state)
    assert isinstance(decision, RouteDecision)
    assert decision.action.value == "wait_for_event"
    assert decision.event_name == "approval"
    assert decision.resume_node == "draft_reply"


def test_support_agent_route_no_human() -> None:
    """Route handler should go to draft_reply when no human needed."""
    state = SupportState(user_message="hello", needs_human=False)
    decision = route_after_classify(state)
    assert isinstance(decision, RouteDecision)
    assert decision.action.value == "next"
    assert decision.next_node == "draft_reply"


@pytest.mark.asyncio
async def test_support_agent_full_flow() -> None:
    """Smoke test: register and execute nodes through the registry."""
    reg = GraphRegistry()
    reg.register(registration)
    graph_hash = registration.manifest.graph_hash

    # Execute classify_request node
    state = await reg.execute_node(
        "support_agent", graph_hash, "classify_request", {"user_message": "I need a refund"}
    )
    assert state["needs_human"] is True
    assert "refund" in state["tags"]

    # Execute draft_reply node
    state = await reg.execute_node("support_agent", graph_hash, "draft_reply", state)
    assert state["draft_response"] is not None
