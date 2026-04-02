"""Smoke tests for the data_pipeline example."""

from __future__ import annotations

import pytest

from azure_functions_durable_graph.registry import GraphRegistry
from examples.data_pipeline.graph import (
    PipelineState,
    extract,
    load,
    registration,
    transform,
)


def test_data_pipeline_registration_builds() -> None:
    """The data_pipeline example should produce a valid registration."""
    assert registration.manifest.graph_name == "data_pipeline"
    assert registration.manifest.entrypoint == "extract"
    assert "extract" in registration.manifest.nodes
    assert "transform" in registration.manifest.nodes
    assert "load" in registration.manifest.nodes
    assert registration.manifest.graph_hash


def test_extract_returns_raw_records() -> None:
    """extract should populate raw_records and record_count."""
    state = PipelineState(source_url="https://example.com/data")
    result = extract(state)
    assert len(result["raw_records"]) == 3
    assert result["record_count"] == 3


def test_transform_cleans_records() -> None:
    """transform should strip names and cast scores to int."""
    state = PipelineState(
        source_url="https://example.com/data",
        raw_records=[
            {"id": 1, "name": "  Alice  ", "score": "85"},
            {"id": 2, "name": "  Bob  ", "score": "92"},
        ],
    )
    result = transform(state)
    records = result["transformed_records"]
    assert records[0]["name"] == "Alice"
    assert records[0]["score"] == 85
    assert records[1]["name"] == "Bob"


def test_load_produces_result_message() -> None:
    """load should produce a result referencing the source URL."""
    state = PipelineState(
        source_url="https://example.com/data",
        transformed_records=[{"id": 1, "name": "Alice", "score": 85}],
    )
    result = load(state)
    assert "1 records" in result["load_result"]
    assert "example.com" in result["load_result"]


@pytest.mark.asyncio
async def test_data_pipeline_full_flow() -> None:
    """Smoke test: register and execute all nodes through the registry."""
    reg = GraphRegistry()
    reg.register(registration)
    graph_hash = registration.manifest.graph_hash

    # Execute extract
    state = await reg.execute_node(
        "data_pipeline", graph_hash, "extract", {"source_url": "https://example.com/data"}
    )
    assert len(state["raw_records"]) == 3
    assert state["record_count"] == 3

    # Execute transform
    state = await reg.execute_node("data_pipeline", graph_hash, "transform", state)
    assert len(state["transformed_records"]) == 3
    assert state["transformed_records"][0]["name"] == "Alice"
    assert state["transformed_records"][0]["score"] == 85

    # Execute load
    state = await reg.execute_node("data_pipeline", graph_hash, "load", state)
    assert "3 records" in state["load_result"]
