"""
Swim Dojo Workout Scraper (JSON Only, with Summary from workouts.json)
----------------------------------------------------------------------

Generates:
  - workouts_by_category.json (with summary field)
  - total_distance_cache.json
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.swimdojo.com"
ARCHIVE_URL = f"{BASE_URL}/archive"
WORKOUTS_JSON = Path("workouts.json")  # source of summaries
OUTPUT_JSON = Path("workouts_by_category.json")
CACHE_JSON = Path("total_distance_cache.json")


# -------------------- Data Retrieval -------------------- #
def fetch_archive_html(url: str) -> BeautifulSoup:
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        sys.exit(f"❌ Failed to retrieve {url}. Status code: {response.status_code}")
    return BeautifulSoup(response.text, "html.parser")


def extract_workouts_by_category(soup: BeautifulSoup) -> tuple[Dict[str, List[str]], Dict[str, str]]:
    by_category: Dict[str, List[str]] = {}
    workout_links: Dict[str, str] = {}

    for group in soup.select("li.archive-group"):
        category_tag = group.select_one(".archive-group-name-link")
        if not category_tag:
            continue

        category = category_tag.get_text(strip=True)
        workouts: List[str] = []

        for anchor in group.select(".archive-item a.archive-item-link"):
            name = anchor.get_text(strip=True)
            href = anchor.get("href")
            if href and href.startswith("/"):
                href = f"{BASE_URL}{href}"
            if name:
                workouts.append(name)
                workout_links[name] = href

        by_category[category] = workouts

    return by_category, workout_links


# -------------------- Cache -------------------- #
def load_cache() -> dict:
    if CACHE_JSON.exists():
        raw_cache = json.loads(CACHE_JSON.read_text(encoding="utf-8"))
        # Convert old int-only format to dict format
        fixed_cache = {}
        for k, v in raw_cache.items():
            if isinstance(v, dict):
                fixed_cache[k] = v
            else:
                fixed_cache[k] = {"TotalDistance": v, "Summary": ""}
        return fixed_cache
    return {}


def save_cache(cache: dict) -> None:
    CACHE_JSON.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def fetch_workout_total(url: str, cache: dict, name: str) -> int | None:
    """Fetch total distance from workout page, cached"""
    if name in cache and "TotalDistance" in cache[name]:
        return cache[name]["TotalDistance"]
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        total_distance = None
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if "TOTAL:" in text.upper():
                digits = "".join(c for c in text if c.isdigit())
                if digits:
                    total_distance = int(digits)
                    if name not in cache:
                        cache[name] = {}
                    cache[name]["TotalDistance"] = total_distance
                    return total_distance
        return None
    except Exception:
        return None


# -------------------- Data Transformation -------------------- #
def invert_category_mapping(by_category: Dict[str, List[str]]) -> Dict[str, List[str]]:
    by_workout = defaultdict(set)
    for category, workouts in by_category.items():
        for workout in workouts:
            by_workout[workout].add(category)
    return {w: sorted(cats) for w, cats in by_workout.items()}


def merge_workout_data(by_workout: Dict[str, List[str]], links: Dict[str, str], cache: dict, summaries: dict) -> Dict[str, dict]:
    data = {}
    for name, cats in by_workout.items():
        url = links.get(name)
        total_distance = fetch_workout_total(url, cache, name) if url else None
        summary = summaries.get(name, "")
        data[name] = {
            "Distance": [c for c in cats if any(x in c for x in ("-", "+"))],
            "Difficulty": [c for c in cats if c in ("Beginner", "Intermediate", "Advanced", "Hard", "Insane")],
            "Stroke": [c for c in cats if c in ("Freestyle", "Backstroke", "Breaststroke", "Butterfly", "IM", "Stroke")],
            "Other": [c for c in cats if c not in (
                "Beginner", "Intermediate", "Advanced", "Hard", "Insane",
                "Freestyle", "Backstroke", "Breaststroke", "Butterfly", "IM", "Stroke"
            ) and not any(x in c for x in ("-", "+"))],
            "url": url,
            "TotalDistance": total_distance,
            "summary": summary,
        }
    return data


# -------------------- Main -------------------- #
def main():
    print("Starting JSON generation...")
    cache = load_cache()
    print("Cache loaded")
    
    # Load summaries from workouts.json
    raw_workouts = json.loads(WORKOUTS_JSON.read_text(encoding="utf-8"))
    summaries = {w["title"]: w.get("summary", "") for w in raw_workouts}
    
    soup = fetch_archive_html(ARCHIVE_URL)
    print("Archive fetched")
    
    by_category, workout_links = extract_workouts_by_category(soup)
    by_workout = invert_category_mapping(by_category)
    
    full_data = merge_workout_data(by_workout, workout_links, cache, summaries)
    
    save_cache(cache)
    OUTPUT_JSON.write_text(json.dumps(full_data, indent=2), encoding="utf-8")
    
    print("✅ JSON files generated with summaries:")
    print(f" - {OUTPUT_JSON.resolve()}")
    print(f" - {CACHE_JSON.resolve()}")


if __name__ == "__main__":
    main()
