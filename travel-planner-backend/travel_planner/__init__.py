"""
Travel Planner Package - V4
A multi-agent system for travel planning based on LangGraph.
This version includes a sophisticated architecture with task decomposition,
judgement, and synthesis steps.
"""

from .graph_builder import build_travel_graph, create_travel_planner
from .nodes.coordinator import Coordinator
from .nodes.chat_node import ChatNode
from .nodes.task_decomposer import TaskDecomposer
from .nodes.judgement_agent import JudgementAgent
from .nodes.plan_agent import ToolExecutor
from .nodes.plan_synthesizer import PlanSynthesizer

__version__ = "0.4.0"
__all__ = [
    "build_travel_graph",
    "create_travel_planner",
    "Coordinator",
    "ChatNode",
    "TaskDecomposer",
    "JudgementAgent",
    "ToolExecutor",
    "PlanSynthesizer",
]

