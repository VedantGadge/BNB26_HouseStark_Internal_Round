"""Prototype graph shell for the durable script worker workflow.

The worker owns persistence; this graph gives the prototype a concrete, inspectable workflow
entrypoint without adding checkpoint infrastructure that the hackathon demo does not need.
"""

from langgraph.graph import END, START, StateGraph


def build_script_graph():
    """Build a minimal validate → generate → persist workflow graph.

    ScriptCreationService performs those stages against the durable Job record. The graph is kept
    deliberately small so callers can inspect or invoke the prototype flow without a database-only
    checkpoint dependency.
    """

    graph = StateGraph(dict)
    graph.add_node("validate", lambda state: state)
    graph.add_node("generate", lambda state: state)
    graph.add_node("persist", lambda state: state)
    graph.add_edge(START, "validate")
    graph.add_edge("validate", "generate")
    graph.add_edge("generate", "persist")
    graph.add_edge("persist", END)
    return graph.compile()
