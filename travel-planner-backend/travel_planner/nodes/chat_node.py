"""
Chat Node Module
Handles user interaction, conversation management, and robustly extracts structured information.
This version simplifies the logic to perform a single, clear function per invocation.
"""
import json
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError
from ..utils.constraints_utils import get_default_constraints, validate_hard_constraints

# Pydantic model for structured information extraction.
# All fields are optional to allow for partial extraction during a conversation.
class TravelRequest(BaseModel):
    origin: str | None = Field(None, description="The departure location (e.g., 'San Francisco', 'New York', 'LAX'). Look for patterns like 'from [city]', 'departing from [city]', 'leaving from [city]'.")
    destination: str | None = Field(None, description="The travel destination (e.g., 'Paris', 'Tokyo', 'New York').")
    start_date: str | None = Field(None, description="The start date of the trip (e.g., '2025-06-15', 'June 15', 'Nov 22').")
    end_date: str | None = Field(None, description="The end date of the trip (e.g., '2025-06-20', 'June 20', 'Nov 24').")
    travelers: str | None = Field(None, description="Number and type of travelers (e.g., '2 adults, 1 child', 'solo', '4 people', 'couple').")
    budget: str | None = Field(None, description="The budget for the trip (e.g., '$1000', '800 USD', 'moderate').")
    interests: str | None = Field(None, description="The traveler's interests (e.g., 'food, museums', 'nature, hiking', 'romantic dining').")
    travel_type: str | None = Field(None, description="The type of travel (e.g., 'honeymoon', 'graduation trip', 'family vacation', 'business trip', 'solo adventure').")

