"""
Amadeus Flight Search Integration
Uses Amadeus Flight Offers Search API with LLM fallback
"""

import os
import requests
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class AmadeusFlightClient:
    """Client for Amadeus Flight Offers Search API"""

    def __init__(self):
        self.api_key = os.getenv("AMADEUS_API_KEY")
        self.api_secret = os.getenv("AMADEUS_API_SECRET")
        self.base_url = "https://test.api.amadeus.com"  # Test environment
        # Production: "https://api.amadeus.com"
        self.access_token = None
        self.token_expires_at = None

    def _get_access_token(self) -> str:
        """
        Get OAuth 2.0 access token
        Token expires in ~30 minutes, cached to reduce API calls
        """
        # Check if token is still valid
        if self.access_token and self.token_expires_at:
            if datetime.now().timestamp() < self.token_expires_at:
                return self.access_token

        # Request new token
        url = f"{self.base_url}/v1/security/oauth2/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }

        logger.info("🔐 Requesting Amadeus access token...")
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data["access_token"]
        # Set expiration time (5 minutes before actual expiry for safety)
        expires_in = token_data.get("expires_in", 1800)
        self.token_expires_at = datetime.now().timestamp() + expires_in - 300

        logger.info(f"✅ Access token obtained (expires in {expires_in}s)")
        return self.access_token

    def _convert_to_iata_code(self, location: str) -> Optional[str]:
        """
        Convert city name to IATA airport code
        Uses Amadeus Airport & City Search API

        Examples:
        - "San Francisco" → "SFO"
        - "Tokyo" → "NRT" (or "HND")
        - "New York" → "JFK" (or "LGA", "EWR")
        """
        try:
            # Clean location: extract city name only (remove country/state)
            # "Paris, France" → "Paris"
            # "Tokyo, Japan" → "Tokyo"
            clean_location = location.split(',')[0].strip()

            token = self._get_access_token()
            url = f"{self.base_url}/v1/reference-data/locations"
            headers = {"Authorization": f"Bearer {token}"}
            params = {
                "keyword": clean_location,
                "subType": "AIRPORT,CITY",
                "page[limit]": 1
            }

            logger.info(f"🔍 Converting '{location}' (cleaned: '{clean_location}') to IATA code...")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Debug: log the full response
            logger.info(f"📊 Amadeus API response: {json.dumps(data, indent=2)}")

            if data.get("data") and len(data["data"]) > 0:
                iata_code = data["data"][0]["iataCode"]
                location_name = data["data"][0].get("name", "")
                location_type = data["data"][0].get("subType", "")
                logger.info(f"✓ '{location}' → {iata_code} ({location_name}, {location_type})")
                return iata_code

            # Amadeus API returned no data - use LLM fallback
            logger.warning(f"⚠️ Amadeus API returned no data for '{location}', using LLM fallback...")
            return self._convert_to_iata_code_llm(location)

        except Exception as e:
            logger.error(f"❌ Amadeus API error for '{location}': {e}, using LLM fallback...")
            return self._convert_to_iata_code_llm(location)

    def _convert_to_iata_code_llm(self, location: str) -> Optional[str]:
        """
        Convert city name to IATA code using LLM knowledge
        Fallback when Amadeus API fails

        Args:
            location: City or airport name

        Returns:
            IATA code or None
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            prompt = f"""What is the main IATA airport code for "{location}"?

Rules:
1. Return ONLY the 3-letter IATA code, nothing else
2. For cities with multiple airports, return the main international airport
3. Examples:
   - "Tokyo" → "NRT" (Narita)
   - "New York" → "JFK"
   - "Paris" → "CDG"
   - "London" → "LHR"
   - "Boston" → "BOS"

