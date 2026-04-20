"""
Data Normalization Module
Handles data format conversion and standardization.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import logging
from openai import OpenAI
import os
import json

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Data Normalizer with LLM-powered standardization"""
    
    @staticmethod
    def normalize_date(date_str: Optional[str]) -> Optional[str]:
        """Normalizes date format to YYYY-MM-DD.

        Args:
            date_str: The date string (can be None).

        Returns:
            The standardized date string or None.
        """
        if not date_str:
            return None

        # Try multiple date formats
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m-%d-%Y",
            "%m/%d/%Y"
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None
    
    @staticmethod
    def normalize_city_name(city: str) -> str:
        """Normalizes city names.
        
        Args:
            city: The city name.
        
        Returns:
            The standardized city name.
        """
        # Remove extra spaces and capitalize
        city = re.sub(r'\s+', ' ', city.strip())
        return city.title()
    
    @staticmethod
    def normalize_price(price: Any):
        """Normalizes prices.

        Args:
            price: The price (can be a string or number).

        Returns:
            The price as a float, or None if no valid price found.
        """
        if price is None or price == "":
            return None

        if isinstance(price, (int, float)):
            return float(price) if price > 0 else None

        # Remove currency symbols and commas
        price_str = str(price)
        price_str = re.sub(r'[^\d.]', '', price_str)

        try:
            result = float(price_str)
            return result if result > 0 else None
        except ValueError:
            return None
    
    @staticmethod
    def normalize_travel_request_with_llm(raw_request: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes a travel request using LLM for intelligent standardization.

        Corrects spelling errors, standardizes formats, and ensures consistency.

        Args:
            raw_request: The raw request dictionary.

        Returns:
            The standardized request dictionary.
        """
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            prompt = f"""Normalize and standardize the following travel request data. Correct any spelling errors, standardize formats, and ensure consistency.

Input data:
{json.dumps(raw_request, indent=2)}

Rules:
1. **origin & destination**: Correct spelling errors and format as "City, Country" (e.g., "Bostn" → "Boston, USA", "Tokio" → "Tokyo, Japan", "paris" → "Paris, France")
2. **dates**: Convert to YYYY-MM-DD format
3. **budget**: Extract numeric value only (remove currency symbols)
4. **duration/days**: Ensure it's a number
5. **travelers**: Ensure it's a number
6. **interests**: Clean up and standardize as a list of strings
7. Keep other fields as-is unless they need correction

Return ONLY valid JSON with the normalized data, no explanation.

Example:
Input: {{"origin": "Bostn", "destination": "tokio", "start_date": "April 1, 2025"}}
Output: {{"origin": "Boston, USA", "destination": "Tokyo, Japan", "start_date": "2025-04-01"}}
"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a data normalization assistant. Always return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
            )

            result = response.choices[0].message.content.strip()

            # Clean up JSON formatting
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()

            normalized = json.loads(result)
            logger.info(f"✅ LLM normalized request: {raw_request} → {normalized}")
            return normalized

        except Exception as e:
            logger.warning(f"⚠️ LLM normalization failed, using fallback: {e}")
            # Fallback to basic normalization
            return DataNormalizer.normalize_travel_request(raw_request)

    @staticmethod
    def normalize_travel_request(raw_request: Dict[str, Any]) -> Dict[str, Any]:
        """Basic normalization (fallback when LLM is unavailable).

        Args:
            raw_request: The raw request dictionary.

        Returns:
            The standardized request dictionary.
        """
        normalized = {}

        # Normalize city
        if "origin" in raw_request:
            normalized["origin"] = DataNormalizer.normalize_city_name(raw_request["origin"])
        if "destination" in raw_request:
            normalized["destination"] = DataNormalizer.normalize_city_name(raw_request["destination"])

        # Normalize date
        if "start_date" in raw_request:
            normalized["start_date"] = DataNormalizer.normalize_date(raw_request["start_date"])
        if "end_date" in raw_request:
            normalized["end_date"] = DataNormalizer.normalize_date(raw_request["end_date"])

        # Normalize budget
        if "budget" in raw_request:
            normalized["budget"] = DataNormalizer.normalize_price(raw_request["budget"])

        # Keep other fields
        for key, value in raw_request.items():
            if key not in normalized:
                normalized[key] = value

        return normalized
    
    @staticmethod
    def format_travel_plan(plan_data: Dict[str, Any]) -> str:
        """Formats a travel plan into readable text.
        
        Args:
            plan_data: The plan data.
        
        Returns:
            The formatted text.
        """
        output = ["=== Travel Plan ===\n"]
        
        if "destination" in plan_data:
            output.append(f"Destination: {plan_data['destination']}")
        
        if "dates" in plan_data:
            output.append(f"Dates: {plan_data['dates']}")
        
        if "flights" in plan_data:
            output.append("\nFlight Information:")
            for flight in plan_data["flights"]:
                output.append(f"  - {flight.get('flight_no')}: {flight.get('departure_time')} - {flight.get('arrival_time')}")
        
        if "hotels" in plan_data:
            output.append("\nHotel Information:")
            for hotel in plan_data["hotels"]:
                output.append(f"  - {hotel.get('hotel_name')}: ${hotel.get('price_per_night')}/night")
        
        if "attractions" in plan_data:
            output.append("\nRecommended Attractions:")
            for attraction in plan_data["attractions"]:
                output.append(f"  - {attraction.get('name')}")
        
        return "\n".join(output)
