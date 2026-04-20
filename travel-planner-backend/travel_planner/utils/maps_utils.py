"""
Google Maps utility for calculating travel times between locations.
"""
import logging
import os
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class GoogleMapsClient:
    """Client for Google Maps APIs."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Google Maps client.

        Args:
            api_key: Google Maps API key. If not provided, reads from GOOGLE_MAPS_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            logger.warning("Google Maps API key not found. Travel time calculation will be disabled.")
        self.base_url = "https://maps.googleapis.com/maps/api"

    def get_travel_time(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
        departure_time: str = "now"
    ) -> Optional[int]:
        """
        Get travel time between two locations using Google Distance Matrix API.

        Args:
            origin: Starting location (address or place name)
            destination: Ending location (address or place name)
            mode: Travel mode - "driving", "walking", "bicycling", "transit" (default: "transit")
            departure_time: When to depart - "now" or unix timestamp (default: "now")

        Returns:
            Travel time in minutes, or None if request fails
        """
        if not self.api_key:
            logger.debug("Google Maps API key not configured, skipping travel time calculation")
            return None

        # Try transit first, then fallback to driving if transit fails
        modes_to_try = [mode]
        if mode == "transit":
            modes_to_try.append("driving")

        for current_mode in modes_to_try:
            try:
                url = f"{self.base_url}/distancematrix/json"
                params = {
                    "origins": origin,
                    "destinations": destination,
                    "mode": current_mode,
                    "key": self.api_key,
                }

                # Only add departure_time for transit mode
                if current_mode == "transit":
                    params["departure_time"] = departure_time

                logger.debug(f"Trying {current_mode} mode: {origin} -> {destination}")
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                # Check if request was successful
                if data.get("status") != "OK":
                    logger.warning(f"Google Maps API returned status: {data.get('status')}")
                    continue

                # Extract travel time
                rows = data.get("rows", [])
                if not rows:
                    logger.warning("No rows returned from Google Maps API")
                    continue

                elements = rows[0].get("elements", [])
                if not elements:
                    logger.warning("No elements in first row from Google Maps API")
                    continue

                element = elements[0]
                if element.get("status") != "OK":
                    logger.warning(f"Element status: {element.get('status')} for route {origin} -> {destination}")
                    continue

                duration = element.get("duration", {})
                duration_seconds = duration.get("value")

                if duration_seconds is None:
                    logger.warning("No duration value returned")
                    continue

                # Convert seconds to minutes (round up)
                duration_minutes = (duration_seconds + 59) // 60

                logger.info(f"✓ Travel time ({current_mode}): '{origin}' → '{destination}' = {duration_minutes} min")
                return duration_minutes

            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling Google Maps API: {e}")
                continue
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Error parsing Google Maps API response: {e}")
                continue

        # All modes failed
        logger.warning(f"Failed to get travel time for {origin} -> {destination} with all modes")
        return None


def add_travel_times_to_plan(plan: Dict[str, Any], maps_client: Optional[GoogleMapsClient] = None) -> Dict[str, Any]:
    """
    Add travel time information to a travel plan.

    Args:
        plan: The travel plan JSON object
        maps_client: Google Maps client instance. If None, creates a new one.

    Returns:
        Updated plan with travel_time_to_next field added to items
    """
    if maps_client is None:
        maps_client = GoogleMapsClient()

    if not maps_client.api_key:
        logger.info("Skipping travel time calculation - no API key configured")
        return plan

    # Get destination for context (helps with geocoding)
    destination_context = plan.get("destination", "")

    days = plan.get("days", [])
    for day in days:
        items = day.get("items", [])

        for i in range(len(items) - 1):
            current_item = items[i]
            next_item = items[i + 1]

            current_place = current_item.get("place", "")
            next_place = next_item.get("place", "")

            if not current_place or not next_place:
                continue

            # Add destination context to help with geocoding
            origin = f"{current_place}, {destination_context}"
            destination = f"{next_place}, {destination_context}"

            # Calculate travel time
            travel_time = maps_client.get_travel_time(origin, destination)

            if travel_time is not None:
                current_item["travel_time_to_next"] = travel_time
                logger.info(f"Added travel time: {current_place} → {next_place} = {travel_time} min")
            else:
                # If calculation fails, don't add the field (frontend will show placeholder)
                logger.warning(f"Failed to calculate travel time: {current_place} → {next_place}")

    return plan
