"""
Validate Plan Node
Validates the generated plan against constraints and provides adjustment suggestions.
"""
from typing import Dict, Any, List


class PlanValidator:
    """
    Validates travel plans against user constraints.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def validate_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the plan against constraints.

        Args:
            state: Current travel state

        Returns:
            Dictionary with validation results
        """
        plan = state.get("plan")
        constraints = state.get("constraints", {})
        errors = []

        if not plan:
            return {
                "validation_errors": ["No plan to validate"],
                "next_step": "synthesize"  # Need to generate a plan first
            }

        if self.verbose:
            print("\n🔍 Validating plan...")

        # Validation 1: Check budget
        budget_error = self._validate_budget(plan, constraints)
        if budget_error:
            errors.append(budget_error)

        # Validation 2: Check days match duration
        duration_error = self._validate_duration(plan, state.get("user_request", {}))
        if duration_error:
            errors.append(duration_error)

        # Validation 3: Check interests are reflected
        interests_error = self._validate_interests(plan, constraints)
        if interests_error:
            errors.append(interests_error)

        # Validation 4: Check travel type appropriateness
        travel_type_error = self._validate_travel_type(plan, constraints)
        if travel_type_error:
            errors.append(travel_type_error)

        if errors:
            if self.verbose:
                print(f"❌ Validation failed with {len(errors)} errors:")
                for error in errors:
                    print(f"   - {error}")

            return {
                "validation_errors": errors,
                "next_step": "adjust_plan",  # Need adjustments
                "status": "validation_failed"
            }
        else:
            if self.verbose:
                print("✅ Plan validation passed!")

            return {
                "validation_errors": [],
                "next_step": "complete",
                "status": "validated"
            }

    def _validate_budget(self, plan: Dict[str, Any], constraints: Dict[str, Any]) -> str:
        """Validate budget constraints."""
        budget_limit = constraints.get("budget_limit")
        if not budget_limit:
            return None  # No budget limit specified

        plan_budget = plan.get("budget", {})
        estimated_total = plan_budget.get("estimated_total")

        if not estimated_total:
            return None  # No budget estimate in plan

        if estimated_total > budget_limit:
            overage = estimated_total - budget_limit
            currency = constraints.get("currency", "USD")
            return f"Budget exceeded by {currency} {overage:.2f} (limit: {budget_limit}, estimated: {estimated_total})"

        return None

    def _validate_duration(self, plan: Dict[str, Any], user_request: Dict[str, Any]) -> str:
        """Validate that the number of days matches the requested duration."""
        duration_str = user_request.get("duration", "")
        plan_days = plan.get("days", [])

        if not duration_str or not plan_days:
            return None

        # Extract number from duration string (e.g., "3 days" → 3)
        import re
        match = re.search(r'(\d+)', duration_str)
        if not match:
            return None

        requested_days = int(match.group(1))
        actual_days = len(plan_days)

        if actual_days != requested_days:
            return f"Day count mismatch: requested {requested_days} days but plan has {actual_days} days"

        return None

    def _validate_interests(self, plan: Dict[str, Any], constraints: Dict[str, Any]) -> str:
        """Validate that plan reflects user interests."""
        interests = constraints.get("interests", [])
        if not interests or interests == ["general sightseeing"]:
            return None  # No specific interests to validate

        plan_days = plan.get("days", [])
        if not plan_days:
            return None

        # Check if at least some items mention the interests
        all_items_text = ""
        for day in plan_days:
            for item in day.get("items", []):
                all_items_text += f" {item.get('place', '')} {item.get('reason', '')}"

        all_items_text = all_items_text.lower()

        matched_interests = []
        for interest in interests:
            if interest.lower() in all_items_text:
                matched_interests.append(interest)

        if not matched_interests and len(interests) > 0:
            return f"Plan does not reflect user interests: {', '.join(interests)}"

        return None

    def _validate_travel_type(self, plan: Dict[str, Any], constraints: Dict[str, Any]) -> str:
        """Validate that plan is appropriate for travel type."""
        travel_type = constraints.get("travel_type")
        if not travel_type:
            return None  # No specific travel type

        plan_days = plan.get("days", [])
        if not plan_days:
            return None

        # Check for travel type appropriateness
        all_items_text = ""
        for day in plan_days:
            for item in day.get("items", []):
                all_items_text += f" {item.get('place', '')} {item.get('reason', '')}"

        all_items_text = all_items_text.lower()

        # Travel type specific checks
        if travel_type.lower() in ["honeymoon", "romantic"]:
            if "romantic" not in all_items_text and "couple" not in all_items_text:
                return f"Plan does not seem appropriate for {travel_type} trip"

        if travel_type.lower() in ["family", "family vacation"]:
            if "family" not in all_items_text and "kids" not in all_items_text and "children" not in all_items_text:
                return f"Plan may not be suitable for {travel_type}"

        if travel_type.lower() in ["budget", "graduation trip", "backpacking"]:
            budget = plan.get("budget", {}).get("estimated_total", 0)
            if budget > 2000:  # Threshold for budget trips
                return f"Plan seems expensive for {travel_type}"

        return None
