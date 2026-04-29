"""
Seed Pinecone with destination knowledge for popular cities.

This script triggers the existing tool functions (research_destination,
find_attractions, suggest_restaurants), each of which transparently upserts
its results to Pinecone. The script itself is a thin loop - the upsert logic
lives inside the tools, so seeding always uses the same code path as runtime.

Usage:
    cd travel-planner-backend
    python -m scripts.seed_pinecone
    python -m scripts.seed_pinecone --cities "Tokyo,Paris,Bali"
    python -m scripts.seed_pinecone --skip-restaurants
    python -m scripts.seed_pinecone --interests "food,history"

Requirements:
    PINECONE_API_KEY, OPENAI_API_KEY, GOOGLE_MAPS_API_KEY (optional but recommended)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import List

# Ensure parent directory is on path so `travel_planner` imports work when
# running this script directly.
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(HERE)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from travel_planner.utils.tools_def import (  # noqa: E402
    find_attractions,
    research_destination,
    suggest_restaurants,
)
from travel_planner.utils.pinecone_utils import PineconeStore  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("seed_pinecone")

DEFAULT_CITIES: List[str] = [
    "Tokyo, Japan",
    "Paris, France",
    "New York City, USA",
    "London, UK",
    "Rome, Italy",
    "Barcelona, Spain",
    "Bali, Indonesia",
    "Iceland",
    "Sydney, Australia",
    "Bangkok, Thailand",
    "Dubai, UAE",
    "Singapore",
    "Istanbul, Turkey",
    "Amsterdam, Netherlands",
    "Maldives",
    "Hawaii, USA",
    "Santorini, Greece",
    "Venice, Italy",
    "Prague, Czech Republic",
    "Switzerland",
]


def seed_city(
    city: str,
    interests: str,
    skip_attractions: bool,
    skip_restaurants: bool,
) -> None:
    """Run the three info-gathering tools for one city."""
    logger.info("=" * 80)
    logger.info(f"Seeding city: {city}")
    logger.info("=" * 80)

    try:
        logger.info("[1/3] research_destination ...")
        research_destination(city)
    except Exception as e:
        logger.warning(f"research_destination failed for '{city}': {e}")

    if not skip_attractions:
        try:
            logger.info("[2/3] find_attractions ...")
            find_attractions(city, days=3, interests=interests)
        except Exception as e:
            logger.warning(f"find_attractions failed for '{city}': {e}")
    else:
        logger.info("[2/3] find_attractions skipped")

    if not skip_restaurants:
        try:
            logger.info("[3/3] suggest_restaurants ...")
            suggest_restaurants(
                city,
                budget_level="moderate",
                cuisine_preference="local",
                interests=interests,
            )
        except Exception as e:
            logger.warning(f"suggest_restaurants failed for '{city}': {e}")
    else:
        logger.info("[3/3] suggest_restaurants skipped")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cities",
        type=str,
        default=None,
        help='Comma-separated city list (e.g. "Tokyo,Paris,Bali"). '
        f"Defaults to {len(DEFAULT_CITIES)} popular cities.",
    )
    parser.add_argument(
        "--interests",
        type=str,
        default="general",
        help="Interests passed to find_attractions / suggest_restaurants. Default: 'general'.",
    )
    parser.add_argument(
        "--skip-attractions",
        action="store_true",
        help="Do not call find_attractions.",
    )
    parser.add_argument(
        "--skip-restaurants",
        action="store_true",
        help="Do not call suggest_restaurants.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Seconds to sleep between cities (rate limiting). Default: 1.0",
    )
    args = parser.parse_args()

    # Verify Pinecone is reachable before doing expensive work.
    store = PineconeStore.instance()
    if not store.enabled:
        logger.error(
            "PineconeStore is disabled. Make sure PINECONE_API_KEY and OPENAI_API_KEY "
            "are set in your .env file, then re-run."
        )
        return 1

    cities = (
        [c.strip() for c in args.cities.split(",") if c.strip()]
        if args.cities
        else DEFAULT_CITIES
    )

    logger.info(f"Seeding {len(cities)} cities into Pinecone index '{store.index_name}'")
    logger.info(f"Cities: {cities}")

    for idx, city in enumerate(cities, start=1):
        logger.info(f"\n>>> [{idx}/{len(cities)}] {city}")
        seed_city(
            city,
            interests=args.interests,
            skip_attractions=args.skip_attractions,
            skip_restaurants=args.skip_restaurants,
        )
        if idx < len(cities) and args.sleep > 0:
            time.sleep(args.sleep)

    logger.info("\n" + "=" * 80)
    logger.info(f"Seed complete: {len(cities)} cities processed.")
    logger.info("Inspect the Pinecone Console to confirm vectors were written.")
    logger.info("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
