"""
Judgement Agent V4
This agent evaluates the results of a tool call and decides the next step for a sub-task.
"""
import json
import re
from typing import Dict, Any, List, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..core.prompt_templates import JUDGEMENT_AGENT_PROMPT
from .plan_agent import ToolExecutor

class JudgementAgent:
    """
    The JudgementAgent evaluates the state of a sub-task and decides what to do next.
    It can either decide the sub-task is complete or that another tool call is needed.
    """
    def __init__(self, llm, tool_executor: ToolExecutor, custom_prompt: str = None):
        self.llm = llm
        self.output_parser = JsonOutputParser()
        
        # Get the list of available tools from the provided executor
        available_tools_string = tool_executor.available_tools_string

        # Use custom prompt if provided, otherwise use default
        prompt_template_str = custom_prompt if custom_prompt else JUDGEMENT_AGENT_PROMPT

        self.prompt_template = PromptTemplate(
            template=prompt_template_str,
            input_variables=["sub_task", "tool_results", "conversation_history", "user_request", "completed_tasks"],
            partial_variables={
                "format_instructions": self.output_parser.get_format_instructions(),
                "available_tools": available_tools_string
            }
        )
        self.chain = self.prompt_template | self.llm | self.output_parser

    def make_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates the current sub-task and tool results to make a decision.

        Args:
            state: The current graph state.

        Returns:
            A dictionary containing the agent's judgement.
        """
        sub_task = state.get("current_sub_task")
        tool_results = state.get("tool_results", [])
        conversation_history = state.get("conversation_history", [])
        user_request = state.get("user_request")
        completed_tasks_results = state.get("completed_tasks_results", {})

        # Check retry limit - default max 3 retries per sub-task
        max_retries = state.get("max_retries", 3)
        current_retries = state.get("current_retries", 0)

        # If we've hit the retry limit, force complete
        if current_retries >= max_retries and tool_results:
            print(f"⚠️ Max retries ({max_retries}) reached for sub-task. Forcing completion with current results.")
            return {
                "judgement": {
                    "decision": "complete",
                    "next_thought": f"Maximum retry limit reached. Proceeding with available information: {tool_results[-1] if tool_results else 'No results'}",
                    "next_tool_call": None
                },
                "current_retries": 0  # Reset for next sub-task
            }

        # Format completed tasks for the prompt
        completed_tasks_str = ""
        if completed_tasks_results:
            completed_tasks_list = [f"- {task}" for task in completed_tasks_results.keys()]
            completed_tasks_str = f"\nCompleted sub-tasks so far:\n" + "\n".join(completed_tasks_list)
        else:
            completed_tasks_str = "No sub-tasks have been completed yet."

        # Prepare the input for the LLM chain
        chain_input = {
            "sub_task": sub_task,
            "tool_results": "\n".join(map(str, tool_results)),
            "conversation_history": "\n".join(map(str, conversation_history)),
            "user_request": user_request,
            "completed_tasks": completed_tasks_str
        }

        # Invoke the chain and get the structured output
        try:
            judgement_output = self.chain.invoke(chain_input)
        except Exception as e:
            # If JSON parsing fails, try to clean and parse manually
            if "Invalid json" in str(e) or "OUTPUT_PARSING" in str(e):
                # Try to extract JSON from the error message or raw output
                raw_output = str(e)
                # Try to find JSON in the error message
                json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    # Remove comments (// ... and /* ... */)
                    json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
                    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                    try:
                        judgement_output = json.loads(json_str)
                    except:
                        # If still fails, return a default decision
                        judgement_output = {
                            "decision": "continue",
                            "next_thought": "Error parsing JSON, will retry with tool call",
                            "next_tool_call": None
                        }
                else:
                    # Fallback: return default decision
                    judgement_output = {
                        "decision": "continue",
                        "next_thought": "Error parsing JSON output, will retry",
                        "next_tool_call": None
                    }
            else:
                raise

        # Increment retry counter if decision is "continue", reset if "complete"
        result = {"judgement": judgement_output}
        if judgement_output.get("decision") == "continue":
            result["current_retries"] = current_retries + 1
        else:
            result["current_retries"] = 0  # Reset for next sub-task

        return result
