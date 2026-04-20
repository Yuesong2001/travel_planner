"""
Refine Plan Node
Handles incremental modifications to existing travel plans.
This is much faster than regenerating the entire plan from scratch.
"""
import json
from typing import Dict, Any
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage


class PlanRefiner:
    """
    Node for refining existing travel plans based on user feedback.
    Uses LLM to make targeted modifications without regenerating the entire plan.
    """

    def __init__(self, llm, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose

    def refine_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refine an existing plan based on user's modification request.

        Args:
            state: Must contain:
                - plan: The existing plan (Dict)
                - refinement_request: User's modification request (Dict with 'description' key)

        Returns:
            Updated state with modified plan
        """
        existing_plan = state.get("plan")
        refinement_request = state.get("refinement_request", {})
        modification_description = refinement_request.get("description", "")

        if not existing_plan:
            if self.verbose:
                print("⚠️  PlanRefiner: No existing plan found, cannot refine")
            return {
                "ai_response": "I don't have an existing plan to modify. Would you like me to create a new travel plan?",
                "intent": "chat",
                "status": "awaiting_input"
            }

        if not modification_description:
            if self.verbose:
                print("⚠️  PlanRefiner: No modification description provided")
            return {
                "ai_response": "Could you please specify what you'd like to change in your travel plan?",
                "intent": "chat",
                "status": "awaiting_input"
            }

        if self.verbose:
            print(f"🔧 PlanRefiner: Modifying plan based on: '{modification_description}'")

        # Build prompt for LLM to modify the plan
        system_message = SystemMessage(content="""You are a travel plan modification assistant.

Your task is to modify an existing travel plan based on the user's request.

**Important Guidelines:**
1. Only modify the parts that the user requested to change
2. Keep all other parts of the plan unchanged
3. Ensure the modified plan maintains the same JSON structure
4. Preserve the destination, dates, budget unless explicitly asked to change
5. If modifying a specific day, only change that day's itinerary
6. Return the COMPLETE modified plan in JSON format

**Response Format:**
Return a valid JSON object with the same structure as the original plan.
Do not add any explanation text, only return the JSON.""")

        user_message = HumanMessage(content=f"""Original Plan:
{json.dumps(existing_plan, indent=2)}

User's Modification Request:
{modification_description}

Please return the modified plan as a complete JSON object.""")

        try:
            # Call LLM to modify the plan
            if self.verbose:
                print("🤖 PlanRefiner: Calling LLM to modify plan...")

            response = self.llm.invoke([system_message, user_message])
            response_text = response.content.strip()

            # Extract JSON from response (handle cases where LLM adds markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Parse the modified plan
            modified_plan = json.loads(response_text)

            # Update version and timestamp
            modified_plan["version"] = existing_plan.get("version", 1) + 1
            modified_plan["generated_at"] = datetime.utcnow().isoformat() + "Z"
            modified_plan["last_modified"] = datetime.utcnow().isoformat() + "Z"
            modified_plan["modification_note"] = modification_description

            if self.verbose:
                print(f"✅ PlanRefiner: Successfully modified plan (v{modified_plan['version']})")

            # Generate a confirmation message
            ai_response = self._generate_confirmation_message(modification_description, modified_plan)

            return {
                "plan": modified_plan,
                "ai_response": ai_response,
                "status": "refined",
                "intent": "refine"
            }

        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"❌ PlanRefiner: Failed to parse modified plan JSON: {e}")
                print(f"   Response text: {response_text[:200]}...")

            return {
                "ai_response": "I had trouble modifying your plan. Could you rephrase your request?",
                "intent": "chat",
                "status": "refinement_failed",
                "errors": [f"JSON parse error: {str(e)}"]
            }

        except Exception as e:
            if self.verbose:
                print(f"❌ PlanRefiner: Error during plan refinement: {e}")

            return {
                "ai_response": "I encountered an error while modifying your plan. Please try again.",
                "intent": "chat",
                "status": "refinement_failed",
                "errors": [str(e)]
            }

    def _generate_confirmation_message(self, modification: str, modified_plan: Dict[str, Any]) -> str:
        """
        Generate a friendly confirmation message about what was changed.
        """
        destination = modified_plan.get("destination", "your destination")
        version = modified_plan.get("version", 1)

        # Try to be specific about what changed
        message = f"I've updated your {destination} travel plan (version {version}) based on your request: \"{modification}\"."

        # Check if a specific day was modified
        if "day" in modification.lower() or "第" in modification:
            message += " The day-by-day itinerary has been adjusted accordingly."

        message += " Would you like to make any other changes?"

        return message


# For backward compatibility
def create_plan_refiner(llm, verbose=False):
    """Factory function to create a PlanRefiner instance."""
    return PlanRefiner(llm, verbose=verbose)
