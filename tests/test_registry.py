from typing import Any

from pydantic import BaseModel
import pytest

from azure_functions_langgraph import ManifestBuilder, RouteDecision
from azure_functions_langgraph.registry import GraphRegistry


class DemoState(BaseModel):
    message: str
    approved: bool | None = None
    result: str | None = None


def classify(state: DemoState) -> dict[str, Any]:
    return {}


def route(state: DemoState) -> RouteDecision:
    if state.approved:
        return RouteDecision.next("finish")
    return RouteDecision.wait_for_event(
        event_name="approval",
        resume_node="finish",
        event_handler_name="approval",
    )


def finish(state: DemoState) -> dict[str, str]:
    return {"result": f"done:{state.message}"}


def apply_approval(state: DemoState, payload: Any) -> dict[str, bool]:
    return {"approved": bool(payload["approved"])}


@pytest.fixture()
def registry() -> GraphRegistry:
    builder = ManifestBuilder(graph_name="demo", state_model=DemoState, version="1")
    builder.set_entrypoint("classify")
    builder.add_node("classify", classify, route=route)
    builder.add_event_handler("approval", apply_approval)
    builder.add_node("finish", finish, terminal=True)

    reg = GraphRegistry()
    reg.register(builder.build())
    return reg


@pytest.mark.asyncio
async def test_registry_routes_to_wait_for_event(registry: GraphRegistry) -> None:
    decision = await registry.resolve_route("demo", "classify", {"message": "hello"})
    assert decision["action"] == "wait_for_event"
    assert decision["event_name"] == "approval"


@pytest.mark.asyncio
async def test_registry_applies_event(registry: GraphRegistry) -> None:
    new_state = await registry.apply_event(
        "demo",
        "approval",
        {"message": "hello"},
        {"approved": True},
    )
    assert new_state["approved"] is True
