from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

JsonDict = dict[str, Any]


class RouteAction(str, Enum):
    NEXT = "next"
    COMPLETE = "complete"
    WAIT_FOR_EVENT = "wait_for_event"


class RouteDecision(BaseModel):
    action: RouteAction
    next_node: str | None = None
    event_name: str | None = None
    resume_node: str | None = None
    note: str | None = None

    @classmethod
    def next(cls, node_name: str) -> "RouteDecision":
        return cls(action=RouteAction.NEXT, next_node=node_name)

    @classmethod
    def complete(cls, note: str | None = None) -> "RouteDecision":
        return cls(action=RouteAction.COMPLETE, note=note)

    @classmethod
    def wait_for_event(
        cls,
        *,
        event_name: str,
        resume_node: str,
        note: str | None = None,
    ) -> "RouteDecision":
        return cls(
            action=RouteAction.WAIT_FOR_EVENT,
            event_name=event_name,
            resume_node=resume_node,
            note=note,
        )


class OrchestrationInput(BaseModel):
    graph_name: str
    graph_hash: str
    initial_state: JsonDict
    current_node: str | None = None
    metadata: JsonDict = Field(default_factory=dict)


class NodeExecutionRequest(BaseModel):
    graph_name: str
    graph_hash: str
    node_name: str
    state: JsonDict


class RouteResolutionRequest(BaseModel):
    graph_name: str
    graph_hash: str
    node_name: str
    state: JsonDict


class EventApplyRequest(BaseModel):
    graph_name: str
    graph_hash: str
    event_name: str
    state: JsonDict
    event_payload: Any


class RunStatusEnvelope(BaseModel):
    instance_id: str
    runtime_status: str | None = None
    custom_status: Any | None = None
    input: Any | None = None
    output: Any | None = None
