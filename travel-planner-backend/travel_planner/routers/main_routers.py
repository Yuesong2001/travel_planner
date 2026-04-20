"""
Main Routers
All routing logic for the travel planning graph.
"""
from typing import Dict, Any

MAX_RETRIES = 3


def entry_router(state: Dict[str, Any]) -> str:
    """Routes from the entry point based on initial state."""
    return "chat"


def chat_router(state: Dict[str, Any]) -> str:
    """After chat, decide if we have enough info to plan, refine existing plan, or continue chatting."""
    intent = state.get("intent")
    user_request = state.get("user_request")
    existing_plan = state.get("plan")
    refinement_request = state.get("refinement_request")

    # Check if user wants to refine an existing plan
    if intent == "refine" and existing_plan and refinement_request:
        return "refine_plan"

    # Check if we have intent to plan and a valid (non-empty) user_request
    if intent == "plan" and user_request and isinstance(user_request, dict) and len(user_request) > 0:
        return "normalize_input"

    # If intent is "chat", end and wait for next user input
    if intent == "chat":
        return "__end__"

    return "__end__"  # Default to end to prevent infinite loops


def coordinator_router(state: Dict[str, Any]) -> str:
    """Routes from the main coordinator."""
    next_step = state.get("next_step")

    if next_step == "synthesize":
        return "synthesize_plan"
    elif next_step == "collect_result":
        return "collect_result"
    else:
        return "judge"  # Default to judge for sub-task execution


def judgement_router(state: Dict[str, Any]) -> str:
    """Routes based on the JudgementAgent's decision, with a retry mechanism."""
    current_retries = state.get('current_retries', 0)

    if current_retries >= MAX_RETRIES:
        return "fallback"

    judgement = state.get("judgement", {})
    decision = judgement.get("decision")

    if decision == "complete":
        # Sub-task is done, collect results
        return "collect_result"

    if decision == "continue":
        tool_call = judgement.get("next_tool_call")
        if tool_call and isinstance(tool_call, dict) and tool_call.get("name"):
            return "execute_tool"
        else:
            # Continue but no valid tool call - retry
            return "judge"
    else:
        # Invalid decision - retry
        return "judge"


def validation_router(state: Dict[str, Any]) -> str:
    """Routes based on plan validation results."""
    validation_errors = state.get("validation_errors", [])
    next_step = state.get("next_step")

    if not validation_errors and next_step == "complete":
        # Validation passed, plan is good
        return "__end__"

    elif validation_errors and next_step == "adjust_plan":
        # Validation failed, need to regenerate plan
        # For now, we'll just end with errors
        # In future, could loop back to synthesize with adjustment instructions
        return "__end__"

    else:
        # Default: end
        return "__end__"
