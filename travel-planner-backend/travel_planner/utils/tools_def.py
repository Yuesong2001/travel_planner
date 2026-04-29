"""
Tool Function Definition Module
Uses real LLM calls to generate travel planning content.
Based on the implementation in TravelPlanner.ipynb.
"""

import textwrap
import os
import requests
import logging
import requests
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Set up logger first
logger = logging.getLogger(__name__)

# Load environment variables
# Try to find .env file in multiple possible locations
env_paths = [
    os.path.join(os.path.dirname(__file__), "..", ".env"),  # From travel_planner/utils/ -> travel_planner/.env
    os.path.join(os.path.dirname(__file__), "..", "..", ".env"),  # From travel_planner/utils/ -> backend/.env
    os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),  # From travel_planner/utils/ -> final/.env
    ".env",  # Current directory
    os.path.expanduser("~/.env"),  # Home directory
]

env_loaded = False
logger.info("🔍 Searching for .env file in the following locations:")
for env_path in env_paths:
    abs_path = os.path.abspath(env_path)
    logger.info(f"   Checking: {abs_path}")
    if os.path.exists(abs_path):
        load_dotenv(abs_path)
        env_loaded = True
        logger.info(f"✅ Loaded .env from: {abs_path}")
        break
    else:
        logger.debug(f"   ❌ Not found: {abs_path}")

