"""
Plan Synthesizer Node
Synthesizes all sub-task results into a final, coherent travel plan.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Dict, List
from openai import OpenAI
import os
from datetime import datetime

from ..core.prompt_templates import PLAN_SYNTHESIZER_PROMPT, PLAN_SYNTHESIZER_JSON_PROMPT
from ..utils.maps_utils import add_travel_times_to_plan
from ..utils.unsplash_utils import add_destination_image_to_plan
from ..utils.pinecone_utils import PineconeStore
import re

logger = logging.getLogger(__name__)


class PlanSynthesizer:
    """
    An agent responsible for creating the final travel plan from collected data.
    Can output both text format (backward compatible) and structured JSON format.
    """

    def __init__(self, llm=None, *, model: str = "gpt-4o-mini", temperature: float = 0.5, output_format: str = "both"):
        """
        Initialize the PlanSynthesizer.

        Args:
            llm: Not used (kept for compatibility)
            model: OpenAI model name
            temperature: Temperature for generation
            output_format: "text", "json", or "both" (default: "both")
        """
        del llm  # Not used
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.temperature = temperature
        self.output_format = output_format
        self.text_system_prompt = PLAN_SYNTHESIZER_PROMPT
        self.json_system_prompt = PLAN_SYNTHESIZER_JSON_PROMPT

    def synthesize_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes all completed sub-task results and generates a final plan.

        Args:
            state: The current graph state with all sub-task results.

        Returns:
            A dictionary containing the final travel plan (text and/or JSON).
        """
        completed_tasks_results = state.get("completed_tasks_results", {})
        if not completed_tasks_results:
            return {
                "travel_plan": "No information was gathered to create a plan.",
                "plan": None,
                "status": "completed"
            }

        # Format the collected data for the prompt
        formatted_results = []
        for task, result in completed_tasks_results.items():
            formatted_results.append(f"### Sub-task: {task}\n{json.dumps(result, indent=2, ensure_ascii=False)}\n")

        data_section = "\n---\n".join(formatted_results)

        # Get constraints and user_request from state
        constraints = state.get("constraints", {})
        user_request = state.get("user_request", {})

        # RAG: retrieve similar past plans for few-shot inspiration.
        similar_plans_block = self._build_similar_plans_block(user_request, constraints)

        # Build context for JSON generation
        context = f"""
**User Request:**
{json.dumps(user_request, indent=2, ensure_ascii=False)}

**Constraints:**
{json.dumps(constraints, indent=2, ensure_ascii=False)}
{similar_plans_block}
**Collected Information:**
{data_section}
"""

        result = {}

        # Generate text plan if needed
        if self.output_format in ["text", "both"]:
            text_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.text_system_prompt},
                    {"role": "user", "content": data_section},
                ],
                temperature=self.temperature,
            )
            result["travel_plan"] = text_response.choices[0].message.content or "Failed to generate the final plan."
            
            # Print final text plan
            print("=" * 100)
            print("📋📋📋 FINAL AI OUTPUT (TEXT PLAN) 📋📋📋")
            print("=" * 100)
            print(result["travel_plan"])
            print("=" * 100)
            logger.info("=" * 100)
            logger.info("📋📋📋 FINAL AI OUTPUT (TEXT PLAN) 📋📋📋")
            logger.info("=" * 100)
            logger.info(result["travel_plan"])
            logger.info("=" * 100)

        # Generate JSON plan with streaming support
        if self.output_format in ["json", "both"]:
            # Check if we should use streaming (passed from state)
            use_streaming = state.get("_streaming_enabled", False)
            stream_callback = state.get("_stream_callback", None)

            if use_streaming and stream_callback:
                # Use streaming mode
                json_content = self._generate_json_streaming(context, stream_callback)
            else:
                # Use non-streaming mode (backward compatible)
                json_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.json_system_prompt},
                        {"role": "user", "content": context},
                    ],
                    temperature=0.3,
                )
                json_content = json_response.choices[0].message.content or "{}"

            # Clean up common JSON formatting issues
            json_content = json_content.strip()
            if json_content.startswith("```json"):
                json_content = json_content[7:]
            if json_content.startswith("```"):
                json_content = json_content[3:]
            if json_content.endswith("```"):
                json_content = json_content[:-3]
            json_content = json_content.strip()

            # Parse JSON
            try:
                plan_json = json.loads(json_content)
                # Add metadata if missing or incorrect
                # Always set generated_at to current time (fix any incorrect dates from LLM)
                plan_json["generated_at"] = datetime.utcnow().isoformat() + "Z"
                if "version" not in plan_json:
                    plan_json["version"] = 1

                # Add travel times to the plan
                logger.info("🗺️ Calculating travel times between locations...")
                plan_json = add_travel_times_to_plan(plan_json)

                # Add destination image URL
                logger.info("🖼️  Fetching destination image...")
                plan_json = add_destination_image_to_plan(plan_json)

                # Extract flight information from completed tasks
                logger.info("✈️ Extracting flight information from tool results...")
                plan_json = self._extract_flight_info_from_tasks(plan_json, state)

                result["plan"] = plan_json

                # Print final JSON plan
                print("=" * 100)
                print("📋📋📋 FINAL AI OUTPUT (JSON PLAN) 📋📋📋")
                print("=" * 100)
                print(json.dumps(plan_json, indent=2, ensure_ascii=False))
                print("=" * 100)
                logger.info("=" * 100)
                logger.info("📋📋📋 FINAL AI OUTPUT (JSON PLAN) 📋📋📋")
                logger.info("=" * 100)
                logger.info(json.dumps(plan_json, indent=2, ensure_ascii=False))
                logger.info("=" * 100)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON plan: {e}")
                print(f"Raw content: {json_content}")
                logger.warning(f"⚠️ Failed to parse JSON plan: {e}")
                logger.warning(f"Raw content: {json_content}")
                result["plan"] = {
                    "error": "Failed to parse JSON",
                    "raw_content": json_content
                }

        result["status"] = "completed"
        return result

    def _build_similar_plans_block(self, user_request: Dict[str, Any], constraints: Dict[str, Any]) -> str:
        """
        Query Pinecone for similar past plans and format them as a context block.

        Returns an empty string if Pinecone is disabled, no hits, or any failure occurs.
        """
        try:
            destination = (user_request or {}).get("destination") or ""
            if not destination:
                return ""

            interests = constraints.get("interests") if constraints else None
            travel_type = constraints.get("travel_type") if constraints else None

            store = PineconeStore.instance()
            if not store.enabled:
                return ""

            hits = store.query_similar_plans(
                destination=destination,
                interests=interests,
                travel_type=travel_type,
                top_k=3,
            )
            if not hits:
                return ""

            blocks: List[str] = ["\n**Similar Past Plans (reference only):**"]
            for idx, hit in enumerate(hits, start=1):
                md = hit.get("metadata") or {}
                plan_json_str = md.get("plan_json")
                summary_text = md.get("text") or ""
                score = hit.get("score")

                header_parts = [f"Past Plan #{idx}"]
                if score is not None:
                    try:
                        header_parts.append(f"similarity={float(score):.2f}")
                    except (TypeError, ValueError):
                        pass
                if md.get("destination"):
                    header_parts.append(f"destination={md.get('destination')}")
                if md.get("travel_type"):
                    header_parts.append(f"type={md.get('travel_type')}")
                if md.get("duration_days"):
                    header_parts.append(f"days={md.get('duration_days')}")

                blocks.append(f"\n--- {' | '.join(header_parts)} ---")

                # Prefer the structured plan if available.
                if plan_json_str:
                    try:
                        past_plan = json.loads(plan_json_str)
                        for day in past_plan.get("days", []) or []:
                            blocks.append(
                                f"Day {day.get('day')}: {day.get('summary', '')}"
                            )
                            for item in (day.get("items") or [])[:6]:
                                blocks.append(
                                    f"  - [{item.get('time', '')}] "
                                    f"{item.get('place', '')}: {item.get('reason', '')}"
                                )
                        continue
                    except (json.JSONDecodeError, TypeError):
                        pass

                if summary_text:
                    blocks.append(summary_text[:800])

            block = "\n".join(blocks)
            logger.info(
                f"📚 PlanSynthesizer RAG: retrieved {len(hits)} similar plan(s) for '{destination}'"
            )
            return block + "\n"
        except Exception as e:
            logger.warning(f"_build_similar_plans_block failed: {e}")
            return ""

    def _generate_json_streaming(self, context: str, stream_callback) -> str:
        """
        Generate JSON plan with streaming, calling stream_callback for each chunk.

        Args:
            context: The context to generate from
            stream_callback: Function to call with each text chunk

        Returns:
            The complete generated JSON string
        """
        json_content = ""

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.json_system_prompt},
                {"role": "user", "content": context},
            ],
            temperature=0.3,
            stream=True,  # Enable streaming
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                text_chunk = chunk.choices[0].delta.content
                json_content += text_chunk
                # Call the callback with the chunk
                stream_callback(text_chunk)

        return json_content

    def _extract_flight_info_from_tasks(self, plan_json: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract flight information from completed task results and add to plan.

        Args:
            plan_json: The generated plan JSON
            state: The graph state containing completed_tasks_results

        Returns:
            Updated plan with flight_options and flight_total_cost
        """
        try:
            completed_results = state.get("completed_tasks_results", {})

            # Look for flight search results in completed tasks
            flight_result = None
            for task_name, result in completed_results.items():
                if "flight" in task_name.lower() or "搜索航班" in task_name or "search flights" in task_name.lower():
                    flight_result = result
                    logger.info(f"✓ Found flight search result in task: {task_name}")
                    break

            if not flight_result:
                logger.info("⚠️ No flight information found in completed tasks")
                return plan_json

            # Parse flight information using the AmadeusFlightClient's search method
            # The flight tool returns formatted text, we need to extract structured data
            # For now, we'll note that flights were searched but full integration needs
            # the tool to store structured data in state

            # Try to import and use the flight client directly if we have the required info
            try:
                from ..utils.flight_utils import AmadeusFlightClient

                constraints = state.get("constraints", {})
                origin = constraints.get("origin")
                destination = plan_json.get("destination")
                start_date = constraints.get("start_date")
                end_date = constraints.get("end_date")
                travelers = constraints.get("travelers", 1)

                if origin and destination and start_date:
                    logger.info(f"🔍 Re-fetching flight data: {origin} → {destination}")
                    client = AmadeusFlightClient()
                    flight_options = client.search_flights(
                        origin=origin,
                        destination=destination,
                        departure_date=start_date,
                        return_date=end_date,
                        adults=travelers
                    )

                    if flight_options:
                        # Calculate total cost (cheapest combination)
                        outbound_flights = [f for f in flight_options if f["type"] == "outbound"]
                        return_flights = [f for f in flight_options if f["type"] == "return"]

                        total_cost = 0
                        cheapest_outbound = None
                        cheapest_return = None

                        if outbound_flights:
                            cheapest_outbound = min(outbound_flights, key=lambda x: x["price"])
                            total_cost += cheapest_outbound["price"]
                        if return_flights:
                            cheapest_return = min(return_flights, key=lambda x: x["price"])
                            total_cost += cheapest_return["price"]

                        # Format flights data for FlightCard component (matching frontendexample.jsx structure)
                        flights_data = {}

                        if cheapest_outbound:
                            # Format time from ISO to "HH:MM AM/PM"
                            dep_time = self._format_time_12h(cheapest_outbound["departure_time"])
                            arr_time = self._format_time_12h(cheapest_outbound["arrival_time"])
                            dep_date = cheapest_outbound["departure_time"][:10]  # YYYY-MM-DD

                            flights_data["arrival"] = {
                                "origin": f"{origin} ({cheapest_outbound['departure_airport']})",
                                "destination": f"{destination} ({cheapest_outbound['arrival_airport']})",
                                "airline": f"{cheapest_outbound['airline']} ({cheapest_outbound['flight_number']})",
                                "departure_time": dep_time,
                                "arrival_time": arr_time,
                                "date": dep_date,
                                "cost": round(cheapest_outbound["price"]),
                                "currency": cheapest_outbound["currency"],
                                "notes": f"Flight duration: {cheapest_outbound['duration']}. {'Direct flight' if cheapest_outbound['stops'] == 0 else f'{cheapest_outbound['stops']} stop(s)'}"
                            }

                        if cheapest_return:
                            dep_time = self._format_time_12h(cheapest_return["departure_time"])
                            arr_time = self._format_time_12h(cheapest_return["arrival_time"])
                            dep_date = cheapest_return["departure_time"][:10]

                            flights_data["departure"] = {
                                "origin": f"{destination} ({cheapest_return['departure_airport']})",
                                "destination": f"{origin} ({cheapest_return['arrival_airport']})",
                                "airline": f"{cheapest_return['airline']} ({cheapest_return['flight_number']})",
                                "departure_time": dep_time,
                                "arrival_time": arr_time,
                                "date": dep_date,
                                "cost": round(cheapest_return["price"]),
                                "currency": cheapest_return["currency"],
                                "notes": f"Flight duration: {cheapest_return['duration']}. {'Direct flight' if cheapest_return['stops'] == 0 else f'{cheapest_return['stops']} stop(s)'}"
                            }

                        # Add to plan (both formats for flexibility)
                        plan_json["flight_options"] = flight_options  # Full list for future use
                        plan_json["flights"] = flights_data  # FlightCard format
                        plan_json["flight_total_cost"] = round(total_cost, 2)

                        logger.info(f"✓ Added flight data to plan (arrival + departure)")
                        logger.info(f"✓ Total flight cost: ${total_cost:.2f}")
                    else:
                        logger.warning("⚠️ Flight search returned no results")

            except Exception as e:
                logger.warning(f"⚠️ Could not fetch flight data: {e}")

            return plan_json

        except Exception as e:
            logger.error(f"❌ Error extracting flight info: {e}")
            return plan_json  # Return original plan if extraction fails

    def _format_time_12h(self, iso_time: str) -> str:
        """
        Convert ISO 8601 time to 12-hour format.

        Args:
            iso_time: ISO format time string (e.g., "2025-04-01T08:00:00")

        Returns:
            12-hour formatted time (e.g., "08:00 AM")
        """
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
            return dt.strftime("%I:%M %p")
        except Exception as e:
            logger.warning(f"⚠️ Could not format time {iso_time}: {e}")
            return iso_time[:5]  # Return HH:MM as fallback
