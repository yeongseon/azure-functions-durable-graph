"""Tests for DurableGraphApp HTTP handlers and activity functions."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

from pydantic import BaseModel
import pytest

from azure_functions_langgraph import ManifestBuilder, RouteDecision
from azure_functions_langgraph.contracts import (
    EventApplyRequest,
    NodeExecutionRequest,
    OrchestrationInput,
    RouteAction,
    RouteResolutionRequest,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


class DemoState(BaseModel):
    value: int = 0


def increment(state: DemoState) -> dict[str, Any]:
    return {"value": state.value + 1}


def router(state: DemoState) -> RouteDecision:
    if state.value >= 3:
        return RouteDecision.complete()
    return RouteDecision.next("inc")


def _build_registration() -> Any:
    builder = ManifestBuilder(graph_name="demo", state_model=DemoState, version="1")
    builder.set_entrypoint("inc")
    builder.add_node("inc", increment, route=router, terminal=False)
    return builder.build()


def _make_http_request(
    *,
    route_params: dict[str, str] | None = None,
    body: Any = None,
    body_bytes: bytes | None = None,
) -> MagicMock:
    """Build a mock azure.functions.HttpRequest."""
    req = MagicMock()
    req.route_params = route_params or {}
    if body_bytes is not None:
        req.get_json.side_effect = ValueError("invalid json")
    elif body is not None:
        req.get_json.return_value = body
    else:
        req.get_json.side_effect = ValueError("no body")
    return req


# ── Module-level helpers ─────────────────────────────────────────────────────


def _import_app() -> Any:
    """Import DurableGraphApp with mocked Azure SDK packages."""
    with (
        patch.dict(
            "sys.modules",
            {
                "azure": MagicMock(),
                "azure.functions": MagicMock(),
                "azure.durable_functions": MagicMock(),
            },
        ),
    ):
        # Force re-import so the mocks are used
        import importlib

        import azure_functions_langgraph.app as app_mod

        importlib.reload(app_mod)
        return app_mod


# ── DurableGraphApp construction ─────────────────────────────────────────────


class TestDurableGraphAppInit:
    """Test that DurableGraphApp initialises with mocked Azure SDK."""

    def test_creates_instance(self) -> None:
        app_mod = _import_app()
        app = app_mod.DurableGraphApp()
        assert app.registry is not None
        assert app.function_app is not None
        assert app.blueprint is not None

    def test_register_registration(self) -> None:
        app_mod = _import_app()
        app = app_mod.DurableGraphApp()
        registration = _build_registration()
        app.register_registration(registration)
        manifests = app.registry.list_manifests()
        assert len(manifests) == 1
        assert manifests[0]["graph_name"] == "demo"


# ── HTTP helpers ─────────────────────────────────────────────────────────────


class TestReadJson:
    """Test _read_json and _read_json_any helpers."""

    def test_read_json_valid_dict(self) -> None:
        app_mod = _import_app()
        req = _make_http_request(body={"key": "value"})
        result = app_mod._read_json(req)
        assert result == {"key": "value"}

    def test_read_json_returns_none_for_list(self) -> None:
        app_mod = _import_app()
        req = _make_http_request(body=["a", "b"])
        result = app_mod._read_json(req)
        assert result is None

    def test_read_json_returns_none_for_invalid(self) -> None:
        app_mod = _import_app()
        req = _make_http_request(body_bytes=b"not json")
        result = app_mod._read_json(req)
        assert result is None

    def test_read_json_any_valid(self) -> None:
        app_mod = _import_app()
        req = _make_http_request(body=["a", "b"])
        result = app_mod._read_json_any(req)
        assert result == ["a", "b"]

    def test_read_json_any_invalid(self) -> None:
        app_mod = _import_app()
        req = _make_http_request(body_bytes=b"not json")
        result = app_mod._read_json_any(req)
        assert result is None


class TestJsonResponse:
    """Test _json_response helper."""

    def test_default_200(self) -> None:
        app_mod = _import_app()
        app_mod._json_response({"ok": True})
        call_kwargs = app_mod.func.HttpResponse.call_args
        assert call_kwargs.kwargs["status_code"] == 200
        body = json.loads(call_kwargs.kwargs["body"])
        assert body == {"ok": True}

    def test_custom_status_code(self) -> None:
        app_mod = _import_app()
        app_mod._json_response({"error": "not found"}, status_code=404)
        call_kwargs = app_mod.func.HttpResponse.call_args
        assert call_kwargs.kwargs["status_code"] == 404


# ── Contract models with graph_hash ──────────────────────────────────────────


class TestContractsWithGraphHash:
    """Verify all request models carry graph_hash."""

    def test_orchestration_input_has_graph_hash(self) -> None:
        oi = OrchestrationInput(graph_name="g", graph_hash="abc123", initial_state={})
        assert oi.graph_hash == "abc123"

    def test_node_execution_request_has_graph_hash(self) -> None:
        req = NodeExecutionRequest(graph_name="g", graph_hash="abc123", node_name="n", state={})
        assert req.graph_hash == "abc123"

    def test_route_resolution_request_has_graph_hash(self) -> None:
        req = RouteResolutionRequest(graph_name="g", graph_hash="abc123", node_name="n", state={})
        assert req.graph_hash == "abc123"

    def test_event_apply_request_has_graph_hash(self) -> None:
        req = EventApplyRequest(
            graph_name="g",
            graph_hash="abc123",
            event_name="e",
            state={},
            event_payload=None,
        )
        assert req.graph_hash == "abc123"

    def test_route_decision_wait_for_event_no_handler_name(self) -> None:
        """After Fix #2 — event_handler_name is removed, only event_name."""
        d = RouteDecision.wait_for_event(event_name="approval", resume_node="next")
        assert d.action == RouteAction.WAIT_FOR_EVENT
        assert d.event_name == "approval"
        assert d.resume_node == "next"
        assert not hasattr(d, "event_handler_name") or "event_handler_name" not in d.model_fields