Location: {location}
IATA Code:"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an airport code expert. Return only the 3-letter IATA code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=10
            )

            iata_code = response.choices[0].message.content.strip().upper()

            # Validate it's a 3-letter code
            if iata_code and len(iata_code) == 3 and iata_code.isalpha():
                logger.info(f"✓ LLM converted '{location}' → {iata_code}")
                return iata_code
            else:
                logger.warning(f"⚠️ LLM returned invalid IATA code: {iata_code}")
                return None

        except Exception as e:
            logger.error(f"❌ LLM conversion failed for '{location}': {e}")
            return None

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,  # YYYY-MM-DD
        return_date: Optional[str] = None,
        adults: int = 1,
        cabin_class: str = "ECONOMY",
        max_results: int = 5,
        currency: str = "USD"
    ) -> List[Dict[str, Any]]:
        """
        Search for flights

        Args:
            origin: Departure location (city name or IATA code)
            destination: Destination location (city name or IATA code)
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date (YYYY-MM-DD), None for one-way
            adults: Number of adult travelers
            cabin_class: Cabin class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
            max_results: Maximum number of results to return
            currency: Currency code

        Returns:
            List of flight options with details
        """
        if not self.api_key or not self.api_secret:
            logger.warning("⚠️ Amadeus API credentials not configured")
            return []

        try:
            # Convert city names to IATA codes
            origin_code = self._convert_to_iata_code(origin)
            dest_code = self._convert_to_iata_code(destination)

            if not origin_code or not dest_code:
                logger.error("❌ Failed to convert locations to IATA codes")
                return []

            # Get access token
            token = self._get_access_token()

            # Build request
            url = f"{self.base_url}/v2/shopping/flight-offers"
            headers = {"Authorization": f"Bearer {token}"}
            params = {
                "originLocationCode": origin_code,
                "destinationLocationCode": dest_code,
                "departureDate": departure_date,
                "adults": adults,
                "currencyCode": currency,
                "max": max_results,
                "travelClass": cabin_class
            }

            if return_date:
                params["returnDate"] = return_date

            logger.info("=" * 100)
            logger.info("✈️✈️✈️ AMADEUS FLIGHT SEARCH ✈️✈️✈️")
            logger.info("=" * 100)
            logger.info(f"📍 Route: {origin} ({origin_code}) → {destination} ({dest_code})")
            logger.info(f"📅 Dates: {departure_date}" + (f" - {return_date}" if return_date else " (one-way)"))
            logger.info(f"👥 Travelers: {adults}, Class: {cabin_class}")
            logger.info("─" * 100)

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            flight_offers = data.get("data", [])

            logger.info(f"✓ Found {len(flight_offers)} flight offers")
            logger.info("=" * 100 + "\n")

            # Format results
            formatted_flights = self._format_flight_offers(flight_offers, origin_code, dest_code)
            return formatted_flights

        except requests.RequestException as e:
            logger.error(f"❌ Amadeus API error: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error searching flights: {e}")
            return []

    def _format_flight_offers(
        self,
        offers: List[Dict],
        origin_code: str,
        dest_code: str
    ) -> List[Dict[str, Any]]:
        """
        Format Amadeus API response to simplified flight data
        """
        formatted = []

        for idx, offer in enumerate(offers[:5], 1):  # Take first 5
            try:
                price = offer.get("price", {})
                total_price = float(price.get("total", 0))
                currency = price.get("currency", "USD")

                # Extract itinerary information
                itineraries = offer.get("itineraries", [])

                # Round-trip has 2 itineraries (outbound + return)
                for itin_idx, itinerary in enumerate(itineraries):
                    segments = itinerary.get("segments", [])
                    if not segments:
                        continue

                    # First and last segment
                    first_seg = segments[0]
                    last_seg = segments[-1]

                    # Calculate total duration
                    duration = itinerary.get("duration", "").replace("PT", "")

                    # Extract airline information
                    carrier_code = first_seg.get("carrierCode", "")
                    flight_number = f"{carrier_code}{first_seg.get('number', '')}"

                    # Number of stops
                    stops = len(segments) - 1

                    formatted.append({
                        "option_id": idx,
                        "type": "outbound" if itin_idx == 0 else "return",
                        "airline": self._get_airline_name(carrier_code),
                        "airline_code": carrier_code,
                        "flight_number": flight_number,
                        "departure_airport": first_seg.get("departure", {}).get("iataCode"),
                        "departure_time": first_seg.get("departure", {}).get("at"),
                        "arrival_airport": last_seg.get("arrival", {}).get("iataCode"),
                        "arrival_time": last_seg.get("arrival", {}).get("at"),
                        "duration": self._format_duration(duration),
                        "stops": stops,
                        "price": total_price / len(itineraries) if len(itineraries) > 1 else total_price,
                        "currency": currency,
                    })

            except Exception as e:
                logger.warning(f"⚠️ Error formatting flight offer: {e}")
                continue

        return formatted

    def _get_airline_name(self, code: str) -> str:
        """
        Convert airline code to name
        Simplified version, can maintain a full mapping table
        """
        airlines = {
            "UA": "United Airlines",
            "AA": "American Airlines",
            "DL": "Delta Air Lines",
            "NH": "ANA",
            "JL": "Japan Airlines",
            "BA": "British Airways",
            "LH": "Lufthansa",
            "AF": "Air France",
            "KL": "KLM",
            "SQ": "Singapore Airlines",
            "EK": "Emirates",
            "QR": "Qatar Airways",
            "CX": "Cathay Pacific",
            "TK": "Turkish Airlines",
        }
        return airlines.get(code, f"Airline {code}")

    def _format_duration(self, duration: str) -> str:
        """
        Format flight duration
        Input: "14H30M" or "2H15M"
        Output: "14h 30m" or "2h 15m"
        """
        duration = duration.replace("H", "h ").replace("M", "m")
        return duration.strip()
