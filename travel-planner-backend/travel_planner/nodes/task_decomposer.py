"""
Task Decomposer Node
Breaks down a complex user request into a list of actionable sub-tasks.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List
from openai import OpenAI
import os

from ..core.prompt_templates import TASK_DECOMPOSER_PROMPT


class TaskDecomposer:
    """
    An agent responsible for breaking down a complex request into a list of sub-tasks.
    """

    def __init__(self, llm=None, *, model: str = "gpt-4o-mini", temperature: float = 0.2):
        del llm  # Not used, kept for compatibility
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.temperature = temperature
        self.system_prompt = TASK_DECOMPOSER_PROMPT

    def decompose_task(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes a user request from the state and breaks it down into sub-tasks.

        Args:
            state: The current graph state.

        Returns:
            A dictionary containing the list of sub-tasks.
        """
        user_request = state.get("user_request", {})
        constraints = state.get("constraints", {})

        if not user_request:
            return {"sub_tasks": []}

        # Format the user request for the prompt
        formatted_request = "\n".join(f"- {key}: {value}" for key, value in user_request.items() if value)

        # Add constraints context if available
        constraints_note = ""
        if constraints:
            travel_type = constraints.get("travel_type")
            interests = constraints.get("interests", [])

            if travel_type:
                constraints_note += f"\n\nTravel Type: {travel_type}"
                constraints_note += f"\nNote: Consider {travel_type}-specific recommendations when planning."

            if interests:
                constraints_note += f"\nInterests: {', '.join(interests)}"
                constraints_note += f"\nNote: Prioritize activities matching these interests."

        prompt = f"User Request:\n{formatted_request}{constraints_note}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
        )

        content = response.choices[0].message.content or ""
        sub_tasks = self._parse_sub_tasks(content)

        # Print all subtasks after decomposition
        print("=" * 100)
        print("📋📋📋 SUBTASKS DECOMPOSED 📋📋📋")
        print("=" * 100)
        for i, task in enumerate(sub_tasks, 1):
            print(f"  {i}. {task}")
        print("=" * 100)
        print(f"✅ Total: {len(sub_tasks)} subtasks\n")

        return {"sub_tasks": sub_tasks}

    @staticmethod
    def _parse_sub_tasks(text: str) -> List[str]:
        """Parses the LLM's numbered list output into a Python list of strings."""
        # Find all lines starting with a number and a dot
        tasks = re.findall(r"^\s*\d+\.\s*(.*)", text, re.MULTILINE)
        # Strip any leading/trailing whitespace from each task
        return [task.strip() for task in tasks]