class ChatNode:
    """
    Node for handling conversations and extracting travel request details.
    This node is stateless and performs one of two actions per call:
    1. Extracts complete information and signals to plan.
    2. Asks a clarifying question and signals to continue chatting.
    """
    
    def __init__(self, llm):
        self.llm = llm
        self.extraction_llm = llm.with_structured_output(TravelRequest)
        self.chat_system_message = SystemMessage(
            content="""You are a friendly and helpful travel planning assistant.

**Your Role:**
- Help users by collecting their travel requirements through conversation
- Ask clarifying questions to gather all necessary information
- Once you have enough information, the system will automatically generate a detailed itinerary

**IMPORTANT: Your job is ONLY to collect information, NOT to create itineraries yourself.**

**When starting a new conversation (no conversation history):**
1. Introduce yourself: "Hello! I'm your travel planning assistant."
2. Explain your capabilities: "I can help you plan trips by understanding your destination, travel dates, budget, interests, and preferences. I'll create a personalized itinerary for you."
3. Ask if they want help: "Would you like me to help you plan a trip today?"

**When user asks non-travel related questions:**
1. Briefly and accurately answer the question
2. Then, naturally connect the topic to travel planning by suggesting a related destination or experience
3. Ask if they would like to plan a trip related to that topic
4. Guide them to provide travel information (departure city, destination, travel dates, budget, interests, number of travelers)

**Examples:**
- If user asks "Who is the President of the United States?", answer briefly, then say: "Speaking of the White House, would you like to plan a trip to Washington D.C. to visit the White House and explore the capital? I can help you create an itinerary!"
- If user asks about a famous landmark, answer briefly, then suggest planning a trip there
- If user asks about a country/city, answer briefly, then ask if they want to plan a trip there

**During travel planning conversation:**
- Ask focused questions to gather REQUIRED information: departure city, destination, travel dates, number of travelers
- Ask follow-up questions about OPTIONAL information: budget, interests, travel type
- Keep your questions SHORT (1-2 questions at a time)
- DO NOT create preliminary itineraries or day-by-day plans yourself
- DO NOT say "Here's a preliminary outline" or "Let me create a plan"
- Instead, ask questions like: "Where will you be departing from?" or "What are your main interests?"

**Keep responses natural, helpful, and focused on COLLECTING INFORMATION ONLY."""
        )
        self.extraction_system_message = SystemMessage(
            content="""From the following conversation, extract the user's travel requirements.

**Important fields to extract:**

1. **origin** (IMPORTANT for flight search):
   - The user's departure location/city
   - Look for patterns:
     - "from [city] to [destination]" → extract [city] as origin
     - "departing from [city]" → extract [city]
     - "leaving from [city]" → extract [city]
     - "I'm in [city]" → extract [city]
   - **CAREFUL**:
     - "to Paris from December 25" → origin: null (date, not city)
     - "from Boston to Austin" → origin: "Boston"
   - Examples:
     - "from San Francisco to Paris" → origin: "San Francisco"
     - "departing LAX" → origin: "LAX"
     - "I'm in New York" → origin: "New York"
     - "trip to Paris from Dec 25" → origin: null (from = date)

2. **destination** (REQUIRED):
   - Where the user wants to go
   - Look for patterns: "to [place]", "visit [place]", "trip to [place]"
   - "to Paris from December 25" → destination: "Paris" (not origin)

3. **start_date**, **end_date**: Travel dates
   - Extract dates AS-IS from user's message (preserve relative expressions like "this weekend", "next Friday")
   - Examples:
     - "this weekend" → start_date: "this weekend", end_date: "this weekend"
     - "June 15-20" → start_date: "June 15", end_date: "June 20"
     - "next Friday" → start_date: "next Friday", end_date: null
   - DON'T try to calculate specific dates here - just extract the text

4. **travelers**: Number and type of travelers
5. **budget**: Budget amount
6. **interests**: User interests
7. **travel_type**: Type of trip

IMPORTANT:
- If user provides "from X to Y" → extract both origin and destination
- If user only provides "to Y" → destination only, origin is None
- For dates: extract the relative expressions AS-IS (e.g., "this weekend", "next Friday") - date normalization happens later
- If a piece of information is not present, leave its value as null
- Your job is only to extract information, not to ask questions"""
        )

    def process_message(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a user message, attempts to extract a complete travel request,
        and decides whether to continue chatting, proceed to planning, or refine existing plan.
        """
        user_message = state.get("user_message", "")
        # Use unified messages field
        history = state.get("messages", [])
        existing_plan = state.get("plan")

        # The conversation for this turn includes the new user message
        current_conversation = history + [HumanMessage(content=user_message)]

        # Check if this is a plan refinement request (user wants to modify existing plan)
        if existing_plan and self._is_refinement_request(user_message):
            # Extract refinement details
            refinement_request = self._extract_refinement_request(user_message)

            ai_response_content = "I'll update your travel plan based on your request."
            updated_history = current_conversation + [AIMessage(content=ai_response_content)]

            return {
                "ai_response": ai_response_content,
                "intent": "refine",
                "refinement_request": refinement_request,
                "messages": updated_history
            }

        # 1. Attempt to extract structured information from the current conversation
        try:
            extraction_prompt = [self.extraction_system_message] + current_conversation
            extracted_data: TravelRequest = self.extraction_llm.invoke(extraction_prompt)
            user_request = extracted_data.dict()

            # 2.1. PRIORITY: Validate start_date is not in the past (check BEFORE other validations)
            start_date = user_request.get("start_date")
            if start_date:
                from datetime import datetime
                from ..utils.constraints_utils import normalize_date

                # First normalize the date to ISO format (e.g., "June 15, 2025" → "2025-06-15")
                normalized_date = normalize_date(start_date, llm=self.llm, field_name="start_date")

                if normalized_date:
                    try:
                        start_dt = datetime.fromisoformat(normalized_date.split('T')[0])
                        today = datetime.now().date()
                        if start_dt.date() < today:
                            # Date is in the past - ask for future date
                            ai_response_content = (
                                f"I notice the travel date you mentioned ({start_date}) is in the past. "
                                f"Could you please provide a future date for your trip?"
                            )
                            updated_history = current_conversation + [AIMessage(content=ai_response_content)]
                            return {
                                "ai_response": ai_response_content,
                                "intent": "chat",
                                "user_request": user_request,
                                "messages": updated_history
                            }
                    except Exception as e:
                        # If date parsing still fails, log and continue
                        print(f"Warning: Failed to parse date '{normalized_date}': {e}")
                        pass

            # 2.2. Validate hard constraints (destination, duration, and origin)
            is_valid, missing_msg = validate_hard_constraints(user_request)

            # 2.5. Check if origin is needed for flight search
            origin = user_request.get("origin")
            destination = user_request.get("destination")

            # Determine if this is a trip that needs flights
            if is_valid and self._is_flight_needed(user_message, origin, destination) and not origin:
                # User needs flights but didn't provide origin
                ai_response_content = (
                    f"Great! I'll help you plan your trip to {destination}. "
                    f"To find the best flights, where will you be departing from?"
                )
                updated_history = current_conversation + [AIMessage(content=ai_response_content)]

                return {
                    "ai_response": ai_response_content,
                    "intent": "chat",  # Keep in chat mode to collect origin
                    "user_request": user_request,  # Save extracted data
                    "messages": updated_history
                }

            if is_valid:
                # We have minimum required info, build constraints and proceed to planning
                # Pass self.llm to enable LLM-based parsing
                constraints = get_default_constraints(user_request, llm=self.llm)

                # Build a confirmation message
                destination = user_request.get("destination")
                start_date = user_request.get("start_date")
                end_date = user_request.get("end_date")

                # Calculate duration from dates
                duration_msg = ""
                if start_date and end_date:
                    try:
                        from datetime import datetime
                        start = datetime.fromisoformat(start_date.split('T')[0])
                        end = datetime.fromisoformat(end_date.split('T')[0])
                        days = (end - start).days + 1
                        duration_msg = f"{days}-day "
                    except:
                        duration_msg = ""

                travel_type_msg = f" for your {constraints.get('travel_type')}" if constraints.get('travel_type') else ""

                ai_response_content = f"Great! I'll plan a {duration_msg}trip to {destination}{travel_type_msg}. Let me create a detailed itinerary for you."

                updated_history = current_conversation + [AIMessage(content=ai_response_content)]

                return {
                    "ai_response": ai_response_content,
                    "intent": "plan",
                    "user_request": user_request,
                    "constraints": constraints,
                    "messages": updated_history  # Unified messages field
                }
            else:
                # Missing hard constraints, continue chatting to collect them
                # Use the missing message as guidance, but let LLM generate natural response
                user_request_partial = user_request

        except (ValidationError, AttributeError):
            # Extraction failed, which is expected if info is missing. We'll continue to chat.
            user_request_partial = None

        # 3. If planning criteria are not met, ask a clarifying question.
        # Check if this is the first message (no conversation history)
        is_first_message = len(history) == 0

        # Add a special instruction for first message if needed
        chat_prompt = [self.chat_system_message] + current_conversation
        if is_first_message:
            # Add a reminder for first message
            first_message_reminder = SystemMessage(
                content="This is the first message from the user. Make sure to introduce yourself, explain your capabilities, and ask if they want help planning a trip."
            )
            chat_prompt = [self.chat_system_message, first_message_reminder] + current_conversation

        # Check if streaming is enabled
        stream_callback = state.get("_chat_stream_callback")

        if stream_callback:
            # Use streaming mode
            print(f"🌊 ChatNode: Streaming enabled, starting to stream response...")
            ai_response_content = ""
            chunk_count = 0
            for chunk in self.llm.stream(chat_prompt):
                if chunk.content:
                    ai_response_content += chunk.content
                    stream_callback(chunk.content)
                    chunk_count += 1
            print(f"🌊 ChatNode: Streamed {chunk_count} chunks, total length: {len(ai_response_content)}")
        else:
            # Non-streaming mode (backward compatible)
            print(f"⚠️  ChatNode: Streaming NOT enabled, using regular invoke")
            response = self.llm.invoke(chat_prompt)
            ai_response_content = response.content

        updated_history = current_conversation + [AIMessage(content=ai_response_content)]

        return {
            "ai_response": ai_response_content,
            "intent": "chat",
            "messages": updated_history,  # Unified messages field
            "user_request": user_request_partial  # Pass partially extracted data if available
        }

    def _is_refinement_request(self, message: str) -> bool:
        """
        Detect if the user message is requesting a modification to an existing plan.

        Args:
            message: User's message text

        Returns:
            True if this appears to be a refinement request, False otherwise
        """
        message_lower = message.lower()

        # Keywords that indicate modification intent
        refinement_keywords = [
            "change", "modify", "update", "adjust", "edit", "replace",
            "instead", "rather", "different", "改", "修改", "调整", "换成",
            "day ", "第", "天", "morning", "afternoon", "evening",
            "remove", "add", "delete", "swap"
        ]

        # Check if message contains refinement keywords
        return any(keyword in message_lower for keyword in refinement_keywords)

    def _extract_refinement_request(self, message: str) -> Dict[str, Any]:
        """
        Extract details about what the user wants to modify.

        Args:
            message: User's message text

        Returns:
            Dictionary with refinement details
        """
        return {
            "description": message,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z"
        }

    def _is_flight_needed(self, user_message: str, origin: str | None, destination: str | None) -> bool:
        """
        Determine if this trip needs flight search.

        Heuristic rules:
        1. If user explicitly provided origin → needs flights
        2. If destination is in user's current location → local trip, no flights needed
        3. Default: long-distance trips need flights

        Args:
            user_message: The user's original message
            origin: Extracted origin (may be None)
            destination: Extracted destination

        Returns:
            True if flights are needed, False otherwise
        """
        # If user already provided origin, they expect flight information
        if origin:
            return True

        # Check for local trip patterns
        message_lower = user_message.lower()
        local_trip_patterns = [
            f"in {destination.lower()}" if destination else "",
            f"around {destination.lower()}" if destination else "",
            f"within {destination.lower()}" if destination else "",
        ]

        if any(pattern and pattern in message_lower for pattern in local_trip_patterns):
            return False  # Local trip, no flights needed

        # Default: long-distance trips need flights
        return True

    def clear_history(self):
        """This method is no longer needed as history is managed in the graph state."""
        pass