if not env_loaded:
    # Fallback: try default load_dotenv() behavior
    logger.warning("⚠️ No .env file found in expected locations, trying default load_dotenv()...")
    load_dotenv()
    # Check again after default load
    if os.getenv("GOOGLE_MAPS_API_KEY"):
        logger.info("✅ Environment variables loaded via default load_dotenv()")
    else:
        logger.warning("⚠️ Default load_dotenv() also failed to load GOOGLE_MAPS_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Debug: Log if API keys are found
if GOOGLE_MAPS_API_KEY:
    logger.info(f"✅ GOOGLE_MAPS_API_KEY found (length: {len(GOOGLE_MAPS_API_KEY)})")
else:
    logger.warning("⚠️ GOOGLE_MAPS_API_KEY not found in environment variables")

if OPENWEATHER_API_KEY:
    logger.info(f"✅ OPENWEATHER_API_KEY found (length: {len(OPENWEATHER_API_KEY)})")
else:
    logger.warning("⚠️ OPENWEATHER_API_KEY not found in environment variables")

# Wikipedia API headers (required to avoid 403 Forbidden errors)
WIKIPEDIA_HEADERS = {
    'User-Agent': 'TravelPlanner/1.0 (Travel Planning Application; contact@travelplanner.com)'
}


# ============================================================================
# Pinecone RAG helpers
# All helpers are best-effort: if Pinecone is disabled or fails, they return
# empty strings / no-op so the rest of the tool keeps working unchanged.
# ============================================================================

def _rag_destination_context(destination: str, top_k: int = 3) -> str:
    """Pull cached destination knowledge and format it as a context block."""
    try:
        from .pinecone_utils import PineconeStore
        store = PineconeStore.instance()
        if not store.enabled:
            return ""
        hits = store.query_knowledge(
            f"Travel guide for {destination}",
            filter={"type": "destination"},
            top_k=top_k,
        )
        if not hits:
            return ""
        lines = ["**Knowledge base context (from past research):**"]
        for hit in hits:
            text = (hit.get("metadata") or {}).get("text", "")
            if text:
                lines.append(f"- {text[:500]}")
        return "\n".join(lines)
    except Exception as e:
        logger.debug(f"_rag_destination_context failed: {e}")
        return ""


def _rag_upsert_destination(destination: str, content: str, source: str = "wikipedia+llm") -> None:
    """Index a destination guide for future RAG calls."""
    if not destination or not content:
        return
    try:
        from .pinecone_utils import PineconeStore, make_destination_id
        store = PineconeStore.instance()
        if not store.enabled:
            return
        store.upsert_knowledge(
            [
                {
                    "id": make_destination_id(destination),
                    "text": content,
                    "metadata": {
                        "type": "destination",
                        "destination": destination,
                        "source": source,
                    },
                }
            ]
        )
    except Exception as e:
        logger.debug(f"_rag_upsert_destination failed: {e}")


def _rag_places_context(destination: str, kind: str, interests: str = "general", top_k: int = 5) -> str:
    """Pull cached attractions/restaurants for a destination."""
    try:
        from .pinecone_utils import PineconeStore
        store = PineconeStore.instance()
        if not store.enabled:
            return ""
        query = f"{kind} in {destination} matching {interests}"
        hits = store.query_knowledge(
            query,
            filter={"type": kind, "destination": destination},
            top_k=top_k,
        )
        if not hits:
            return ""
        label = "Attractions" if kind == "attraction" else "Restaurants"
        lines = [f"\n**Additional {label.lower()} from knowledge base:**"]
        for hit in hits:
            md = hit.get("metadata") or {}
            name = md.get("name") or ""
            rating = md.get("rating")
            address = md.get("address") or ""
            text = md.get("text", "")
            entry = f"- {name}" if name else f"- {text[:200]}"
            if rating:
                entry += f" (rating: {rating})"
            if address:
                entry += f" — {address}"
            lines.append(entry)
        return "\n".join(lines)
    except Exception as e:
        logger.debug(f"_rag_places_context failed: {e}")
        return ""


def _rag_upsert_places(
    destination: str,
    places: list,
    kind: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Index a batch of attractions or restaurants from Google Maps results.

    Args:
        destination: target city/country
        places: list of Google Maps Place dicts (raw API response items)
        kind: 'attraction' or 'restaurant'
        extra_metadata: optional dict merged into every place's metadata
    """
    if not destination or not places:
        return
    try:
        from .pinecone_utils import PineconeStore, make_place_id
        store = PineconeStore.instance()
        if not store.enabled:
            return

        items = []
        for place in places:
            name = place.get("name") or ""
            if not name:
                continue
            rating = place.get("rating")
            address = place.get("formatted_address", "")
            place_id = place.get("place_id")
            types = place.get("types") or []
            price_level = place.get("price_level")

            # Build searchable text
            text_parts = [f"{name} in {destination}"]
            if address:
                text_parts.append(address)
            if types:
                pretty_types = ", ".join(t.replace("_", " ") for t in types[:5])
                text_parts.append(f"Types: {pretty_types}")
            if rating:
                text_parts.append(f"Rating: {rating}")
            text = " | ".join(text_parts)

            metadata: Dict[str, Any] = {
                "type": kind,
                "destination": destination,
                "name": name,
                "source": "google_maps",
            }
            if address:
                metadata["address"] = address
            if rating is not None:
                metadata["rating"] = float(rating)
            if place_id:
                metadata["place_id"] = place_id
            if price_level is not None:
                metadata["price_level"] = int(price_level)
            if types:
                metadata["place_types"] = [str(t) for t in types[:10]]
            if extra_metadata:
                metadata.update(extra_metadata)

            items.append(
                {
                    "id": make_place_id(kind, place_id, f"{name}|{destination}"),
                    "text": text,
                    "metadata": metadata,
                }
            )

        if items:
            store.upsert_knowledge(items)
    except Exception as e:
        logger.debug(f"_rag_upsert_places failed: {e}")


def research_destination(destination: str) -> str:
    """Researches basic information about a destination using Wikipedia API.
    
    Args:
        destination: The name of the destination.
    
    Returns:
        Detailed information about the destination.
    """
    logger.info("=" * 100)
    logger.info("🔧🔧🔧 TOOL CALL: research_destination 🔧🔧🔧")
    logger.info("=" * 100)
    logger.info(f"📥 INPUT: destination = '{destination}'")
    logger.info("─" * 100)

    # RAG: pull cached destination knowledge to enrich the prompt.
    rag_context = _rag_destination_context(destination)
    if rag_context:
        logger.info(f"📚 RAG: retrieved destination context ({len(rag_context)} chars)")

    # Try Wikipedia API first
    try:
        logger.info(f"📚📚📚 WIKIPEDIA API CALL: research_destination 📚📚📚")
        logger.info(f"📚 Searching Wikipedia for: '{destination}'")
        
        # Use Wikipedia REST API to get page summary
        wiki_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + destination.replace(" ", "_")
        logger.info(f"📚 Wikipedia API URL: {wiki_url}")
        wiki_response = requests.get(wiki_url, headers=WIKIPEDIA_HEADERS, timeout=10)
        wiki_response.raise_for_status()
        wiki_data = wiki_response.json()
        
        # Log Wikipedia API response
        logger.info("=" * 100)
        logger.info("📚📚📚 WIKIPEDIA API RESPONSE 📚📚📚")
        logger.info("=" * 100)
        logger.info(f"📚 Response Status: {wiki_response.status_code}")
        logger.info(f"📚 Page Type: {wiki_data.get('type', 'unknown')}")
        logger.info(f"📚 Title: {wiki_data.get('title', 'N/A')}")
        logger.info(f"📚 Description: {wiki_data.get('description', 'N/A')}")
        logger.info(f"📚 Extract Length: {len(wiki_data.get('extract', ''))} characters")
        logger.info("─" * 100)
        logger.info(f"📚 Extract Preview (first 200 chars):\n{wiki_data.get('extract', '')[:200]}...")
        logger.info("=" * 100)
        
        # Check if page exists
        if wiki_data.get("type") == "disambiguation":
            logger.warning(f"⚠️ Wikipedia returned disambiguation page for '{destination}'. Trying LLM fallback.")
            return _research_destination_llm_fallback(destination)
        
        if wiki_data.get("type") == "standard":
            extract = wiki_data.get("extract", "")
            title = wiki_data.get("title", destination)
            description = wiki_data.get("description", "")
            
            logger.info(f"📚 Wikipedia page found: '{title}'")
            logger.info(f"📚 Description: {description}")
            logger.info(f"📚 Extract length: {len(extract)} characters")
            
            if not extract or len(extract) < 50:
                logger.warning("⚠️ Wikipedia extract too short. Trying LLM fallback.")
                return _research_destination_llm_fallback(destination)
            
            # Use LLM to format Wikipedia data into travel guide
            research_prompt = textwrap.dedent(f"""
                Based on the following Wikipedia information about {destination}, create a concise travel guide covering:
                - Best time to visit and typical weather
                - Top 5-7 must-see attractions
                - Local culture and customs travelers should know
                - Transportation options within the city
                - Typical cuisine and dining culture
                
                **Wikipedia Information:**
                {extract}
                
                {rag_context}

                Use the Wikipedia data as the primary source, but format it as a helpful travel guide.
                Keep it under 300 words, factual and helpful.
            """).strip()
            
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                temperature=0.7,
                max_tokens=400,
                messages=[
                    {'role': 'system', 'content': 'You are a knowledgeable travel researcher. Use the provided Wikipedia data to create a comprehensive travel guide.'},
                    {'role': 'user', 'content': research_prompt}
                ]
            )
            result = response.choices[0].message.content.strip()
            logger.info(f"📤 OUTPUT (Wikipedia + LLM):\n{result}")
            logger.info("=" * 100 + "\n")
            _rag_upsert_destination(destination, result, source="wikipedia+llm")
            return result
        else:
            logger.warning(f"⚠️ Wikipedia returned unexpected page type: {wiki_data.get('type')}. Trying LLM fallback.")
            return _research_destination_llm_fallback(destination)
            
    except requests.RequestException as e:
        error_msg = f"Error accessing Wikipedia API: {str(e)}. Falling back to LLM."
        logger.warning(f"⚠️ WARNING: {error_msg}")
        logger.info("─" * 100)
        return _research_destination_llm_fallback(destination, rag_context)
    except Exception as e:
        error_msg = f"Error researching destination: {str(e)}"
        logger.error(f"❌ ERROR: {error_msg}")
        logger.info("─" * 100)
        return _research_destination_llm_fallback(destination, rag_context)


def _research_destination_llm_fallback(destination: str, rag_context: str = "") -> str:
    """Fallback to pure LLM if Wikipedia API fails."""
    research_prompt = textwrap.dedent(f"""
        Provide a concise travel guide for {destination} covering:
        - Best time to visit and typical weather
        - Top 5-7 must-see attractions
        - Local culture and customs travelers should know
        - Transportation options within the city
        - Typical cuisine and dining culture
        
        {rag_context}

        Keep it under 300 words, factual and helpful.
    """).strip()
    
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.7,
            max_tokens=400,
            messages=[
                {'role': 'system', 'content': 'You are a knowledgeable travel researcher.'},
                {'role': 'user', 'content': research_prompt}
            ]
        )
        result = response.choices[0].message.content.strip()
        logger.info(f"📤 OUTPUT (LLM Fallback):\n{result}")
        logger.info("=" * 100 + "\n")
        _rag_upsert_destination(destination, result, source="llm_fallback")
        return result
    except Exception as e:
        error_msg = f"Error researching destination: {str(e)}"
        logger.error(f"❌ ERROR: {error_msg}")
        logger.info("=" * 100 + "\n")
        return error_msg


def check_weather(destination: str, month: str, travel_date: Optional[str] = None) -> str:
    """Checks weather for a destination using OpenWeather API.
    Intelligently uses forecast for near-term dates or provides climate info for distant dates.

    Args:
        destination: The name of the destination (e.g., 'Paris', 'Bali, Indonesia').
        month: The month for context (e.g., 'December', 'January').
        travel_date: Optional travel start date in YYYY-MM-DD format. If provided, determines strategy.

    Returns:
        Weather information - forecast for near dates, climate info for distant dates.
    """
    if not OPENWEATHER_API_KEY:
        return "Weather API key not configured. Please add OPENWEATHER_API_KEY to environment variables."

    try:
        from datetime import datetime, timedelta

        # Parse city name (handle "City, Country" format)
        city = destination.split(',')[0].strip()

        # Determine if we should use forecast or climate data
        use_forecast = False
        days_until_travel = None

        if travel_date:
            try:
                travel_dt = datetime.fromisoformat(travel_date.split('T')[0])
                today = datetime.now()
                days_until_travel = (travel_dt - today).days

                # Use forecast if travel is within next 5 days
                if 0 <= days_until_travel <= 5:
                    use_forecast = True
            except:
                pass  # If date parsing fails, fall back to climate data

        # Step 1: Get coordinates using Geocoding API
        geocoding_url = "http://api.openweathermap.org/geo/1.0/direct"
        geocoding_params = {
            "q": city,
            "limit": 1,
            "appid": OPENWEATHER_API_KEY
        }

        geo_response = requests.get(geocoding_url, params=geocoding_params, timeout=5)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if not geo_data:
            return f"Could not find weather data for '{destination}'. Please check the city name."

        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']

        # Step 2: Get current weather (always useful as reference)
        current_weather_url = "https://api.openweathermap.org/data/2.5/weather"
        current_params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }

        current_response = requests.get(current_weather_url, params=current_params, timeout=5)
        current_response.raise_for_status()
        current_data = current_response.json()

        # Extract current weather
        temp = round(current_data['main']['temp'])
        feels_like = round(current_data['main']['feels_like'])
        condition = current_data['weather'][0]['main']
        description = current_data['weather'][0]['description']
        humidity = current_data['main']['humidity']

        # Build response based on travel timeline
        if use_forecast:
            # Travel is within 5 days - provide detailed forecast
            result = f"**Weather Forecast for {destination} (Travel in {days_until_travel} day(s)):**\n\n"
            result += f"**Current Conditions:**\n"
            result += f"- Temperature: {temp}°C (feels like {feels_like}°C)\n"
            result += f"- Condition: {condition} - {description}\n"
            result += f"- Humidity: {humidity}%\n"

            # Get 5-day forecast
            forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
            forecast_params = {
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "cnt": 40
            }

            forecast_response = requests.get(forecast_url, params=forecast_params, timeout=5)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()

            # Process forecast
            daily_temps = {}
            daily_conditions = {}

            for item in forecast_data['list']:
                date = item['dt_txt'].split(' ')[0]
                temp_item = item['main']['temp']
                condition_item = item['weather'][0]['main']

                if date not in daily_temps:
                    daily_temps[date] = []
                    daily_conditions[date] = []

                daily_temps[date].append(temp_item)
                daily_conditions[date].append(condition_item)

            result += f"\n**5-Day Detailed Forecast:**\n"
            for i, (date, temps) in enumerate(list(daily_temps.items())[:5]):
                min_temp = round(min(temps))
                max_temp = round(max(temps))
                conditions = daily_conditions[date]
                most_common = max(set(conditions), key=conditions.count)
                result += f"- {date}: {min_temp}°C - {max_temp}°C, {most_common}\n"

        else:
            # Travel is more than 5 days away - only show current weather
            if days_until_travel is not None:
                result = f"**Current Weather in {destination} (Travel in {days_until_travel} days):**\n\n"
                result += f"- Temperature: {temp}°C (feels like {feels_like}°C)\n"
                result += f"- Condition: {condition} - {description}\n"
                result += f"- Humidity: {humidity}%\n\n"
                result += f"**Note:** Accurate weather forecast is only available within 5 days. "
                result += f"Please check weather again closer to your travel date for the most up-to-date forecast."
            else:
                result = f"**Current Weather in {destination}:**\n"
                result += f"- Temperature: {temp}°C (feels like {feels_like}°C)\n"
                result += f"- Condition: {condition} - {description}\n"
                result += f"- Humidity: {humidity}%"

        return result

    except requests.Timeout:
        return f"Weather API request timed out for {destination}. Please try again."
    except requests.RequestException as e:
        return f"Error fetching weather data: {str(e)}"
    except (KeyError, IndexError) as e:
        return f"Error parsing weather data for {destination}: {str(e)}"
    except Exception as e:
        return f"Unexpected error checking weather: {str(e)}"


def _get_real_price_context(destination: str, budget_level: str) -> str:
    """
    Get real price data from Google Places API to provide context for LLM estimation.

    Args:
        destination: Destination to get prices for
        budget_level: Budget level (budget, moderate, luxury)

    Returns:
        String with real price information or empty string if unavailable
    """
    google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not google_api_key:
        return ""

    try:
        # Search for sample restaurants and hotels in the destination
        places_base_url = "https://maps.googleapis.com/maps/api/place"

        # Get restaurant prices
        restaurant_url = f"{places_base_url}/textsearch/json"
        restaurant_params = {
            "query": f"restaurants in {destination}",
            "key": google_api_key,
        }

        response = requests.get(restaurant_url, params=restaurant_params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK":
                results = data.get("results", [])[:5]  # Get top 5

                # Extract price levels
                price_levels = [r.get("price_level") for r in results if r.get("price_level")]
                if price_levels:
                    avg_price_level = sum(price_levels) / len(price_levels)

                    # Convert price level to actual cost estimates
                    price_map = {
                        1: "Budget-friendly ($10-15 per meal)",
                        2: "Moderate ($20-30 per meal)",
                        3: "Upscale ($40-60 per meal)",
                        4: "Luxury ($80+ per meal)"
                    }

                    price_desc = price_map.get(round(avg_price_level), "Moderate ($20-30 per meal)")

                    context = f"\n**Real Price Data from {destination}:**\n"
                    context += f"- Average restaurant prices: {price_desc}\n"
                    context += f"- Based on actual data from Google Places API\n"

                    logger.info(f"✓ Got real price data for {destination}: Avg price level {avg_price_level:.1f}")
                    return context

    except Exception as e:
        logger.warning(f"Failed to get real price data: {e}")

    return ""


def estimate_costs(destination: str, days: int, budget_level: str, budget_amount: Optional[float] = None, itinerary_info: Optional[str] = None, travelers: Optional[int] = None) -> str:
    """Estimates travel costs using real APIs + LLM fallback.

    Args:
        destination: The destination.
        days: The number of days.
        budget_level: The budget level ('budget', 'moderate', 'luxury').
        budget_amount: Optional actual budget amount in USD (e.g., 1500.0).
        itinerary_info: Optional information about the planned itinerary (activities, accommodations, etc.).
        travelers: Optional number of travelers (default: 1 if not specified).

    Returns:
        A detailed cost estimate with real API data when available.
    """
    logger.info("=" * 100)
    logger.info("🔧🔧🔧 TOOL CALL: estimate_costs (Enhanced with Real APIs) 🔧🔧🔧")
    logger.info("=" * 100)
    logger.info(f"📥 INPUT: destination = '{destination}', days = {days}, budget_level = '{budget_level}', budget_amount = {budget_amount}, travelers = {travelers}, itinerary_info = {bool(itinerary_info)}")
    logger.info("─" * 100)

    # Default to 1 traveler if not specified
    num_travelers = travelers if travelers is not None else 1

    # Try to get real price data from Google Places API
    real_prices_context = _get_real_price_context(destination, budget_level)
    
    # Build prompt based on available information
    if budget_amount and itinerary_info:
        # Use actual budget and itinerary
        cost_prompt = textwrap.dedent(f"""
        Estimate the total cost for a {days}-day trip to {destination} for {num_travelers} traveler{'s' if num_travelers > 1 else ''} based on the following planned itinerary.

        **User's Budget:** ${budget_amount:,.0f}
        **Number of Travelers:** {num_travelers}
        **Number of Days:** {days}
        {real_prices_context}
        **IMPORTANT:** All costs must be calculated for {num_travelers} traveler{'s' if num_travelers > 1 else ''} over {days} days.
        - Accommodation costs should be multiplied by {num_travelers} travelers × {days} nights
        - Food costs should be multiplied by {num_travelers} travelers × {days} days
        - Transportation and activities should account for {num_travelers} traveler{'s' if num_travelers > 1 else ''}

        **Planned Itinerary:**
        {itinerary_info}

        Calculate costs based on the specific activities, accommodations, and restaurants mentioned in the itinerary.
        {'Use the real price data provided above to make more accurate estimates.' if real_prices_context else ''}

        Break down costs into:
        - Accommodation (based on planned stays, for {num_travelers} traveler{'s' if num_travelers > 1 else ''} × {days} nights)
        - Food (based on planned restaurants and meals, for {num_travelers} traveler{'s' if num_travelers > 1 else ''} × {days} days)
        - Local transportation (for {num_travelers} traveler{'s' if num_travelers > 1 else ''})
        - Activities and attractions (based on planned visits, for {num_travelers} traveler{'s' if num_travelers > 1 else ''})
        - Total estimated budget

        **CRITICAL:** The total estimated budget should be close to but not exceed ${budget_amount:,.0f}.
        **CRITICAL:** Remember to multiply all per-person costs by {num_travelers} travelers and all per-day costs by {days} days.
        If the calculated costs are significantly below the budget, suggest additional activities or upgrades to better utilize the budget.

        Provide realistic USD amounts. Keep response under 200 words.
        """).strip()
    elif budget_amount:
        # Use actual budget but no itinerary
        cost_prompt = textwrap.dedent(f"""
        Estimate the total cost for a {days}-day trip to {destination} for {num_travelers} traveler{'s' if num_travelers > 1 else ''}.

        **User's Budget:** ${budget_amount:,.0f}
        **Number of Travelers:** {num_travelers}
        **Number of Days:** {days}
        {real_prices_context}
        **IMPORTANT:** All costs must be calculated for {num_travelers} traveler{'s' if num_travelers > 1 else ''} over {days} days.
        - Accommodation costs should be multiplied by {num_travelers} travelers × {days} nights
        - Food costs should be multiplied by {num_travelers} travelers × {days} days
        - Transportation and activities should account for {num_travelers} traveler{'s' if num_travelers > 1 else ''}
        
        Break down costs into:
        - Accommodation per night (for {num_travelers} traveler{'s' if num_travelers > 1 else ''}) × {days} nights
        - Food per day (for {num_travelers} traveler{'s' if num_travelers > 1 else ''}) × {days} days
        - Local transportation per day (for {num_travelers} traveler{'s' if num_travelers > 1 else ''}) × {days} days
        - Activities and attractions per day (for {num_travelers} traveler{'s' if num_travelers > 1 else ''}) × {days} days
        - Total estimated budget
        
        **CRITICAL:** The total estimated budget should be close to but not exceed ${budget_amount:,.0f}.
        **CRITICAL:** Remember to multiply all per-person costs by {num_travelers} travelers and all per-day costs by {days} days.
        
        Provide realistic USD amounts. Keep response under 150 words.
        """).strip()
    else:
        # Fallback to budget level
        cost_prompt = textwrap.dedent(f"""
        Estimate the total cost for a {days}-day trip to {destination} at a {budget_level} level for {num_travelers} traveler{'s' if num_travelers > 1 else ''}.

        **Number of Travelers:** {num_travelers}
        **Number of Days:** {days}
        {real_prices_context}
        **IMPORTANT:** All costs must be calculated for {num_travelers} traveler{'s' if num_travelers > 1 else ''} over {days} days.
        - Accommodation costs should be multiplied by {num_travelers} travelers × {days} nights
        - Food costs should be multiplied by {num_travelers} travelers × {days} days
        - Transportation and activities should account for {num_travelers} traveler{'s' if num_travelers > 1 else ''}
        
        Break down costs into:
        - Accommodation per night (for {num_travelers} traveler{'s' if num_travelers > 1 else ''}) × {days} nights
        - Food per day (for {num_travelers} traveler{'s' if num_travelers > 1 else ''}) × {days} days
        - Local transportation per day (for {num_travelers} traveler{'s' if num_travelers > 1 else ''}) × {days} days
        - Activities and attractions per day (for {num_travelers} traveler{'s' if num_travelers > 1 else ''}) × {days} days
        - Total estimated budget
        
        **CRITICAL:** Remember to multiply all per-person costs by {num_travelers} travelers and all per-day costs by {days} days.
        
        Provide realistic USD amounts. Keep response under 150 words.
        """).strip()
    
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.6,
            max_tokens=400,  # Increased from 200 to allow complete cost breakdown
            messages=[
                {'role': 'system', 'content': 'You are a travel budget expert.'},
                {'role': 'user', 'content': cost_prompt}
            ]
        )
        result = response.choices[0].message.content.strip()
        logger.info(f"📤 OUTPUT:\n{result}")
        logger.info("=" * 100 + "\n")
        return result
    except Exception as e:
        error_msg = f"Error estimating costs: {str(e)}"
        logger.error(f"❌ ERROR: {error_msg}")
        logger.info("=" * 100 + "\n")
        return error_msg


def _fetch_places_from_google_maps(query: str, destination: str, num_results: int) -> list:
    """Helper function to fetch places from Google Maps API.
    
    Args:
        query: The search query string.
        destination: The destination name (for logging).
        num_results: Maximum number of results to return.
    
    Returns:
        A list of place dictionaries from Google Maps API.
    """
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "key": GOOGLE_MAPS_API_KEY,
        "type": "tourist_attraction|museum|park|zoo|aquarium|amusement_park"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        api_status = data.get("status")
        if api_status == "OK" and data.get("results"):
            return data["results"][:num_results]
        else:
            logger.debug(f"🌐 Query '{query}' returned status: {api_status}")
            return []
    except requests.RequestException as e:
        logger.debug(f"🌐 Error fetching places for query '{query}': {str(e)}")
        return []
    except Exception as e:
        logger.debug(f"🌐 Unexpected error for query '{query}': {str(e)}")
        return []


def find_attractions(destination: str, days: int, interests: str = 'general') -> str:
    """Recommends attractions based on interests using Google Maps Places API.
    First fetches general recommendations, then interest-specific ones, and merges them.
    
    Args:
        destination: The destination.
        days: The number of travel days.
        interests: Traveler interests (e.g., 'history', 'food', 'nature').
    
    Returns:
        A list of recommended attractions with real data from Google Maps.
    """
    logger.info("=" * 100)
    logger.info("🔧🔧🔧 TOOL CALL: find_attractions 🔧🔧🔧")
    logger.info("=" * 100)
    logger.info(f"📥 INPUT: destination = '{destination}', days = {days}, interests = '{interests}'")
    logger.info("─" * 100)
    
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("⚠️ WARNING: GOOGLE_MAPS_API_KEY not configured. Using LLM fallback.")
        logger.info("─" * 100)
        result = _find_attractions_llm_fallback(destination, days, interests)
        logger.info(f"📤 OUTPUT (LLM Fallback):\n{result}")
        logger.info("=" * 100 + "\n")
        return result
    
    try:
        num_results = min(days * 2, 10)
        all_places = {}  # Use dict with place_id as key to avoid duplicates
        
        # Step 1: Always get general recommendations first
        logger.info("🌐🌐🌐 GOOGLE MAPS API CALL: find_attractions 🌐🌐🌐")
        logger.info("🌐 Step 1: Fetching general recommendations...")
        general_query = f"attractions in {destination}"
        general_results = _fetch_places_from_google_maps(general_query, destination, num_results)
        
        for place in general_results:
            place_id = place.get("place_id")
            if place_id:
                all_places[place_id] = place
        
        logger.info(f"🌐 Found {len(all_places)} general attractions")
        
        # Step 2: If interests is not 'general', also fetch interest-specific recommendations
        if interests and interests.lower() != 'general':
            logger.info(f"🌐 Step 2: Fetching '{interests}' specific recommendations...")
            interest_query = f"{interests} attractions in {destination}"
            interest_results = _fetch_places_from_google_maps(interest_query, destination, num_results)
            
            for place in interest_results:
                place_id = place.get("place_id")
                if place_id:
                    # If duplicate, keep the one with higher rating (or the interest-specific one)
                    if place_id in all_places:
                        existing_rating = all_places[place_id].get("rating", 0) or 0
                        new_rating = place.get("rating", 0) or 0
                        if new_rating > existing_rating:
                            all_places[place_id] = place
                    else:
                        all_places[place_id] = place
            
            logger.info(f"🌐 Found {len(interest_results)} interest-specific attractions")
        
        logger.info(f"🌐 Total unique attractions: {len(all_places)}")
        
        # Convert dict back to list and limit to num_results
        # Sort by rating (descending) to prioritize higher-rated places
        results = list(all_places.values())
        results.sort(key=lambda x: x.get("rating", 0) or 0, reverse=True)
        results = results[:num_results]
        
        if not results:
            logger.warning("⚠️ No attractions found. Falling back to LLM...")
            result = _find_attractions_llm_fallback(destination, days, interests)
            logger.info(f"📤 OUTPUT (LLM Fallback):\n{result}")
            logger.info("=" * 100 + "\n")
            return result
        
        # Format results
        output_lines = [f"Found {len(results)} attractions in {destination}"]
        if interests and interests.lower() != 'general':
            output_lines[0] += f" (including general recommendations and '{interests}' specific attractions)"
        output_lines[0] += ":\n"
        
        for i, place in enumerate(results, 1):
            name = place.get("name", "Unknown")
            rating = place.get("rating", "N/A")
            address = place.get("formatted_address", "Address not available")
            types = [t.replace("_", " ").title() for t in place.get("types", []) if t not in ["point_of_interest", "establishment"]]
            place_types = ", ".join(types[:3]) if types else "Attraction"
            
            # Try to get description from Google Maps Place Details reviews
            description = ""
            place_id = place.get("place_id", None)
            if place_id and GOOGLE_MAPS_API_KEY:
                try:
                    # Get Place Details to fetch reviews
                    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                    details_params = {
                        "place_id": place_id,
                        "key": GOOGLE_MAPS_API_KEY,
                        "fields": "reviews,rating"  # Only request needed fields to save cost
                    }
                    
                    logger.info(f"🌐 Fetching Place Details for '{name}' (place_id: {place_id[:20]}...)")
                    details_response = requests.get(details_url, params=details_params, timeout=5)
                    
                    if details_response.status_code == 200:
                        details_data = details_response.json()
                        if details_data.get("status") == "OK":
                            result_data = details_data.get("result", {})
                            reviews = result_data.get("reviews", [])
                            
                            if reviews:
                                # Filter and sort reviews by rating (highest first)
                                # Only use reviews with rating >= 4
                                high_rating_reviews = [r for r in reviews if r.get("rating", 0) >= 4]
                                
                                if high_rating_reviews:
                                    # Sort by rating (descending)
                                    sorted_reviews = sorted(high_rating_reviews, key=lambda x: x.get("rating", 0), reverse=True)
                                    top_review = sorted_reviews[0]
                                    review_text = top_review.get("text", "")
                                    
                                    if review_text and len(review_text) > 20:
                                        # Take first 150 characters as description
                                        description = review_text[:150] + "..." if len(review_text) > 150 else review_text
                                        review_rating = top_review.get("rating", "N/A")
                                        logger.info(f"🌐 Found high-rating review (rating: {review_rating}) for '{name}' ({len(description)} chars)")
                                else:
                                    logger.debug(f"🌐 No high-rating reviews (>=4) found for '{name}'")
                            else:
                                logger.debug(f"🌐 No reviews available for '{name}'")
                        else:
                            logger.debug(f"🌐 Place Details API returned status: {details_data.get('status')} for '{name}'")
                except requests.RequestException as e:
                    # Silently fail - reviews are optional
                    logger.debug(f"Could not fetch Place Details for '{name}': {str(e)}")
                except Exception as e:
                    # Log but don't fail
                    logger.debug(f"Error processing reviews for '{name}': {str(e)}")
            
            output_lines.append(f"{i}. {name}")
            output_lines.append(f"   Type: {place_types}")
            output_lines.append(f"   Rating: {rating}/5.0" if isinstance(rating, (int, float)) else f"   Rating: {rating}")
            output_lines.append(f"   Address: {address}")
            if description:
                output_lines.append(f"   Description: {description}")
            output_lines.append("")
        
        # Persist Google Maps places to Pinecone for future RAG calls.
        _rag_upsert_places(destination, results, kind="attraction", extra_metadata={"interests": interests})

        # Append cached/related attractions retrieved from the knowledge base.
        rag_block = _rag_places_context(destination, kind="attraction", interests=interests)

        result = "\n".join(output_lines).strip()
        if rag_block:
            result = result + "\n" + rag_block
        logger.info(f"📤 OUTPUT:\n{result}")
        logger.info("=" * 100 + "\n")
        return result
        
    except requests.RequestException as e:
        error_msg = f"Error accessing Google Maps API: {str(e)}. Falling back to LLM."
        logger.warning(f"⚠️ WARNING: {error_msg}")
        logger.info("─" * 100)
        result = _find_attractions_llm_fallback(destination, days, interests)
        logger.info(f"📤 OUTPUT (LLM Fallback):\n{result}")
        logger.info("=" * 100 + "\n")
        return result
    except Exception as e:
        error_msg = f"Error finding attractions: {str(e)}"
        logger.error(f"❌ ERROR: {error_msg}")
        logger.info("=" * 100 + "\n")
        return error_msg


def _find_attractions_llm_fallback(destination: str, days: int, interests: str) -> str:
    """Fallback to LLM if Google Maps API fails."""
    attractions_prompt = textwrap.dedent(f"""
        Recommend {min(days * 2, 10)} attractions and activities in {destination} for a {days}-day trip.
        Traveler interests: {interests}
        
        For each recommendation include:
        - Name and brief description
        - Estimated time needed
        - Approximate cost
        
        Prioritize variety and feasibility. Keep under 300 words.
    """).strip()
    
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.7,
            max_tokens=400,
            messages=[
                {'role': 'system', 'content': 'You are a local tour expert.'},
                {'role': 'user', 'content': attractions_prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error finding attractions: {str(e)}"


def create_day_by_day_plan(
    destination: str,
    days: int,
    month: str,
    budget_level: str,
    travelers: int,
    budget_limit: Optional[float] = None,
    flight_info: Optional[str] = None  # NEW: Flight constraints
) -> str:
    """Generates a detailed day-by-day itinerary - generated by an LLM.

    Args:
        destination: The destination.
        days: The number of days.
        month: The month of travel.
        budget_level: The budget level.
        travelers: The number of travelers.
        budget_limit: Optional total budget limit in USD. If provided, the itinerary MUST NOT exceed this budget.
        flight_info: Optional flight details including arrival/departure times.
                     Format: "Arrival: Day 1 at 4:00 PM\nDeparture: Day 7 at 11:30 PM"

    Returns:
        A complete day-by-day itinerary that respects flight timing constraints.
    """
    logger.info("=" * 100)
    logger.info("🔧🔧🔧 TOOL CALL: create_day_by_day_plan 🔧🔧🔧")
    logger.info("=" * 100)
    logger.info(f"📥 INPUT: destination = '{destination}', days = {days}, month = '{month}', budget_level = '{budget_level}', travelers = {travelers}")
    if flight_info:
        logger.info(f"✈️ FLIGHT INFO: {flight_info}")
    logger.info("─" * 100)

    # Build flight constraints section
    flight_constraints = ""
    if flight_info:
        flight_constraints = f"""

**CRITICAL FLIGHT TIME CONSTRAINTS:**
{flight_info}

IMPORTANT RULES:
- Day 1: Start activities ONLY AFTER arrival time + 2-3 hours (customs, baggage, hotel check-in)
  * If arrival is after 2 PM, only schedule evening activities
  * If arrival is evening/night, start activities from Day 2 morning
- Last Day: End ALL activities at least 3 hours BEFORE departure time
  * If departure is before noon, only schedule morning activities and airport transfer
  * If departure is evening, can include afternoon activities but must end by departure time - 3 hours
- DO NOT schedule activities that conflict with flight times
- Adjust the number of activities on first/last day based on available time

"""

    itinerary_prompt = textwrap.dedent(f"""
        Create a detailed {days}-day itinerary for {travelers} traveler(s) visiting {destination} in {month}.
        Budget level: {budget_level}{budget_constraint}
        {flight_constraints}
        For each day provide:
        - Morning: activity with timing and logistics
        - Afternoon: activity with timing and logistics
        - Evening: dinner recommendation and optional activity
        - Daily transportation notes
        - Estimated daily cost per person

        Include realistic timing, distances, and local dining options.
        Format with clear day headers and bullet points.
        Make it 400-600 words total.
    """).strip()
    
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.8,
            max_tokens=800,
            messages=[
                {'role': 'system', 'content': 'You are an expert travel itinerary planner.'},
                {'role': 'user', 'content': itinerary_prompt}
            ]
        )
        result = response.choices[0].message.content.strip()
        logger.info(f"📤 OUTPUT:\n{result}")
        logger.info("=" * 100 + "\n")
        return result
    except Exception as e:
        error_msg = f"Error creating itinerary: {str(e)}"
        logger.error(f"❌ ERROR: {error_msg}")
        logger.info("=" * 100 + "\n")
        return error_msg


def suggest_restaurants(destination: str, budget_level: str, cuisine_preference: str = 'local', interests: str = 'general') -> str:
    """Recommends restaurants using Google Maps Places API.
    
    Args:
        destination: The destination.
        budget_level: The budget level.
        cuisine_preference: The cuisine preference (e.g., 'local', 'international', 'vegetarian').
        interests: Specific interests for dining, e.g., 'family-friendly', 'romantic', 'live music'.
    
    Returns:
        A list of recommended restaurants with real data from Google Maps.
    """
    logger.info("=" * 100)
    logger.info("🔧🔧🔧 TOOL CALL: suggest_restaurants 🔧🔧🔧")
    logger.info("=" * 100)
    logger.info(f"📥 INPUT: destination = '{destination}', budget_level = '{budget_level}', cuisine_preference = '{cuisine_preference}', interests = '{interests}'")
    logger.info("─" * 100)
    
    if not GOOGLE_MAPS_API_KEY:
        logger.warning("⚠️ WARNING: GOOGLE_MAPS_API_KEY not configured. Using LLM fallback.")
        logger.info("─" * 100)
        result = _suggest_restaurants_llm_fallback(destination, budget_level, cuisine_preference, interests)
        logger.info(f"📤 OUTPUT (LLM Fallback):\n{result}")
        logger.info("=" * 100 + "\n")
        return result
    
    try:
        # Build search query
        query = f"{cuisine_preference} restaurants in {destination}"
        if interests != 'general':
            query += f" {interests}"
        
        # Use Google Maps Places API Text Search
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "key": GOOGLE_MAPS_API_KEY,
            "type": "restaurant"
        }
        
        logger.info(f"🌐🌐🌐 GOOGLE MAPS API CALL: suggest_restaurants 🌐🌐🌐")
        logger.info(f"🌐 Query: '{query}'")
        logger.info(f"🌐 Destination: {destination}, Budget: {budget_level}, Cuisine: {cuisine_preference}, Interests: {interests}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        api_status = data.get("status")
        logger.info(f"🌐 API Status: {api_status}")
        logger.info(f"🌐 Results found: {len(data.get('results', []))}")
        
        if api_status != "OK" or not data.get("results"):
            # Log the specific error status
            if api_status != "OK":
                logger.warning(f"⚠️ Google Maps API returned status: {api_status}")
                if api_status == "ZERO_RESULTS":
                    logger.warning("   No results found for the query")
                elif api_status == "REQUEST_DENIED":
                    logger.warning("   Request denied - check API key permissions")
                elif api_status == "INVALID_REQUEST":
                    logger.warning("   Invalid request - check query parameters")
                else:
                    logger.warning(f"   Error message: {data.get('error_message', 'Unknown error')}")
            
            # Fallback to LLM if API fails
            logger.info("   Falling back to LLM...")
            result = _suggest_restaurants_llm_fallback(destination, budget_level, cuisine_preference, interests)
            logger.info(f"📤 OUTPUT (LLM Fallback):\n{result}")
            logger.info("=" * 100 + "\n")
            return result
        
        # Filter by price level and get top 5-6 results
        results = data["results"]
        filtered_results = []
        for place in results:
            price_level = place.get("price_level")
            if price_level:
                price_int = int(price_level)
                if budget_level == 'budget' and price_int <= 1:
                    filtered_results.append(place)
                elif budget_level == 'moderate' and 1 <= price_int <= 2:
                    filtered_results.append(place)
                elif budget_level == 'luxury' and price_int >= 3:
                    filtered_results.append(place)
            else:
                # If no price level, include it
                filtered_results.append(place)
            
            if len(filtered_results) >= 6:
                break
        
        # If filtering removed too many, use original results
        if len(filtered_results) < 3:
            filtered_results = results[:6]
        else:
            filtered_results = filtered_results[:6]
        
        # Format results
        output_lines = [f"Found {len(filtered_results)} restaurants in {destination}:\n"]
        
        price_symbols = {1: '$', 2: '$$', 3: '$$$', 4: '$$$$'}
        
        for i, place in enumerate(filtered_results, 1):
            name = place.get("name", "Unknown")
            rating = place.get("rating", "N/A")
            address = place.get("formatted_address", "Address not available")
            price_level = place.get("price_level")
            price_display = price_symbols.get(int(price_level), "N/A") if price_level else "N/A"
            user_ratings_total = place.get("user_ratings_total", 0)
            
            output_lines.append(f"{i}. {name}")
            output_lines.append(f"   Price: {price_display}")
            if isinstance(rating, (int, float)):
                output_lines.append(f"   Rating: {rating}/5.0 ({user_ratings_total} reviews)" if user_ratings_total else f"   Rating: {rating}/5.0")
            output_lines.append(f"   Address: {address}")
            output_lines.append("")
        
        # Persist restaurants to Pinecone for future RAG calls.
        _rag_upsert_places(
            destination,
            filtered_results,
            kind="restaurant",
            extra_metadata={
                "budget_level": budget_level,
                "cuisine": cuisine_preference,
                "interests": interests,
            },
        )

        # Append related restaurants from the knowledge base.
        rag_block = _rag_places_context(destination, kind="restaurant", interests=interests)

        result = "\n".join(output_lines).strip()
        if rag_block:
            result = result + "\n" + rag_block
        logger.info(f"📤 OUTPUT:\n{result}")
        logger.info("=" * 100 + "\n")
        return result
        
    except requests.RequestException as e:
        error_msg = f"Error accessing Google Maps API: {str(e)}. Falling back to LLM."
        logger.warning(f"⚠️ WARNING: {error_msg}")
        logger.info("─" * 100)
        result = _suggest_restaurants_llm_fallback(destination, budget_level, cuisine_preference, interests)
        logger.info(f"📤 OUTPUT (LLM Fallback):\n{result}")
        logger.info("=" * 100 + "\n")
        return result
    except Exception as e:
        error_msg = f"Error suggesting restaurants: {str(e)}"
        logger.error(f"❌ ERROR: {error_msg}")
        logger.info("=" * 100 + "\n")
        return error_msg


def _suggest_restaurants_llm_fallback(destination: str, budget_level: str, cuisine_preference: str, interests: str) -> str:
    """Fallback to LLM if Google Maps API fails."""
    restaurant_prompt = textwrap.dedent(f"""
        Recommend 5-6 restaurants or dining experiences in {destination}.
        Budget level: {budget_level}
        Cuisine preference: {cuisine_preference}
        Specific interests: {interests}

        For each recommendation include:
        - Restaurant name and type of cuisine
        - What to order (signature dishes)
        - Approximate price range
        - Best time to visit
        - A note on why it fits the interest '{interests}'.

        Keep under 250 words.
    """).strip()

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.7,
            max_tokens=350,
            messages=[
                {'role': 'system', 'content': 'You are a food and dining expert.'},
                {'role': 'user', 'content': restaurant_prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error suggesting restaurants: {str(e)}"


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1
) -> str:
    """
    Search for flight options using Amadeus API with LLM fallback.

    Args:
        origin: Departure location (city name or airport code)
        destination: Destination location (city name or airport code)
        departure_date: Departure date in YYYY-MM-DD format
        return_date: Return date in YYYY-MM-DD format (optional, None for one-way)
        adults: Number of adult travelers

    Returns:
        Formatted list of flight options
    """
    logger.info("=" * 100)
    logger.info("🔧🔧🔧 TOOL CALL: search_flights 🔧🔧🔧")
    logger.info("=" * 100)
    logger.info(f"📥 INPUT: origin='{origin}', destination='{destination}', departure_date={departure_date}, return_date={return_date}, adults={adults}")
    logger.info("─" * 100)

    # Try using Amadeus API
    try:
        from travel_planner.utils.flight_utils import AmadeusFlightClient

        client_flight = AmadeusFlightClient()
        flight_options = client_flight.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults
        )

        if flight_options:
            # Format output
            output_lines = [f"Found {len(flight_options)} flight options:\n"]

            # Group by type
            outbound_flights = [f for f in flight_options if f['type'] == 'outbound']
            return_flights = [f for f in flight_options if f['type'] == 'return']

            if outbound_flights:
                output_lines.append("🛫 OUTBOUND FLIGHTS:")
                for flight in outbound_flights[:3]:  # Show top 3
                    output_lines.append(
                        f"   {flight['airline']} {flight['flight_number']}: "
                        f"{flight['departure_airport']} {flight['departure_time'][:16]} → "
                        f"{flight['arrival_airport']} {flight['arrival_time'][:16]}"
                    )
                    output_lines.append(
                        f"   Duration: {flight['duration']}, "
                        f"Stops: {flight['stops']}, "
                        f"Price: ${flight['price']:.0f} {flight['currency']}"
                    )
                output_lines.append("")

            if return_flights:
                output_lines.append("🛬 RETURN FLIGHTS:")
                for flight in return_flights[:3]:  # Show top 3
                    output_lines.append(
                        f"   {flight['airline']} {flight['flight_number']}: "
                        f"{flight['departure_airport']} {flight['departure_time'][:16]} → "
                        f"{flight['arrival_airport']} {flight['arrival_time'][:16]}"
                    )
                    output_lines.append(
                        f"   Duration: {flight['duration']}, "
                        f"Stops: {flight['stops']}, "
                        f"Price: ${flight['price']:.0f} {flight['currency']}"
                    )
                output_lines.append("")

            # Calculate total
            if outbound_flights and return_flights:
                cheapest_total = min(f['price'] for f in outbound_flights) + min(f['price'] for f in return_flights)
                output_lines.append(f"Estimated total (cheapest combination): ${cheapest_total:.0f} USD")

            result = "\n".join(output_lines).strip()
            logger.info(f"📤 OUTPUT (Amadeus API):\n{result}")
            logger.info("=" * 100 + "\n")
            return result

    except Exception as e:
        logger.warning(f"⚠️ Amadeus API failed: {e}, falling back to LLM")

    # LLM Fallback
    return _search_flights_llm_fallback(origin, destination, departure_date, return_date, adults)


def _search_flights_llm_fallback(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str],
    adults: int
) -> str:
    """LLM fallback when Amadeus API fails"""
    trip_type = "round-trip" if return_date else "one-way"

    prompt = textwrap.dedent(f"""
        Provide realistic flight options for a {trip_type} trip:

        Route: {origin} → {destination}
        Departure: {departure_date}
        {f'Return: {return_date}' if return_date else ''}
        Travelers: {adults}

        List 3-5 flight options with:
        - Airline name and flight number
        - Departure and arrival times (with timezones)
        - Flight duration
        - Number of stops (specify layover cities if applicable)
        - Estimated price per person in USD

        Make it realistic based on typical routes, airlines serving these cities, and current pricing.
        Consider factors like distance, popular carriers, and seasonal pricing.
        Keep under 250 words.
    """).strip()

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.7,
            max_tokens=350,
            messages=[
                {'role': 'system', 'content': 'You are a flight search expert with knowledge of airline routes, schedules, and pricing.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        result = response.choices[0].message.content.strip()
        logger.info(f"📤 OUTPUT (LLM Fallback):\n{result}")
        logger.info("=" * 100 + "\n")
        return result
    except Exception as e:
        error_msg = f"Error searching flights: {str(e)}"
        logger.error(f"❌ ERROR: {error_msg}")
        logger.info("=" * 100 + "\n")
        return error_msg


# Summary list of all tools - 7 core tools
ALL_TOOLS = [
    research_destination,
    check_weather,
    estimate_costs,
    find_attractions,
    create_day_by_day_plan,
    suggest_restaurants,
    search_flights  # NEW: Flight search tool
]


# Tool Schema for OpenAI Function Calling
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "research_destination",
            "description": "Research comprehensive information about a travel destination using Wikipedia API. Returns detailed information including best time to visit, attractions, culture, history, and logistics. Use this when the user asks about a destination or you need background information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "The destination city or country to research (e.g., 'Paris', 'Japan', 'New York City')"
                    }
                },
                "required": ["destination"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_weather",
            "description": "Check weather for a destination. Provides detailed 5-day forecast if travel is within 5 days, or typical climate information for later dates. IMPORTANT: Pass travel_date if available for more accurate forecast.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "The destination to check weather for"
                    },
                    "month": {
                        "type": "string",
                        "description": "The month to check (e.g., 'January', 'May', 'December')"
                    },
                    "travel_date": {
                        "type": "string",
                        "description": "Optional travel start date in YYYY-MM-DD format. If provided, determines whether to use detailed forecast (within 5 days) or climate information (later dates)."
                    }
                },
                "required": ["destination", "month"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_costs",
            "description": "Estimate trip costs broken down by accommodation, food, transportation, and activities. Use this when discussing budget or when the user asks about costs. IMPORTANT: Always provide the travelers parameter to ensure accurate cost calculation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "The destination to estimate costs for"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days for the trip"
                    },
                    "budget_level": {
                        "type": "string",
                        "enum": ["budget", "moderate", "luxury"],
                        "description": "Budget level - 'budget' for economical travel, 'moderate' for mid-range, 'luxury' for high-end"
                    },
                    "budget_amount": {
                        "type": "number",
                        "description": "Optional actual budget amount in USD (e.g., 1500.0). Use this when user provides a specific budget amount."
                    },
                    "itinerary_info": {
                        "type": "string",
                        "description": "Optional information about the planned itinerary (activities, accommodations, restaurants, etc.). Use this when estimating costs based on a specific planned itinerary."
                    },
                    "travelers": {
                        "type": "integer",
                        "description": "Number of travelers (e.g., 1, 2, 4). CRITICAL: Always provide this parameter from constraints.travelers to ensure costs are calculated correctly for the number of people."
                    }
                },
                "required": ["destination", "days", "budget_level"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_attractions",
            "description": "Find and recommend real attractions, activities, and points of interest using Google Maps Places API. Returns actual places with ratings, addresses, and types. Use this to get authentic, verified location data based on trip length and traveler interests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "The destination to find attractions in"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days for the trip"
                    },
                    "interests": {
                        "type": "string",
                        "description": "Traveler interests or preferences (e.g., 'history and museums', 'food and nightlife', 'nature and hiking', 'family-friendly', 'general')",
                        "default": "general"
                    }
                },
                "required": ["destination", "days"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_day_by_day_plan",
            "description": "Generate a complete day-by-day itinerary with morning, afternoon, and evening activities. Use this as the final step when you have gathered enough information about the destination, dates, budget, and traveler preferences. IMPORTANT: If flight search was performed, you MUST extract and pass flight arrival/departure times as flight_info to ensure activities don't conflict with flights. If user provided a specific budget amount, you MUST pass it as budget_limit to ensure the itinerary stays within budget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "The destination for the itinerary"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days for the trip"
                    },
                    "month": {
                        "type": "string",
                        "description": "The month of travel"
                    },
                    "budget_level": {
                        "type": "string",
                        "enum": ["budget", "moderate", "luxury"],
                        "description": "Budget level for the trip"
                    },
                    "travelers": {
                        "type": "integer",
                        "description": "Number of travelers"
                    },
                    "budget_limit": {
                        "type": "number",
                        "description": "Optional total budget limit in USD (e.g., 1500.0). If user specified a budget amount, MUST pass this to ensure costs don't exceed the limit."
                    },
                    "flight_info": {
                        "type": "string",
                        "description": "Optional flight timing constraints extracted from search_flights tool results. Format: 'Arrival: Day 1 at 4:00 PM\\nDeparture: Day 7 at 11:30 PM'. CRITICAL: If flights were searched, you MUST extract arrival/departure times from tool results and pass here to avoid scheduling conflicts."
                    }
                },
                "required": ["destination", "days", "month", "budget_level", "travelers"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_restaurants",
            "description": "Suggest real restaurants and dining experiences using Google Maps Places API. Returns actual restaurants with ratings, price levels ($-$$$$), addresses, and review counts. Filters by budget level and cuisine preferences. Use this to get authentic, verified restaurant data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "The destination to find restaurants in"
                    },
                    "budget_level": {
                        "type": "string",
                        "enum": ["budget", "moderate", "luxury"],
                        "description": "Budget level for dining - 'budget' ($), 'moderate' ($$), 'luxury' ($$$ or $$$$)"
                    },
                    "cuisine_preference": {
                        "type": "string",
                        "description": "Type of cuisine preferred (e.g., 'local', 'international', 'vegetarian', 'seafood')",
                        "default": "local"
                    },
                    "interests": {
                        "type": "string",
                        "description": "Specific interests for dining, e.g., 'family-friendly', 'romantic', 'live music'",
                        "default": "general"
                    }
                },
                "required": ["destination", "budget_level"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for flight options between two locations using Amadeus Flight API. Returns real flight data including airlines, flight numbers, times, prices, and stops. Use this when the user provides an origin location and you need to find flights for their trip.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin city or airport code (e.g., 'San Francisco', 'SFO', 'New York', 'JFK')"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination city or airport code (e.g., 'Tokyo', 'NRT', 'Paris', 'CDG')"
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Departure date in YYYY-MM-DD format (e.g., '2025-04-01')"
                    },
                    "return_date": {
                        "type": "string",
                        "description": "Return date in YYYY-MM-DD format for round-trip (optional, omit for one-way). Example: '2025-04-07'"
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adult travelers (default: 1)"
                    }
                },
                "required": ["origin", "destination", "departure_date"],
                "additionalProperties": False
            }
        }
    }
]
