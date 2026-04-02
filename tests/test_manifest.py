from typing import Any

from pydantic import BaseModel

from azure_functions_durable_graph import ManifestBuilder


class DemoState(BaseModel):
    counter: int = 0


def first(state: DemoState) -> dict[str, Any]:
    return {"counter": state.counter + 1}


def second(state: DemoState) -> dict[str, Any]:
    return {"counter": state.counter + 1}


def test_manifest_hash_is_stable_for_same_topology() -> None:
    builder_a = ManifestBuilder(graph_name="demo", state_model=DemoState, version="1")
    builder_a.set_entrypoint("first")
    builder_a.add_node("first", first, next_node="second")
    builder_a.add_node("second", second, terminal=True)
    reg_a = builder_a.build()

    builder_b = ManifestBuilder(graph_name="demo", state_model=DemoState, version="1")
    builder_b.set_entrypoint("first")
    builder_b.add_node("first", first, next_node="second")
    builder_b.add_node("second", second, terminal=True)
    reg_b = builder_b.build()

    assert reg_a.manifest.graph_hash == reg_b.manifest.graph_hash
