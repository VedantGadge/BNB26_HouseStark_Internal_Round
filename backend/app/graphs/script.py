"""Bounded script writer/reviewer workflow; the durable job owns persistence."""

from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class ScriptState(TypedDict, total=False):
    hooks: list[dict]
    content: dict
    review: dict
    needs_revision: bool
    requirement_checks: list[dict]
    warning_ids: list[str]


ScriptNode = Callable[[ScriptState], dict]


def build_script_graph(
    *,
    writer: ScriptNode,
    reviewer: ScriptNode,
    revise: ScriptNode,
    validate: ScriptNode,
    persist: ScriptNode,
):
    graph = StateGraph(ScriptState)
    graph.add_node("writer", writer)
    graph.add_node("reviewer", reviewer)
    graph.add_node("revise", revise)
    graph.add_node("validate", validate)
    graph.add_node("persist", persist)
    graph.add_edge(START, "writer")
    graph.add_edge("writer", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        lambda state: "revise" if state["needs_revision"] else "validate",
        {"revise": "revise", "validate": "validate"},
    )
    # A revision proceeds directly to validation, never back into a review loop.
    graph.add_edge("revise", "validate")
    graph.add_edge("validate", "persist")
    graph.add_edge("persist", END)
    return graph.compile()
