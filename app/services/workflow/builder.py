# app/services/workflow/builder.py
"""
KontentPyper - LangGraph Workflow Builder
Assembles the StateGraph from individual node functions and compiles
it into an executable pipeline.
"""

from langgraph.graph import StateGraph, END
from app.services.workflow.state import WorkflowState
from app.services.workflow.nodes import (
    fetch_node,
    score_node,
    draft_node,
    generate_media_node,
)


# ── Wire Graph ────────────────────────────────────────────────────────
def build_graph():
    """
    Builds and compiles the LangGraph state machine.

    Pipeline: fetch -> score -> draft -> generate_media -> END
    """
    workflow = StateGraph(WorkflowState)

    workflow.add_node("fetch", fetch_node)
    workflow.add_node("score", score_node)
    workflow.add_node("draft", draft_node)
    workflow.add_node("generate_media", generate_media_node)

    workflow.set_entry_point("fetch")
    workflow.add_edge("fetch", "score")
    workflow.add_edge("score", "draft")
    workflow.add_edge("draft", "generate_media")
    workflow.add_edge("generate_media", END)

    return workflow.compile()