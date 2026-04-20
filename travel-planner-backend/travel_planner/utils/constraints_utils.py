"""
Constraint Utilities Module
Provides helper functions for parsing and handling travel planning constraints.
Supports both regex-based parsing (fast) and LLM-based parsing (accurate fallback).
"""
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from ..core.state import PlanConstraints


class ParsedConstraints(BaseModel):
    """Pydantic model for LLM-based constraint parsing."""
    budget_limit: Optional[float] = Field(None, description="Numeric budget value")
    currency: Optional[str] = Field(None, description="Currency code (USD, EUR, etc.)")
    travelers: Optional[int] = Field(None, description="Number of travelers")
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    interests: Optional[List[str]] = Field(None, description="List of interest keywords")


def parse_with_llm(
    user_request: Dict[str, Any],
    llm: Any,
    today: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use LLM to intelligently parse constraint fields from user request.

    This is a fallback when regex parsing fails or for complex natural language.

    Args:
        user_request: Raw user request dictionary
        llm: LangChain LLM instance
        today: Today's date in YYYY-MM-DD format (for relative date parsing)

    Returns:
        Dictionary with parsed constraint values

    Examples:
        >>> parse_with_llm({"budget": "1000$ 的 travel"}, llm)
        {"budget_limit": 1000.0, "currency": "USD"}

        >>> parse_with_llm({"travelers": "我和我女朋友"}, llm)
        {"travelers": 2}
    """
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")

    # Build context for LLM
    context = f"""
Parse the following travel request fields and extract structured information.

**User Request:**
{json.dumps(user_request, indent=2, ensure_ascii=False)}

**Today's Date:** {today}

**Instructions:**
1. Extract numeric budget value from the budget field (ignore words like "travel", "的", etc.)
2. Infer number of travelers from phrases like:
   - "我和我女朋友" → 2
   - "couple" → 2
   - "family of 4" → 4
   - "solo" → 1
3. Convert relative dates to YYYY-MM-DD format (Today is {today}):
   - "this weekend" → if today is Sunday-Thursday: next Saturday ({today}+days), if Friday/Saturday: this Saturday
   - "this weekend" should return start_date=Saturday and end_date=Sunday
   - "next weekend" → Saturday and Sunday of next week
   - "下周五" / "next Friday" → calculate from today
   - "June 15, 2025" → use the EXACT year provided: "2025-06-15" (do NOT change the year)
   - "June 15" (no year) → use current year if not passed, otherwise next year
   - IMPORTANT: If user provides explicit year (e.g., "2025"), ALWAYS use that year even if it's in the past
   - IMPORTANT: For weekend trips, set both start_date and end_date (Saturday to Sunday)
4. Extract interest keywords, removing filler words like "I like", "我喜欢"

**Return only the fields you can confidently parse. Set uncertain fields to null.**
"""

    try:
        # Use structured output if available
        if hasattr(llm, 'with_structured_output'):
            structured_llm = llm.with_structured_output(ParsedConstraints)
            result = structured_llm.invoke(context)
            return result.dict(exclude_none=True)
        else:
            # Fallback: use regular LLM and parse JSON
            response = llm.invoke(context)
            content = response.content.strip()

            # Clean up markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            parsed = json.loads(content)
            return {k: v for k, v in parsed.items() if v is not None}

    except Exception as e:
        print(f"Warning: LLM parsing failed: {e}")
        return {}


def parse_budget(budget_str: Optional[str], llm: Any = None) -> Optional[float]:
    """
    Parse budget string to extract numeric value using LLM.

    Args:
        budget_str: Budget string (e.g., '$1000', '800 USD', '1.5k', '1000$ 的 travel')
        llm: LLM instance for parsing (required for non-trivial cases)

    Returns:
        Float budget value or None if not parseable

    Examples:
        >>> parse_budget("$1000", llm)
        1000.0
        >>> parse_budget("1000$ 的 travel", llm)
        1000.0
        >>> parse_budget("moderate", llm)
        None
    """
    if not budget_str:
        return None

    # Use LLM for all parsing
    if llm:
        try:
            llm_result = parse_with_llm({"budget": budget_str}, llm)
            budget_limit = llm_result.get('budget_limit')
            if budget_limit is not None:
                return float(budget_limit)
        except Exception as e:
            print(f"Warning: LLM budget parsing failed: {e}")

    return None


def infer_currency(destination: str) -> str:
    """
    Infer currency based on destination.

    Args:
        destination: Destination name

    Returns:
        Currency code (default: USD)
    """
    destination_lower = destination.lower()

    # European countries
    if any(country in destination_lower for country in [
        'france', 'paris', 'germany', 'berlin', 'italy', 'rome',
        'spain', 'madrid', 'barcelona', 'netherlands', 'amsterdam'
    ]):
        return 'EUR'

    # UK
    if any(place in destination_lower for place in ['london', 'uk', 'england', 'britain']):
        return 'GBP'

    # Japan
    if any(place in destination_lower for place in ['japan', 'tokyo', 'osaka', 'kyoto']):
        return 'JPY'

    # China
    if any(place in destination_lower for place in ['china', 'beijing', 'shanghai']):
        return 'CNY'

    # Default to USD
    return 'USD'


def parse_interests(interests_str: Optional[str], llm: Any = None) -> List[str]:
    """
    Parse interests string into a list of interest keywords using LLM.

    Args:
        interests_str: Comma-separated or natural language interests
        llm: LLM instance for parsing

    Returns:
        List of interest keywords

    Examples:
        >>> parse_interests("food, museums, history", llm)
        ['food', 'museums', 'history']
        >>> parse_interests("I like nature and hiking", llm)
        ['nature', 'hiking']
        >>> parse_interests("我喜欢美食和博物馆", llm)
        ['food', 'museums']
    """
    if not interests_str:
        return ['general sightseeing']

    # Use LLM for all parsing
    if llm:
        try:
            llm_result = parse_with_llm({"interests": interests_str}, llm)
            interests_list = llm_result.get('interests')
            if interests_list and isinstance(interests_list, list) and len(interests_list) > 0:
                return interests_list
        except Exception as e:
            print(f"Warning: LLM interests parsing failed: {e}")

    # Fallback: return as-is or general sightseeing
    return [interests_str.strip().lower()] if interests_str and interests_str.strip() else ['general sightseeing']


def parse_travelers(travelers_str: Optional[str], llm: Any = None) -> int:
    """
    Parse travelers string to extract number of travelers using LLM.

    Args:
        travelers_str: Travelers description (e.g., '2 adults, 1 child', 'solo', '我和我女朋友')
        llm: LLM instance for parsing

    Returns:
        Number of travelers (default: 1)

    Examples:
        >>> parse_travelers("2 adults, 1 child", llm)
        3
        >>> parse_travelers("solo", llm)
        1
        >>> parse_travelers("我和我女朋友", llm)
        2
    """
    if not travelers_str:
        return 1

    # Use LLM for all parsing
    if llm:
        try:
            llm_result = parse_with_llm({"travelers": travelers_str}, llm)
            travelers_count = llm_result.get('travelers')
            if travelers_count is not None:
                return int(travelers_count)
        except Exception as e:
            print(f"Warning: LLM travelers parsing failed: {e}")

    # Default to 1
    return 1


def normalize_date(date_str: Optional[str], llm: Any = None, field_name: str = "date") -> Optional[str]:
    """
    Normalize date string to ISO format using LLM.

    Args:
        date_str: Date string in various formats (e.g., "下周五", "next Friday", "June 15")
        llm: LLM instance for parsing
        field_name: "start_date" or "end_date" for context

    Returns:
        ISO format date string (YYYY-MM-DD) or original string if not parseable

    Examples:
        >>> normalize_date("2025-06-15", llm)
        "2025-06-15"
        >>> normalize_date("下周五", llm)
        "2025-11-29"  # (calculated from today)
        >>> normalize_date("next Friday", llm)
        "2025-11-29"
    """
    if not date_str:
        return None

    # Use LLM for all parsing
    if llm:
        try:
            llm_result = parse_with_llm({field_name: date_str}, llm)
            parsed_date = llm_result.get(field_name)
            if parsed_date:
                return parsed_date
        except Exception as e:
            print(f"Warning: LLM date parsing failed: {e}")

    # Fallback: return original
    return date_str


def get_default_constraints(user_request: Dict[str, Any], llm: Any = None) -> PlanConstraints:
    """
    Build a PlanConstraints object with defaults for missing fields.
    Uses LLM for intelligent parsing of constraint fields.
    OPTIMIZED: Uses a single LLM call to parse all fields at once instead of multiple calls.

    Args:
        user_request: Extracted user request dictionary
        llm: LLM instance for parsing (recommended)

    Returns:
        PlanConstraints with all fields populated (using defaults where needed)
    """
    destination = user_request.get('destination', '')

    # Get today's date for relative date parsing
    today = datetime.now().strftime("%Y-%m-%d")

    # OPTIMIZED: Parse all fields in a single LLM call
    if llm:
        try:
            # Use parse_with_llm to parse all fields at once
            parsed = parse_with_llm(user_request, llm, today=today)
            
            # Extract parsed values
            budget_limit = parsed.get('budget_limit')
            if budget_limit is None and user_request.get('budget'):
                # Fallback: try parsing budget separately if not found
                budget_limit = parse_budget(user_request.get('budget'), llm=llm)
            
            interests = parsed.get('interests')
            if not interests or (isinstance(interests, list) and len(interests) == 0):
                # Fallback: try parsing interests separately if not found
                interests = parse_interests(user_request.get('interests'), llm=llm)

            # Final fallback: ensure interests is never empty
            if not interests or (isinstance(interests, list) and len(interests) == 0):
                interests = ['general sightseeing']
            
            travelers = parsed.get('travelers')
            if travelers is None:
                # Fallback: try parsing travelers separately if not found
                travelers = parse_travelers(user_request.get('travelers'), llm=llm)
            
            start_date = parsed.get('start_date')
            if not start_date:
                # Fallback: try parsing start_date separately if not found
                start_date = normalize_date(user_request.get('start_date'), llm=llm, field_name="start_date")
            
            end_date = parsed.get('end_date')
            if not end_date:
                # Fallback: try parsing end_date separately if not found
                end_date = normalize_date(user_request.get('end_date'), llm=llm, field_name="end_date")
        except Exception as e:
            # If single LLM call fails, fall back to individual parsing
            print(f"Warning: Single LLM parsing failed, using individual parsing: {e}")
            budget_limit = parse_budget(user_request.get('budget'), llm=llm)
            interests = parse_interests(user_request.get('interests'), llm=llm)
            travelers = parse_travelers(user_request.get('travelers'), llm=llm)
            start_date = normalize_date(user_request.get('start_date'), llm=llm, field_name="start_date")
            end_date = normalize_date(user_request.get('end_date'), llm=llm, field_name="end_date")
    else:
        # No LLM available, use basic parsing
        budget_limit = None
        interests = [user_request.get('interests')] if user_request.get('interests') else ['general sightseeing']
        travelers = 1
        start_date = user_request.get('start_date')
        end_date = user_request.get('end_date')

    # Get travel type and origin (no parsing needed)
    travel_type = user_request.get('travel_type')
    origin = user_request.get('origin')  # NEW: Extract origin from user_request

    # Infer currency
    currency = infer_currency(destination)

    return PlanConstraints(
        origin=origin,  # NEW: Add origin to constraints
        budget_limit=budget_limit,
        currency=currency,
        start_date=start_date,
        end_date=end_date,
        interests=interests,
        travelers=travelers,
        travel_type=travel_type
    )


def validate_hard_constraints(user_request: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate that hard constraints are present.

    Minimum requirements: destination + start_date + end_date + origin (optional but recommended)

    Args:
        user_request: Extracted user request dictionary

    Returns:
        (is_valid, missing_field_message)
    """
    destination = user_request.get('destination')
    start_date = user_request.get('start_date')
    end_date = user_request.get('end_date')
    origin = user_request.get('origin')

    if not destination:
        return False, "I need to know your destination. Where would you like to travel?"

    if not start_date or not end_date:
        return False, f"When do you want to travel to {destination}? Please tell me the dates (e.g., 'July 7-11')."

    # Check if origin is needed (ask only if destination is provided)
    if not origin:
        return False, f"Where will you be departing from for your trip to {destination}?"

    return True, None
