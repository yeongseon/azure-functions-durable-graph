"""Smoke tests for the content_classifier example."""

from __future__ import annotations

import pytest

from azure_functions_durable_graph import RouteDecision
from azure_functions_durable_graph.registry import GraphRegistry
from examples.content_classifier.graph import (
    ContentState,
    classify,
    handle_complaint,
    handle_feedback,
    handle_question,
    registration,
    route_after_classify,
    summarize,
)


def test_content_classifier_registration_builds() -> None:
    """The content_classifier example should produce a valid registration."""
    assert registration.manifest.graph_name == "content_classifier"
    assert registration.manifest.entrypoint == "classify"
    assert "classify" in registration.manifest.nodes
    assert "handle_question" in registration.manifest.nodes
    assert "handle_complaint" in registration.manifest.nodes
    assert "handle_feedback" in registration.manifest.nodes
    assert "summarize" in registration.manifest.nodes
    assert registration.manifest.graph_hash


def test_classify_question() -> None:
    """classify should detect questions."""
    state = ContentState(text="How do I reset my password?")
    result = classify(state)
    assert result["category"] == "question"


def test_classify_complaint() -> None:
    """classify should detect complaints."""
    state = ContentState(text="This product is terrible and broken")
    result = classify(state)
    assert result["category"] == "complaint"
    assert result["sentiment"] == "negative"


def test_classify_feedback() -> None:
    """classify should fall back to feedback."""
    state = ContentState(text="I used the product today")
    result = classify(state)
    assert result["category"] == "feedback"
    assert result["sentiment"] == "neutral"


def test_classify_positive_sentiment() -> None:
    """classify should detect positive sentiment."""
    state = ContentState(text="I love this product, excellent work")
    result = classify(state)
    assert result["sentiment"] == "positive"


def test_route_question() -> None:
    """Route handler should send questions to handle_question."""
    state = ContentState(text="test", category="question")
    decision = route_after_classify(state)
    assert isinstance(decision, RouteDecision)
    assert decision.action.value == "next"
    assert decision.next_node == "handle_question"


def test_route_complaint() -> None:
    """Route handler should send complaints to handle_complaint."""
    state = ContentState(text="test", category="complaint")
    decision = route_after_classify(state)
    assert decision.next_node == "handle_complaint"


def test_route_feedback() -> None:
    """Route handler should send feedback to handle_feedback."""
    state = ContentState(text="test", category="feedback")
    decision = route_after_classify(state)
    assert decision.next_node == "handle_feedback"


def test_handle_question_response() -> None:
    """handle_question should produce a response."""
    state = ContentState(text="How?", category="question")
    result = handle_question(state)
    assert "question" in result["response"].lower() or "team" in result["response"].lower()


def test_handle_complaint_response() -> None:
    """handle_complaint should produce an apology response."""
    state = ContentState(text="Broken!", category="complaint")
    result = handle_complaint(state)
    assert "sorry" in result["response"].lower()


def test_handle_feedback_response() -> None:
    """handle_feedback should produce a thank-you response."""
    state = ContentState(text="Nice", category="feedback")
    result = handle_feedback(state)
    assert "thank" in result["response"].lower()


def test_summarize_produces_summary() -> None:
    """summarize should combine category, sentiment, and response."""
    state = ContentState(
        text="test",
        category="question",
        sentiment="neutral",
        response="We will help you.",
    )
    result = summarize(state)
    assert "question" in result["summary"]
    assert "neutral" in result["summary"]
    assert "We will help you." in result["summary"]


@pytest.mark.asyncio
async def test_content_classifier_full_flow_question() -> None:
    """Smoke test: classify a question and route through handle_question."""
    reg = GraphRegistry()
    reg.register(registration)
    graph_hash = registration.manifest.graph_hash

    # Classify
    state = await reg.execute_node(
        "content_classifier",
        graph_hash,
        "classify",
        {"text": "How do I reset my password?"},
    )
    assert state["category"] == "question"

    # Route
    route_result = await reg.resolve_route("content_classifier", graph_hash, "classify", state)
    assert route_result["next_node"] == "handle_question"

    # Handle
    state = await reg.execute_node("content_classifier", graph_hash, "handle_question", state)
    assert state["response"] is not None

    # Summarize
    state = await reg.execute_node("content_classifier", graph_hash, "summarize", state)
    assert "question" in state["summary"]


@pytest.mark.asyncio
async def test_content_classifier_full_flow_complaint() -> None:
    """Smoke test: classify a complaint and route through handle_complaint."""
    reg = GraphRegistry()
    reg.register(registration)
    graph_hash = registration.manifest.graph_hash

    state = await reg.execute_node(
        "content_classifier",
        graph_hash,
        "classify",
        {"text": "This is terrible and broken"},
    )
    assert state["category"] == "complaint"
    assert state["sentiment"] == "negative"

    route_result = await reg.resolve_route("content_classifier", graph_hash, "classify", state)
    assert route_result["next_node"] == "handle_complaint"

    state = await reg.execute_node("content_classifier", graph_hash, "handle_complaint", state)
    assert "sorry" in state["response"].lower()
