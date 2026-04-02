"""Content classifier with conditional routing.

Demonstrates dynamic routing based on state without external events.
A ``classify`` node inspects the input and a route handler directs execution
to one of several specialised handlers.

Graph topology::

    classify ─┬─ handle_question ──┐
              ├─ handle_complaint ─┤
              └─ handle_feedback ──┘
                                   └─ summarize (terminal)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from azure_functions_durable_graph import ManifestBuilder, RouteDecision


class ContentState(BaseModel):
    """State for the content classification pipeline."""

    text: str
    category: str | None = None
    sentiment: str | None = None
    response: str | None = None
    summary: str | None = None


def classify(state: ContentState) -> dict[str, Any]:
    """Determine category and sentiment from input text."""
    lower = state.text.lower()

    if "?" in state.text or any(w in lower for w in ("how", "what", "why", "when")):
        category = "question"
    elif any(w in lower for w in ("broken", "terrible", "worst", "complaint", "angry")):
        category = "complaint"
    else:
        category = "feedback"

    positive = {"great", "good", "love", "excellent", "thanks"}
    negative = {"bad", "broken", "terrible", "worst", "angry", "hate"}
    words = set(lower.split())
    if words & negative:
        sentiment = "negative"
    elif words & positive:
        sentiment = "positive"
    else:
        sentiment = "neutral"

    return {"category": category, "sentiment": sentiment}


def route_after_classify(state: ContentState) -> RouteDecision:
    """Route to the appropriate handler based on category."""
    handler_map = {
        "question": "handle_question",
        "complaint": "handle_complaint",
        "feedback": "handle_feedback",
    }
    target = handler_map.get(state.category or "", "handle_feedback")
    return RouteDecision.next(target)


def handle_question(state: ContentState) -> dict[str, Any]:
    """Generate a response for questions."""
    return {
        "response": (
            "Thank you for your question. Our team will research this and "
            "get back to you within 24 hours."
        ),
    }


def handle_complaint(state: ContentState) -> dict[str, Any]:
    """Generate a response for complaints."""
    return {
        "response": (
            "We're sorry to hear about your experience. A support specialist "
            "has been assigned to resolve this issue."
        ),
    }


def handle_feedback(state: ContentState) -> dict[str, Any]:
    """Generate a response for general feedback."""
    return {
        "response": "Thank you for your feedback! We appreciate you taking the time to share.",
    }


def summarize(state: ContentState) -> dict[str, Any]:
    """Produce a final summary of the classification result."""
    return {
        "summary": (
            f"Category: {state.category} | Sentiment: {state.sentiment} | "
            f"Response: {state.response}"
        ),
    }


builder = ManifestBuilder(
    graph_name="content_classifier",
    state_model=ContentState,
    version="0.1.0",
    metadata={"example": True, "profile": "routing"},
)
builder.set_entrypoint("classify")
builder.add_node("classify", classify, route=route_after_classify)
builder.add_node("handle_question", handle_question, next_node="summarize")
builder.add_node("handle_complaint", handle_complaint, next_node="summarize")
builder.add_node("handle_feedback", handle_feedback, next_node="summarize")
builder.add_node("summarize", summarize, terminal=True)

registration = builder.build()
