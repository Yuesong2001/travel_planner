"""
Graph Builder V5 - Improved Architecture
Builds the travel planning workflow with:
- Restructured node organization (nodes/, routers/, core/, utils/)
- Plan validation node
- Result collection separation
- Clear routing logic
- Backward compatible with V4
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from .core.state import TravelState
from .nodes import (
    ChatNode,
    Coordinator,
    DataNormalizer,
    TaskDecomposer,
    JudgementAgent,
    ToolExecutor,
    PlanSynthesizer,
    PlanValidator,
    ResultCollector,
    PlanRefiner,
)
from .routers import (
    entry_router,
    chat_router,
    coordinator_router,
    judgement_router,
    validation_router,
)

MAX_RETRIES = 3


def build_travel_graph(llm, verbose: bool = False, enable_validation: bool = True, trace_name: str = None, custom_judgement_prompt: str = None):
    """
    Builds the V5 travel planning graph with improved architecture.

    Args:
        llm: The language model to use
        verbose: Whether to print verbose logs
        enable_validation: Whether to enable plan validation (recommended)
        trace_name: Optional name for LangSmith trace (backward compatible)
        custom_judgement_prompt: Optional custom prompt for judgement agent (backward compatible)

    Returns:
        Compiled LangGraph workflow
    """
    # --- 1. Initialize all components ---
    coordinator = Coordinator()
    chat_node = ChatNode(llm)
    normalizer = DataNormalizer()
    task_decomposer = TaskDecomposer(llm)
    tool_executor = ToolExecutor(verbose=verbose)

    # Support custom judgement prompt for backward compatibility
    if custom_judgement_prompt:
        judgement_agent = JudgementAgent(llm, tool_executor=tool_executor, custom_prompt=custom_judgement_prompt)
    else:
        judgement_agent = JudgementAgent(llm, tool_executor=tool_executor)

    plan_synthesizer = PlanSynthesizer(llm, output_format="json")  # Only JSON (faster, frontend only needs JSON)
    plan_validator = PlanValidator(verbose=verbose)
    result_collector = ResultCollector(verbose=verbose)
    plan_refiner = PlanRefiner(llm, verbose=verbose)  # New: plan refinement node

    # --- 2. Define Node Handlers ---

    def chat_handler(state: TravelState) -> Dict[str, Any]:
        """Chat node: handle user input and extract constraints"""
        return chat_node.process_message(state)

    def normalize_handler(state: TravelState) -> Dict[str, Any]:
        """Normalize user request with LLM-powered standardization"""
        normalized_request = normalizer.normalize_travel_request_with_llm(state.get("user_request", {}))
        return {"user_request": normalized_request}

    def task_decomposer_handler(state: TravelState) -> Dict[str, Any]:
        """Decompose user request into sub-tasks"""
        result = task_decomposer.decompose_task(state)
        # Note: Printing is handled inside task_decomposer.decompose_task()
        return {
            "sub_tasks": result.get("sub_tasks", []),
            "current_sub_task_index": 0,
            "completed_tasks_results": {},
        }

    def coordinator_handler(state: TravelState) -> Dict[str, Any]:
        """
        Coordinate sub-task execution.
        Simplified: only manages task sequencing.
        """
        index = state.get("current_sub_task_index", 0)
        sub_tasks = state.get("sub_tasks", [])

        if verbose:
            print(f"📋 Coordinator: Task {index}/{len(sub_tasks)}")

        # Check if all tasks are done
        if index >= len(sub_tasks):
            if verbose:
                print(f"🎯 All {len(sub_tasks)} tasks completed → Synthesizing plan")
            return {"next_step": "synthesize", "status": "synthesizing"}

        # Set up next sub-task
        next_sub_task = sub_tasks[index]
        if verbose:
            print(f"➡️  Starting task {index + 1}/{len(sub_tasks)}: '{next_sub_task}'")

        return {
            "current_sub_task": next_sub_task,
            "current_sub_task_index": index,  # Keep current index, will increment after completion
            "tool_results": [],  # Clear for new sub-task
            "next_step": "judge",
            "current_retries": 0,
        }

    def result_collector_handler(state: TravelState) -> Dict[str, Any]:
        """Collect results from completed sub-task"""
        result = result_collector.collect_result(state)
        # After collecting, go back to coordinator
        result["next_step"] = "continue"
        return result

    def judgement_handler(state: TravelState) -> Dict[str, Any]:
        """Judge whether to call tool or complete sub-task"""
        current_retries = state.get('current_retries', 0)

        result = judgement_agent.make_decision(state)

        decision = result.get("judgement", {}).get("decision")
        tool_call = result.get("judgement", {}).get("next_tool_call")

        # Increment retry if decision is invalid
        if decision == "continue":
            if not (tool_call and isinstance(tool_call, dict) and tool_call.get("name")):
                current_retries += 1
        elif decision not in ["complete", "continue"]:
            current_retries += 1

        result['current_retries'] = current_retries
        return result

    def tool_executor_handler(state: TravelState) -> Dict[str, Any]:
        """Execute tool"""
        return tool_executor.execute_tool(state)

    def plan_synthesizer_handler(state: TravelState) -> Dict[str, Any]:
        """Synthesize final plan"""
        result = plan_synthesizer.synthesize_plan(state)

        # Add to plan history
        plan = result.get("plan")
        if plan:
            plan_history = state.get("plan_history", [])
            plan_history.append(plan)
            result["plan_history"] = plan_history

        if verbose:
            print(f"🎨 Synthesized plan: {'✓ Has plan' if plan else '✗ No plan'}")
            if plan:
                print(f"   Plan keys: {list(plan.keys())}")

        result["status"] = "synthesized"
        return result

    def plan_validator_handler(state: TravelState) -> Dict[str, Any]:
        """Validate the generated plan"""
        return plan_validator.validate_plan(state)

    def refine_plan_handler(state: TravelState) -> Dict[str, Any]:
        """Refine an existing plan based on user feedback"""
        result = plan_refiner.refine_plan(state)

        if verbose:
            plan = result.get("plan")
            status = result.get("status")
            print(f"🔧 Refined plan: status={status}, has_plan={plan is not None}")

        return result

    def fallback_handler(state: TravelState) -> Dict[str, Any]:
        """Fallback node for errors"""
        errors = state.get("errors", [])
        failed_subtask = state.get("current_sub_task")
        retry_count = state.get("current_retries", 0)

        error_msg = f"Failed at: {failed_subtask} after {retry_count} retries."
        if errors:
            error_msg += f" Errors: {', '.join(errors)}"

        return {
            "travel_plan": f"I apologize, but I encountered an issue and cannot complete your travel plan. {error_msg}",
            "status": "failed",
            "errors": errors + [error_msg]
        }

    # --- 3. Build the Graph ---
    workflow = StateGraph(TravelState)

    # Add nodes
    workflow.add_node("chat", chat_handler)
    workflow.add_node("normalize_input", normalize_handler)
    workflow.add_node("decompose_task", task_decomposer_handler)
    workflow.add_node("coordinator", coordinator_handler)
    workflow.add_node("collect_result", result_collector_handler)
    workflow.add_node("judge", judgement_handler)
    workflow.add_node("execute_tool", tool_executor_handler)
    workflow.add_node("synthesize_plan", plan_synthesizer_handler)
    workflow.add_node("refine_plan", refine_plan_handler)  # New: plan refinement node
    workflow.add_node("fallback", fallback_handler)

    if enable_validation:
        workflow.add_node("validate_plan", plan_validator_handler)

    # Set entry point
    workflow.set_entry_point("chat")

    # Add edges
    workflow.add_conditional_edges("chat", chat_router, {
        "normalize_input": "normalize_input",
        "refine_plan": "refine_plan",  # New: route to plan refinement
        "__end__": END
    })

    workflow.add_edge("normalize_input", "decompose_task")
    workflow.add_edge("decompose_task", "coordinator")

    workflow.add_conditional_edges("coordinator", coordinator_router, {
        "synthesize_plan": "synthesize_plan",
        "collect_result": "collect_result",
        "judge": "judge"
    })

    # After collecting result, return to coordinator
    workflow.add_edge("collect_result", "coordinator")

    workflow.add_conditional_edges("judge", judgement_router, {
        "collect_result": "collect_result",
        "execute_tool": "execute_tool",
        "judge": "judge",
        "fallback": "fallback"
    })

    workflow.add_edge("execute_tool", "judge")

    if enable_validation:
        # Add validation after synthesis
        workflow.add_edge("synthesize_plan", "validate_plan")
        # Add validation after refinement (optional, for consistency)
        workflow.add_edge("refine_plan", "validate_plan")
        workflow.add_conditional_edges("validate_plan", validation_router, {
            "__end__": END
        })
    else:
        workflow.add_edge("synthesize_plan", END)
        # Refine plan goes directly to END if validation is disabled
        workflow.add_edge("refine_plan", END)

    workflow.add_edge("fallback", END)

    # Compile
    graph = workflow.compile()
    return graph


def create_travel_planner(llm, verbose=False, enable_validation=True):
    """Creates a travel planner instance."""
    return build_travel_graph(llm, verbose=verbose, enable_validation=enable_validation)


if __name__ == "__main__":
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    planner = create_travel_planner(llm, verbose=True)

    initial_state = {
        "user_message": "Plan a 3-day honeymoon to Paris with $2000. We love romantic restaurants and art.",
        "user_request": {
            "destination": "Paris",
            "duration": "3 days",
            "budget": "$2000",
            "interests": "romantic restaurants, art",
            "travel_type": "honeymoon"
        },
        "messages": [],
        "intent": "plan"
    }

    print("\n🚀 Running Travel Planner V5...\n")

    for event in planner.stream(initial_state, {"recursion_limit": 100}):
        for node_name, node_output in event.items():
            print(f"✓ {node_name}")

    print("\n✅ Completed!")
