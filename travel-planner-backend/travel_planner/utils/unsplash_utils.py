"""
Unsplash API utility for fetching destination images.
"""
import logging
import os
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class UnsplashClient:
    """Client for Unsplash API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Unsplash client.

        Args:
            api_key: Unsplash API Access Key. If not provided, reads from UNSPLASH_ACCESS_KEY env var.
        """
        self.api_key = api_key or os.getenv("UNSPLASH_ACCESS_KEY")
        if not self.api_key:
            logger.warning("Unsplash API key not found. Will use default images.")
        self.base_url = "https://api.unsplash.com"

    def get_destination_image(
        self,
        destination: str,
        width: int = 2000,
        height: int = 1200,
        orientation: str = "landscape"
    ) -> Optional[str]:
        """
        Get a photo URL for a destination from Unsplash.

        Args:
            destination: Destination name (city, country, or landmark)
            width: Desired image width
            height: Desired image height
            orientation: Image orientation - "landscape", "portrait", or "squarish"

        Returns:
            Image URL from Unsplash, or None if request fails
        """
        if not self.api_key:
            logger.debug("Unsplash API key not configured, returning default image")
            return self._get_default_image()

        try:
            # Search for photos related to the destination
            url = f"{self.base_url}/search/photos"
            params = {
                "query": f"{destination} travel landmark city",
                "per_page": 1,
                "orientation": orientation,
                "order_by": "relevant",
            }
            headers = {
                "Authorization": f"Client-ID {self.api_key}",
            }

            logger.debug(f"Searching Unsplash for: {destination}")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Check if we got any results
            results = data.get("results", [])
            if not results:
                logger.warning(f"No images found for destination: {destination}")
                return self._get_default_image()

            # Get the first photo
            photo = results[0]
            photo_urls = photo.get("urls", {})

            # Get the regular size URL (good quality, not too large)
            image_url = photo_urls.get("regular")

            if not image_url:
                logger.warning("No image URL in response")
                return self._get_default_image()

            # Add custom dimensions if needed (Unsplash supports dynamic resizing)
            if width and height:
                image_url = f"{image_url}&w={width}&h={height}&fit=crop"

            logger.info(f"✓ Found Unsplash image for '{destination}': {photo.get('id')}")
            return image_url

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Unsplash API: {e}")
            return self._get_default_image()
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing Unsplash API response: {e}")
            return self._get_default_image()

    def _get_default_image(self) -> str:
        """
        Get default travel image URL.

        Returns:
            Default Unsplash image URL
        """
        return "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&q=80&w=2021"


def add_destination_image_to_plan(plan: dict, unsplash_client: Optional[UnsplashClient] = None) -> dict:
    """
    Add destination background image URL to a travel plan.

    Args:
        plan: The travel plan JSON object
        unsplash_client: Unsplash client instance. If None, creates a new one.

    Returns:
        Updated plan with destination_image_url field
    """
    if unsplash_client is None:
        unsplash_client = UnsplashClient()

    destination = plan.get("destination", "")
    if not destination:
        logger.warning("No destination in plan, using default image")
        plan["destination_image_url"] = unsplash_client._get_default_image()
        return plan

    # Extract main location (city/country before comma)
    main_location = destination.split(',')[0].strip()

    # Get image URL from Unsplash
    image_url = unsplash_client.get_destination_image(main_location)

    # Add to plan
    plan["destination_image_url"] = image_url
    logger.info(f"Added destination image URL to plan for {main_location}")

    return plan
