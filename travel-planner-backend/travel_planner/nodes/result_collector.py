"""
Result Collector Node
Collects and stores results from completed sub-tasks.
Separated from Coordinator for single responsibility principle.
"""
from typing import Dict, Any


class ResultCollector:
    """
    Collects and aggregates results from sub-task execution.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def collect_result(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect the result from the last completed sub-task.

        Args:
            state: Current travel state

        Returns:
            Updated state with collected results
        """
        last_sub_task = state.get("current_sub_task")
        tool_results = state.get("tool_results", [])

        if not last_sub_task:
            # No sub-task to collect
            return {}

        # Get the final tool result
        final_tool_result = tool_results[-1] if tool_results else "No result"

        # Add to completed results
        completed_results = state.get("completed_tasks_results", {})
        completed_results[last_sub_task] = final_tool_result

        # Increment task index after completion
        current_index = state.get("current_sub_task_index", 0)
        new_index = current_index + 1

        if self.verbose:
            print(f"📥 Collected result for: '{last_sub_task}'")
            print(f"   Total completed tasks: {len(completed_results)}")

        return {
            "completed_tasks_results": completed_results,
            "current_sub_task_index": new_index
        }
