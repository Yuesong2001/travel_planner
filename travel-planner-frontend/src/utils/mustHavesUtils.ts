import type { Plan } from "../types";

export interface MustHaveItem {
  interest: string;
  description: string;
  count: number;
  icon: string;
}

// Interest keywords mapping for matching
const INTEREST_KEYWORDS: Record<string, string[]> = {
  "cherry blossom": ["cherry", "blossom", "sakura", "hanami"],
  "traditional culture": ["temple", "shrine", "traditional", "cultural", "historic", "museum", "palace", "garden"],
  "nature": ["park", "nature", "mountain", "forest", "lake", "beach", "garden", "hiking"],
  "food": ["restaurant", "food", "dining", "market", "cuisine", "cafe"],
  "shopping": ["shopping", "market", "mall", "store", "boutique"],
  "nightlife": ["nightlife", "bar", "club", "entertainment"],
  "art": ["art", "museum", "gallery", "exhibition"],
  "architecture": ["architecture", "building", "tower", "bridge"],
  "beach": ["beach", "ocean", "sea", "coastal"],
  "adventure": ["adventure", "hiking", "climbing", "diving", "skiing"],
};

// Icon mapping for different interests
const INTEREST_ICONS: Record<string, string> = {
  "cherry blossom": "nature",
  "traditional culture": "culture",
  "nature": "nature",
  "food": "food",
  "shopping": "sightseeing",
  "nightlife": "sightseeing",
  "art": "culture",
  "architecture": "culture",
  "beach": "nature",
  "adventure": "nature",
};

/**
 * Check if an activity matches an interest
 */
function matchesInterest(activity: any, interest: string): boolean {
  const interestLower = interest.toLowerCase();
  const place = (activity.place || "").toLowerCase();
  const reason = (activity.reason || "").toLowerCase();
  const type = (activity.type || "").toLowerCase();

  // Direct match
  if (place.includes(interestLower) || reason.includes(interestLower) || type.includes(interestLower)) {
    return true;
  }

  // Keyword matching
  const keywords = INTEREST_KEYWORDS[interestLower] || [];
  for (const keyword of keywords) {
    if (place.includes(keyword) || reason.includes(keyword) || type.includes(keyword)) {
      return true;
    }
  }

  return false;
}

/**
 * Generate Must-Haves items from plan interests
 */
export function generateMustHaves(plan: Plan | null): MustHaveItem[] {
  if (!plan) return [];

  const interests = plan.constraints?.interests || [];
  if (interests.length === 0) return [];

  const mustHaves: MustHaveItem[] = [];

  for (const interest of interests) {
    let count = 0;
    const matchedPlaces: string[] = [];

    // Count activities that match this interest
    for (const day of plan.days || []) {
      for (const item of day.items || []) {
        if (matchesInterest(item, interest)) {
          count++;
          if (!matchedPlaces.includes(item.place)) {
            matchedPlaces.push(item.place);
          }
        }
      }
    }

    // Only include if we found matching activities
    if (count > 0) {
      const locationText = matchedPlaces.length === 1
        ? "1 location"
        : `${matchedPlaces.length} locations`;

      mustHaves.push({
        interest: interest.charAt(0).toUpperCase() + interest.slice(1),
        description: `${locationText} included`,
        count: count,
        icon: INTEREST_ICONS[interest.toLowerCase()] || "sightseeing",
      });
    }
  }

  return mustHaves;
}
