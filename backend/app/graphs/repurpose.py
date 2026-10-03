"""Persisted proposal workflow with a review interrupt that frees the worker."""

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


def build_repurpose_graph(propose, checkpointer):
    def review(state):
        selected = interrupt(
            {
                "candidate_ids": state["candidate_ids"],
                "edit_version_ids": state["edit_version_ids"],
                "preview_render_id": state.get("preview_render_id"),
            }
        )
        return {
            **{key: value for key, value in state.items() if key != "__interrupt__"},
            "selected_edit_version_id": selected["edit_version_id"],
        }

    graph = StateGraph(dict)
    graph.add_node("propose", propose)
    graph.add_node("review", review)
    graph.add_edge(START, "propose")
    graph.add_edge("propose", "review")
    graph.add_edge("review", END)
    return graph.compile(checkpointer=checkpointer)