# ── Manifest builder validation (Fix #3) ─────────────────────────────────────


class TestManifestBuilderValidation:
    """Test duplicate detection in ManifestBuilder."""

    def test_duplicate_node_name_raises(self) -> None:
        builder = ManifestBuilder(graph_name="test", state_model=DemoState)
        builder.set_entrypoint("a")
        builder.add_node("a", increment, terminal=True)
        with pytest.raises(ValueError, match="duplicate node name"):
            builder.add_node("a", increment, terminal=True)

    def test_duplicate_event_handler_raises(self) -> None:
        def handler(state: DemoState, payload: Any) -> dict[str, Any]:
            return {}

        builder = ManifestBuilder(graph_name="test", state_model=DemoState)
        builder.add_event_handler("evt", handler)
        with pytest.raises(ValueError, match="duplicate event handler"):
            builder.add_event_handler("evt", handler)

    def test_same_handler_different_nodes_ok(self) -> None:
        """Same function used for two different node names should be fine."""
        builder = ManifestBuilder(graph_name="test", state_model=DemoState)
        builder.set_entrypoint("a")
        builder.add_node("a", increment, next_node="b")
        builder.add_node("b", increment, terminal=True)
        reg = builder.build()
        assert "a" in reg.manifest.nodes
        assert "b" in reg.manifest.nodes


# ── Registry hash-based lookup (Fix #1) ──────────────────────────────────────


