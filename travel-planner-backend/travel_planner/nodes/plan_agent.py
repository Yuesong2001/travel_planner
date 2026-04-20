"""
Tool Executor Node
This node is responsible for executing a single tool call as directed.
"""
from __future__ import annotations
import json
from typing import Any, Dict

from ..utils.tools_def import (
    create_day_by_day_plan,
    estimate_costs,
    find_attractions,
    research_destination,
    check_weather,
    suggest_restaurants,
    search_flights,
)


class ToolExecutor:
    """
    A simple executor that runs a specified tool with given arguments.
    It also provides a list of available tools and their descriptions.
    """

    def __init__(self, verbose: bool = False):
        self.tools = [
            research_destination,
            check_weather,
            estimate_costs,
            find_attractions,
            create_day_by_day_plan,
            suggest_restaurants,
            search_flights,  # NEW: Flight search tool
        ]
        self.tool_functions = {tool.__name__: tool for tool in self.tools}
        self.verbose = verbose

    @property
    def available_tools_string(self) -> str:
        """
        Returns a formatted string of available tools and their descriptions.
        """
        return "\n".join(
            f"- {tool.__name__}: {tool.__doc__.strip()}" for tool in self.tools
        )

    def execute_tool(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a tool call based on the 'judgement' from the JudgementAgent.

        Args:
            state: The current graph state.

        Returns:
            A dictionary containing the result of the tool call.
        """
        judgement = state.get("judgement", {})
        tool_call_request = judgement.get("next_tool_call")

        if not tool_call_request or not isinstance(tool_call_request, dict):
            return {"tool_results": [{"error": "No valid tool call request found."}]}

        function_name = tool_call_request.get("name")
        arguments = tool_call_request.get("arguments", {})

        if not function_name:
            return {"tool_results": [{"error": "Tool name is missing."}]}

        handler = self.tool_functions.get(function_name)
        if handler is None:
            result = f"Error: tool '{function_name}' is not available."
        else:
            try:
                # For estimate_costs, automatically add budget_amount, travelers, and itinerary_info from state if available
                if function_name == "estimate_costs":
                    constraints = state.get("constraints", {})
                    budget_limit = constraints.get("budget_limit")
                    if budget_limit and "budget_amount" not in arguments:
                        arguments["budget_amount"] = budget_limit
                    
                    # Add travelers from constraints
                    travelers = constraints.get("travelers")
                    if travelers and "travelers" not in arguments:
                        arguments["travelers"] = travelers
                    
                    # Collect itinerary information from completed tasks
                    completed_tasks_results = state.get("completed_tasks_results", {})
                    itinerary_info_parts = []
                    for task, result in completed_tasks_results.items():
                        if "itinerary" in task.lower() or "plan" in task.lower() or "day" in task.lower():
                            itinerary_info_parts.append(f"{task}: {result}")
                    if itinerary_info_parts and "itinerary_info" not in arguments:
                        arguments["itinerary_info"] = "\n".join(itinerary_info_parts)
                
                if self.verbose:
                    args_preview = ", ".join(f"{k}={v}" for k, v in arguments.items())
                    print(f"🔧 Executing tool: {function_name}({args_preview})")
                
                # Track Google Maps API tool calls
                if function_name in ["find_attractions", "suggest_restaurants"]:
                    print(f"🗺️  Google Maps API tool called: {function_name}")
                
                # The actual tool functions are LLM-based simulators
                # The JudgementAgent should provide all necessary arguments.
                result = handler(**arguments)

            except Exception as e:
                result = f"Error executing {function_name}: {str(e)}"

        # The result is appended to the existing tool_results list for the current sub-task
        existing_results = state.get("tool_results", [])
        
        # Ensure result is JSON serializable
        try:
            json.dumps(result)
        except (TypeError, OverflowError):
            result = str(result)

        return {"tool_results": existing_results + [result]}
