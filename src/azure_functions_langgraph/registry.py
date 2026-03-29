from __future__ import annotations

import inspect
from typing import Any

from pydantic import BaseModel

from .contracts import RouteDecision
from .manifest import GraphManifest, GraphRegistration, NodeDefinition


class GraphRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, GraphRegistration[Any]] = {}

    def register(self, registration: GraphRegistration[Any]) -> None:
        graph_name = registration.manifest.graph_name
        if graph_name in self._registrations:
            raise ValueError(f"graph '{graph_name}' is already registered")
        self._registrations[graph_name] = registration

    def list_manifests(self) -> list[dict[str, Any]]:
        return [
            registration.manifest.openapi_schema_fragment()
            for registration in self._registrations.values()
        ]

    def manifest(self, graph_name: str) -> GraphManifest:
        return self.registration(graph_name).manifest

    def registration(self, graph_name: str) -> GraphRegistration[Any]:
        try:
            return self._registrations[graph_name]
        except KeyError as exc:
            raise KeyError(f"unknown graph '{graph_name}'") from exc

    async def execute_node(
        self,
        graph_name: str,
        node_name: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        registration = self.registration(graph_name)
        node = registration.manifest.nodes[node_name]
        handler = registration.node_handlers[node.handler_name]
        current_state = registration.state_model.model_validate(state)
        result = await _maybe_await(handler(current_state))
        merged = _merge_state(current_state, result, registration.state_model)
        return merged.model_dump(mode="python")

    async def resolve_route(
        self,
        graph_name: str,
        node_name: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        registration = self.registration(graph_name)
        node = registration.manifest.nodes[node_name]
        current_state = registration.state_model.model_validate(state)

        if node.terminal:
            decision = RouteDecision.complete()

        elif node.route_handler_name:
            handler = registration.route_handlers[node.route_handler_name]
            raw = await _maybe_await(handler(current_state))
            decision = _normalize_route_decision(node=node, raw=raw)

        elif node.next_node:
            decision = RouteDecision.next(node.next_node)

        else:
            decision = RouteDecision.complete(note="implicit completion: no outgoing edge")

        return decision.model_dump(mode="python")

    async def apply_event(
        self,
        graph_name: str,
        event_handler_name: str,
        state: dict[str, Any],
        event_payload: Any,
    ) -> dict[str, Any]:
        registration = self.registration(graph_name)
        try:
            handler = registration.event_handlers[event_handler_name]
        except KeyError as exc:
            raise KeyError(f"unknown event handler '{event_handler_name}'") from exc

        current_state = registration.state_model.model_validate(state)
        result = await _maybe_await(handler(current_state, event_payload))
        merged = _merge_state(current_state, result, registration.state_model)
        return merged.model_dump(mode="python")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _merge_state(
    current_state: BaseModel,
    result: BaseModel | dict[str, Any] | None,
    state_model: type[BaseModel],
) -> BaseModel:
    if result is None:
        return current_state

    if isinstance(result, BaseModel):
        return state_model.model_validate(result.model_dump(mode="python"))

    if isinstance(result, dict):
        merged = current_state.model_dump(mode="python")
        merged.update(result)
        return state_model.model_validate(merged)

    raise TypeError(f"unsupported state merge result: {type(result)!r}")


def _normalize_route_decision(
    *,
    node: NodeDefinition,
    raw: RouteDecision | str | dict[str, Any] | None,
) -> RouteDecision:
    if raw is None:
        if node.next_node:
            return RouteDecision.next(node.next_node)
        return RouteDecision.complete(note="route handler returned None")

    if isinstance(raw, RouteDecision):
        return raw

    if isinstance(raw, str):
        if raw == "__complete__":
            return RouteDecision.complete()
        return RouteDecision.next(raw)

    if isinstance(raw, dict):
        return RouteDecision.model_validate(raw)

    raise TypeError(f"unsupported route decision: {type(raw)!r}")