class TestRegistryHashLookup:
    """Test GraphRegistry.registration_by_hash and composite keying."""

    def test_registration_by_hash_succeeds(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        registration = _build_registration()
        reg = GraphRegistry()
        reg.register(registration)
        graph_hash = registration.manifest.graph_hash
        found = reg.registration_by_hash("demo", graph_hash)
        assert found is registration

    def test_registration_by_hash_unknown_hash_raises(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        registration = _build_registration()
        reg = GraphRegistry()
        reg.register(registration)
        with pytest.raises(KeyError, match="unknown graph"):
            reg.registration_by_hash("demo", "bad_hash")

    def test_registration_by_hash_unknown_name_raises(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        registration = _build_registration()
        reg = GraphRegistry()
        reg.register(registration)
        with pytest.raises(KeyError, match="unknown graph"):
            reg.registration_by_hash("nonexistent", registration.manifest.graph_hash)

    def test_duplicate_registration_same_hash_raises(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        registration = _build_registration()
        reg = GraphRegistry()
        reg.register(registration)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(registration)

    def test_list_manifests_after_register(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        reg = GraphRegistry()
        reg.register(_build_registration())
        manifests = reg.list_manifests()
        assert len(manifests) == 1
        assert "graph_hash" in manifests[0]

    def test_manifest_shortcut(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        reg = GraphRegistry()
        registration = _build_registration()
        reg.register(registration)
        manifest = reg.manifest("demo")
        assert manifest.graph_name == "demo"

    def test_manifest_unknown_graph_raises(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        reg = GraphRegistry()
        with pytest.raises(KeyError, match="unknown graph"):
            reg.manifest("nope")


# ── Registry async operations ─────────────────────────────────────────────────


class TestRegistryAsyncOps:
    """Test execute_node, resolve_route, apply_event with graph_hash."""

    @pytest.fixture()
    def registry_and_hash(self) -> tuple[Any, str]:
        from azure_functions_langgraph.registry import GraphRegistry

        registration = _build_registration()
        reg = GraphRegistry()
        reg.register(registration)
        return reg, registration.manifest.graph_hash

    @pytest.mark.asyncio
    async def test_execute_node(self, registry_and_hash: tuple[Any, str]) -> None:
        reg, graph_hash = registry_and_hash
        result = await reg.execute_node("demo", graph_hash, "inc", {"value": 5})
        assert result["value"] == 6

    @pytest.mark.asyncio
    async def test_resolve_route_complete(self, registry_and_hash: tuple[Any, str]) -> None:
        reg, graph_hash = registry_and_hash
        decision = await reg.resolve_route("demo", graph_hash, "inc", {"value": 3})
        assert decision["action"] == "complete"

    @pytest.mark.asyncio
    async def test_resolve_route_next(self, registry_and_hash: tuple[Any, str]) -> None:
        reg, graph_hash = registry_and_hash
        decision = await reg.resolve_route("demo", graph_hash, "inc", {"value": 0})
        assert decision["action"] == "next"
        assert decision["next_node"] == "inc"


# ── Registry edge cases ──────────────────────────────────────────────────────


class TestRegistryEdgeCases:
    """Cover remaining registry branches for coverage."""

    @pytest.mark.asyncio
    async def test_resolve_route_terminal_node(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        builder = ManifestBuilder(graph_name="t", state_model=DemoState, version="1")
        builder.set_entrypoint("end")
        builder.add_node("end", increment, terminal=True)
        registration = builder.build()
        reg = GraphRegistry()
        reg.register(registration)
        decision = await reg.resolve_route(
            "t", registration.manifest.graph_hash, "end", {"value": 0}
        )
        assert decision["action"] == "complete"

    @pytest.mark.asyncio
    async def test_resolve_route_next_node_static(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        builder = ManifestBuilder(graph_name="s", state_model=DemoState, version="1")
        builder.set_entrypoint("a")
        builder.add_node("a", increment, next_node="b")
        builder.add_node("b", increment, terminal=True)
        registration = builder.build()
        reg = GraphRegistry()
        reg.register(registration)
        decision = await reg.resolve_route("s", registration.manifest.graph_hash, "a", {"value": 0})
        assert decision["action"] == "next"
        assert decision["next_node"] == "b"

    @pytest.mark.asyncio
    async def test_resolve_route_implicit_completion(self) -> None:
        """Node with no next_node, no route, not terminal → implicit complete."""
        from azure_functions_langgraph.registry import GraphRegistry

        builder = ManifestBuilder(graph_name="ic", state_model=DemoState, version="1")
        builder.set_entrypoint("solo")
        # terminal=False, no next_node, no route
        builder.add_node("solo", increment)
        registration = builder.build()
        reg = GraphRegistry()
        reg.register(registration)
        decision = await reg.resolve_route(
            "ic", registration.manifest.graph_hash, "solo", {"value": 0}
        )
        assert decision["action"] == "complete"
        assert "implicit" in (decision.get("note") or "")

    @pytest.mark.asyncio
    async def test_apply_event_unknown_handler_raises(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        registration = _build_registration()
        reg = GraphRegistry()
        reg.register(registration)
        with pytest.raises(KeyError, match="unknown event handler"):
            await reg.apply_event(
                "demo",
                registration.manifest.graph_hash,
                "nonexistent_event",
                {"value": 0},
                {},
            )

    @pytest.mark.asyncio
    async def test_apply_event_success(self) -> None:
        from azure_functions_langgraph.registry import GraphRegistry

        class S(BaseModel):
            x: int = 0

        def evt_handler(state: S, payload: Any) -> dict[str, Any]:
            return {"x": state.x + payload["delta"]}

        builder = ManifestBuilder(graph_name="ev", state_model=S, version="1")
        builder.set_entrypoint("n")
        builder.add_node("n", lambda s: None, terminal=True)
        builder.add_event_handler("tick", evt_handler)
        registration = builder.build()
        reg = GraphRegistry()
        reg.register(registration)
        result = await reg.apply_event(
            "ev", registration.manifest.graph_hash, "tick", {"x": 5}, {"delta": 10}
        )
        assert result["x"] == 15

    @pytest.mark.asyncio
    async def test_execute_node_with_none_result(self) -> None:
        """Node handler returning None should leave state unchanged."""
        from azure_functions_langgraph.registry import GraphRegistry

        def noop(state: DemoState) -> None:
            pass

        builder = ManifestBuilder(graph_name="np", state_model=DemoState, version="1")
        builder.set_entrypoint("n")
        builder.add_node("n", noop, terminal=True)
        registration = builder.build()
        reg = GraphRegistry()
        reg.register(registration)
        result = await reg.execute_node("np", registration.manifest.graph_hash, "n", {"value": 42})
        assert result["value"] == 42

    @pytest.mark.asyncio
    async def test_execute_node_with_model_result(self) -> None:
        """Node handler returning a BaseModel should merge correctly."""
        from azure_functions_langgraph.registry import GraphRegistry

        def model_handler(state: DemoState) -> DemoState:
            return DemoState(value=state.value * 2)

        builder = ManifestBuilder(graph_name="mr", state_model=DemoState, version="1")
        builder.set_entrypoint("n")
        builder.add_node("n", model_handler, terminal=True)
        registration = builder.build()
        reg = GraphRegistry()
        reg.register(registration)
        result = await reg.execute_node("mr", registration.manifest.graph_hash, "n", {"value": 5})
        assert result["value"] == 10


# ── _normalize_route_decision branches ────────────────────────────────────────


class TestNormalizeRouteDecision:
    """Cover all branches of _normalize_route_decision."""

    def _make_node(self, *, next_node: str | None = None, terminal: bool = False) -> Any:
        from azure_functions_langgraph.manifest import NodeDefinition

        return NodeDefinition(
            name="test",
            handler_name="test_handler",
            next_node=next_node,
            terminal=terminal,
        )

    def test_none_with_next_node(self) -> None:
        from azure_functions_langgraph.registry import _normalize_route_decision

        node = self._make_node(next_node="b")
        result = _normalize_route_decision(node=node, raw=None)
        assert result.action == RouteAction.NEXT
        assert result.next_node == "b"

    def test_none_without_next_node(self) -> None:
        from azure_functions_langgraph.registry import _normalize_route_decision

        node = self._make_node()
        result = _normalize_route_decision(node=node, raw=None)
        assert result.action == RouteAction.COMPLETE

    def test_route_decision_passthrough(self) -> None:
        from azure_functions_langgraph.registry import _normalize_route_decision

        node = self._make_node()
        decision = RouteDecision.complete(note="done")
        result = _normalize_route_decision(node=node, raw=decision)
        assert result is decision

    def test_string_next(self) -> None:
        from azure_functions_langgraph.registry import _normalize_route_decision

        node = self._make_node()
        result = _normalize_route_decision(node=node, raw="step_b")
        assert result.action == RouteAction.NEXT
        assert result.next_node == "step_b"

    def test_string_complete(self) -> None:
        from azure_functions_langgraph.registry import _normalize_route_decision

        node = self._make_node()
        result = _normalize_route_decision(node=node, raw="__complete__")
        assert result.action == RouteAction.COMPLETE

    def test_dict_decision(self) -> None:
        from azure_functions_langgraph.registry import _normalize_route_decision

        node = self._make_node()
        result = _normalize_route_decision(node=node, raw={"action": "next", "next_node": "c"})
        assert result.action == RouteAction.NEXT
        assert result.next_node == "c"

    def test_unsupported_type_raises(self) -> None:
        from azure_functions_langgraph.registry import _normalize_route_decision

        node = self._make_node()
        with pytest.raises(TypeError, match="unsupported route decision"):
            _normalize_route_decision(node=node, raw=42)  # type: ignore[arg-type]


# ── _merge_state edge case ────────────────────────────────────────────────────


class TestMergeState:
    """Cover the TypeError branch in _merge_state."""

    def test_unsupported_type_raises(self) -> None:
        from azure_functions_langgraph.registry import _merge_state

        state = DemoState(value=1)
        with pytest.raises(TypeError, match="unsupported state merge"):
            _merge_state(state, 42, DemoState)  # type: ignore[arg-type]


# ── _callable_name ────────────────────────────────────────────────────────────


class TestCallableName:
    """Test _callable_name uses module.qualname."""

    def test_regular_function(self) -> None:
        from azure_functions_langgraph.manifest import _callable_name

        name = _callable_name(increment)
        # Should contain module and qualname
        assert "increment" in name
        assert "." in name

    def test_lambda(self) -> None:
        from azure_functions_langgraph.manifest import _callable_name

        fn = lambda x: x  # noqa: E731
        name = _callable_name(fn)
        assert "<lambda>" in name

    def test_none_raises(self) -> None:
        from azure_functions_langgraph.manifest import _callable_name

        with pytest.raises(ValueError, match="callable cannot be None"):
            _callable_name(None)


# ── NodeDefinition validation ─────────────────────────────────────────────────


class TestNodeDefinitionValidation:
    """Test model_validator on NodeDefinition."""

    def test_terminal_with_next_node_raises(self) -> None:
        from azure_functions_langgraph.manifest import NodeDefinition

        with pytest.raises(ValueError, match="terminal nodes cannot"):
            NodeDefinition(
                name="n",
                handler_name="h",
                terminal=True,
                next_node="other",
            )

    def test_terminal_with_route_raises(self) -> None:
        from azure_functions_langgraph.manifest import NodeDefinition

        with pytest.raises(ValueError, match="terminal nodes cannot"):
            NodeDefinition(
                name="n",
                handler_name="h",
                terminal=True,
                route_handler_name="r",
            )


# ── ManifestBuilder build-time validation ─────────────────────────────────────


class TestManifestBuilderBuildValidation:
    """Test build() validation: entrypoint must be set and reference a node."""

    def test_entrypoint_not_registered_raises(self) -> None:
        builder = ManifestBuilder(graph_name="test", state_model=DemoState)
        builder.set_entrypoint("ghost")
        with pytest.raises(ValueError, match="entrypoint must reference"):
            builder.build()

    def test_openapi_schema_fragment(self) -> None:
        registration = _build_registration()
        frag = registration.manifest.openapi_schema_fragment()
        assert frag["graph_name"] == "demo"
        assert "graph_hash" in frag
        assert "entrypoint" in frag


# ── RouteDecision model_validator (Fix #6) ─────────────────────────────────────


class TestRouteDecisionValidator:
    """Test model_validator on RouteDecision enforces field requirements."""

    def test_next_without_next_node_raises(self) -> None:
        with pytest.raises(ValueError, match="action 'next' requires next_node"):
            RouteDecision(action=RouteAction.NEXT)

    def test_next_with_next_node_ok(self) -> None:
        d = RouteDecision(action=RouteAction.NEXT, next_node="step_b")
        assert d.next_node == "step_b"

    def test_wait_for_event_without_event_name_raises(self) -> None:
        with pytest.raises(ValueError, match="requires both event_name and resume_node"):
            RouteDecision(
                action=RouteAction.WAIT_FOR_EVENT,
                resume_node="next",
            )

    def test_wait_for_event_without_resume_node_raises(self) -> None:
        with pytest.raises(ValueError, match="requires both event_name and resume_node"):
            RouteDecision(
                action=RouteAction.WAIT_FOR_EVENT,
                event_name="approval",
            )

    def test_wait_for_event_with_both_ok(self) -> None:
        d = RouteDecision(
            action=RouteAction.WAIT_FOR_EVENT,
            event_name="approval",
            resume_node="after_approval",
        )
        assert d.event_name == "approval"
        assert d.resume_node == "after_approval"

    def test_complete_with_next_node_raises(self) -> None:
        with pytest.raises(ValueError, match="action 'complete' must not set next_node"):
            RouteDecision(action=RouteAction.COMPLETE, next_node="oops")

    def test_complete_ok(self) -> None:
        d = RouteDecision(action=RouteAction.COMPLETE, note="done")
        assert d.action == RouteAction.COMPLETE

    def test_factory_next(self) -> None:
        d = RouteDecision.next("b")
        assert d.action == RouteAction.NEXT
        assert d.next_node == "b"

    def test_factory_complete(self) -> None:
        d = RouteDecision.complete()
        assert d.action == RouteAction.COMPLETE

    def test_factory_wait_for_event(self) -> None:
        d = RouteDecision.wait_for_event(event_name="e", resume_node="r")
        assert d.action == RouteAction.WAIT_FOR_EVENT


# ── ManifestBuilder edge reference validation (Fix #7) ────────────────────────


class TestManifestBuilderEdgeValidation:
    """Test build-time edge reference and reachability checks."""

    def test_unknown_next_node_raises(self) -> None:
        builder = ManifestBuilder(graph_name="test", state_model=DemoState)
        builder.set_entrypoint("a")
        builder.add_node("a", increment, next_node="nonexistent")
        with pytest.raises(ValueError, match="references unknown next_node"):
            builder.build()

    def test_unreachable_node_raises(self) -> None:
        """Node 'orphan' is registered but not reachable from entrypoint."""
        builder = ManifestBuilder(graph_name="test", state_model=DemoState)
        builder.set_entrypoint("a")
        builder.add_node("a", increment, terminal=True)
        builder.add_node("orphan", increment, terminal=True)
        with pytest.raises(ValueError, match="nodes unreachable from entrypoint"):
            builder.build()

    def test_all_reachable_ok(self) -> None:
        """Linear chain: a -> b -> c (terminal). All reachable."""
        builder = ManifestBuilder(graph_name="test", state_model=DemoState)
        builder.set_entrypoint("a")
        builder.add_node("a", increment, next_node="b")
        builder.add_node("b", increment, next_node="c")
        builder.add_node("c", increment, terminal=True)
        reg = builder.build()
        assert len(reg.manifest.nodes) == 3

    def test_reachable_via_route_only(self) -> None:
        """Node with route (no static next_node) — sibling only reachable via route.
        Since BFS only follows static next_node, route-only targets must be next_node-connected.
        This tests that the builder does NOT false-positive on route-connected nodes."""
        # Node 'a' has a route but also static next_node='b'
        builder = ManifestBuilder(graph_name="test", state_model=DemoState)
        builder.set_entrypoint("a")
        builder.add_node("a", increment, next_node="b", route=router)
        builder.add_node("b", increment, terminal=True)
        reg = builder.build()
        assert len(reg.manifest.nodes) == 2


# ── Tests for Oracle Second Review Fixes ─────────────────────────────────────


class TestRouteTargetValidation:
    """Fix #1: Runtime validation of route decision targets against manifest."""

    @pytest.mark.asyncio
    async def test_resolve_route_unknown_next_node(self) -> None:
        """Dynamic route returning unknown node name raises ValueError."""
        from azure_functions_langgraph.registry import GraphRegistry

        def bad_router(state: DemoState) -> RouteDecision:
            # Returns a node name that doesn't exist in the manifest
            return RouteDecision.next("does_not_exist")

        builder = ManifestBuilder(graph_name="test", state_model=DemoState)
        builder.set_entrypoint("a")
        builder.add_node("a", increment, route=bad_router, next_node="b")
        builder.add_node("b", increment, terminal=True)
        reg = builder.build()

        registry = GraphRegistry()
        registry.register(reg)

        with pytest.raises(ValueError, match="unknown node 'does_not_exist'"):
            await registry.resolve_route("test", reg.manifest.graph_hash, "a", {"value": 0})

    @pytest.mark.asyncio
    async def test_resolve_route_unknown_resume_node(self) -> None:
        """Route returning wait_for_event with unknown resume_node raises ValueError."""
        from azure_functions_langgraph.registry import GraphRegistry

        def event_router(state: DemoState) -> RouteDecision:
            return RouteDecision.wait_for_event(event_name="approval", resume_node="does_not_exist")

        builder = ManifestBuilder(graph_name="test2", state_model=DemoState)
        builder.set_entrypoint("a")
        builder.add_node("a", increment, route=event_router, next_node="b")
        builder.add_node("b", increment, terminal=True)
        reg = builder.build()

        registry = GraphRegistry()
        registry.register(reg)

        with pytest.raises(ValueError, match="unknown resume_node 'does_not_exist'"):
            await registry.resolve_route("test2", reg.manifest.graph_hash, "a", {"value": 0})


class TestRouteDecisionFieldCleaning:
    """Fix #3: Spurious fields are cleaned per action type."""

    def test_next_clears_event_fields(self) -> None:
        """action=NEXT should clear event_name and resume_node."""
        d = RouteDecision(
            action=RouteAction.NEXT,
            next_node="b",
            event_name="stale",
            resume_node="stale",
        )
        assert d.next_node == "b"
        assert d.event_name is None
        assert d.resume_node is None

    def test_wait_for_event_clears_next_node(self) -> None:
        """action=WAIT_FOR_EVENT should clear next_node."""
        d = RouteDecision(
            action=RouteAction.WAIT_FOR_EVENT,
            event_name="approval",
            resume_node="b",
            next_node="stale",
        )
        assert d.event_name == "approval"
        assert d.resume_node == "b"
        assert d.next_node is None

    def test_complete_clears_event_fields(self) -> None:
        """action=COMPLETE should clear event_name and resume_node."""
        d = RouteDecision(
            action=RouteAction.COMPLETE,
            event_name="stale",
            resume_node="stale",
        )
        assert d.event_name is None
        assert d.resume_node is None
