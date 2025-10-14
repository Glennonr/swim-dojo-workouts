"""
Swim Dojo Workout Scraper and HTML Table Generator
--------------------------------------------------

Fetches the Swim Dojo archive page, extracts workout names, categories, and URLs,
then generates:
  - workouts_by_category.json : structured data
  - workouts_table.html        : interactive table view with filters
  - total_distance_cache.json : caches total distances per workout to avoid repeated page requests
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
OUTPUT_JSON = Path("workouts_by_category.json")
OUTPUT_HTML = Path("workouts_table.html")
CACHE_JSON = Path("total_distance_cache.json")


# --------------------------------------------------------------------------- #
# Data Retrieval and Parsing
# --------------------------------------------------------------------------- #
def fetch_archive_html(url: str) -> BeautifulSoup:
    """Retrieve and parse the Swim Dojo archive page into a BeautifulSoup object."""
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        sys.exit(f"❌ Failed to retrieve {url}. Status code: {response.status_code}")
    return BeautifulSoup(response.text, "html.parser")


def extract_workouts_by_category(soup: BeautifulSoup) -> tuple[Dict[str, List[str]], Dict[str, str]]:
    """
    Extract workouts grouped by category and track each workout's link.

    Returns:
        by_category: dict of {category: [workout_names]}
        workout_links: dict of {workout_name: url}
    """
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


# --------------------------------------------------------------------------- #
# Total Distance Retrieval with Caching
# --------------------------------------------------------------------------- #
def load_cache() -> dict:
    if CACHE_JSON.exists():
        return json.loads(CACHE_JSON.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CACHE_JSON.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def fetch_workout_total(url: str, cache: dict, name: str) -> int | None:
    """Fetch the workout page and extract total distance if available, using cache."""
    if name in cache:
        return cache[name]
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # Look for <p> tags containing 'TOTAL:'
        total_distance = None
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if "TOTAL:" in text.upper():
                # Extract the first number found
                digits = "".join(c for c in text if c.isdigit())
                if digits:
                    total_distance = int(digits)
                    cache[name] = total_distance
                    return total_distance
        return None
    except Exception:
        return None



# --------------------------------------------------------------------------- #
# Data Transformation
# --------------------------------------------------------------------------- #
def invert_category_mapping(by_category: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Convert {category: [workouts]} → {workout: [categories]}."""
    by_workout = defaultdict(set)
    for category, workouts in by_category.items():
        for workout in workouts:
            by_workout[workout].add(category)
    return {w: sorted(cats) for w, cats in by_workout.items()}


def merge_workout_data(by_workout: Dict[str, List[str]], links: Dict[str, str], cache: dict) -> Dict[str, dict]:
    """Attach URLs, category columns, and total distance to each workout’s data."""
    data = {}
    for name, cats in by_workout.items():
        url = links.get(name)
        total_distance = fetch_workout_total(url, cache, name) if url else None
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
        }
    return data


# --------------------------------------------------------------------------- #
# HTML Generation
# --------------------------------------------------------------------------- #
def categorize_filters(categories: List[str]) -> Dict[str, List[str]]:
    """Group categories into logical sections."""
    distance = [c for c in categories if any(x in c for x in ("-", "+"))]
    difficulty_order = ["Beginner", "Intermediate", "Advanced", "Hard", "Insane"]
    difficulty = [c for c in difficulty_order if c in categories]
    stroke = [c for c in categories if c in ("Freestyle", "Backstroke", "Breaststroke", "Butterfly", "IM", "Stroke")]
    other = [c for c in categories if c not in distance + difficulty + stroke]
    return {
        "Distance": distance,
        "Difficulty": difficulty,
        "Stroke": stroke,
        "Other": sorted(other),
    }


def build_html(data: Dict[str, dict]) -> str:
    """Create an HTML table page with grouped category filters."""
    all_categories = sorted({c for v in data.values() for c in v["Distance"] + v["Difficulty"] + v["Stroke"] + v["Other"]})
    grouped = categorize_filters(all_categories)

    # Build filters by section
    filters_html = ""
    for section, cats in grouped.items():
        if not cats:
            continue
        filters_html += f"<h3>{section}</h3>\n"
        for c in cats:
            filters_html += (
                f'<label class="category-filter">'
                f'<input type="checkbox" value="{c}" onchange="filter()"> {c}</label>\n'
            )

    # Build table rows
    rows_html = ""
    for name, info in sorted(data.items()):
        link = info["url"]
        link_html = f'<a href="{link}" target="_blank">{name}</a>' if link else name
        distance = ", ".join(info["Distance"])
        difficulty = ", ".join(info["Difficulty"])
        stroke = ", ".join(info["Stroke"])
        other = ", ".join(info["Other"])
        total_distance = info["TotalDistance"] if info["TotalDistance"] is not None else ""
        rows_html += (
            f"<tr>"
            f"<td>{link_html}</td>"
            f"<td>{distance}</td>"
            f"<td>{difficulty}</td>"
            f"<td>{stroke}</td>"
            f"<td>{other}</td>"
            f"<td>{total_distance}</td>"
            f"</tr>\n"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Swim Workouts</title>
<style>
body {{ font-family: sans-serif; margin: 20px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 6px; text-align: left; }}
th {{ background: #f5f5f5; }}
.category-filter {{ margin: 5px; }}
.hidden {{ display: none; }}
a {{ color: #0073e6; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h2>Swim Workouts</h2>
<div id="filters">
  <strong>Filter by category:</strong><br>
  {filters_html}
</div>
<table id="workouts">
  <thead>
    <tr>
      <th>Workout</th>
      <th>Distance</th>
      <th>Difficulty</th>
      <th>Stroke</th>
      <th>Other</th>
      <th>Total Distance</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
<script>
function filter() {{
  const selected = [...document.querySelectorAll('#filters input:checked')].map(c => c.value);
  const rows = document.querySelectorAll('#workouts tbody tr');
  rows.forEach(r => {{
    const cats = [
        r.cells[1].innerText,
        r.cells[2].innerText,
        r.cells[3].innerText,
        r.cells[4].innerText
    ].join(',').split(',').map(c => c.trim()).filter(Boolean);
    const match = selected.every(s => cats.includes(s));
    r.classList.toggle('hidden', selected.length && !match);
  }});
}}
</script>
</body>
</html>"""


# --------------------------------------------------------------------------- #
# Main Entry
# --------------------------------------------------------------------------- #
def main() -> None:
    """Main entry point."""
    print("Starting")
    cache = load_cache()
    print("Cache Loaded")
    soup = fetch_archive_html(ARCHIVE_URL)
    print("Archive Fetched")
    by_category, workout_links = extract_workouts_by_category(soup)
    print("extracted workouts by category")
    by_workout = invert_category_mapping(by_category)
    print("inverted category mapping")

    full_data = merge_workout_data(by_workout, workout_links, cache)
    print("merged workout data")
    save_cache(cache)
    print("Saved cache")
    
    OUTPUT_JSON.write_text(json.dumps(full_data, indent=2), encoding="utf-8")
    OUTPUT_HTML.write_text(build_html(full_data), encoding="utf-8")

    print("✅ Generated:")
    print(f" - {OUTPUT_JSON.resolve()}")
    print(f" - {OUTPUT_HTML.resolve()}")
    print(f" - {CACHE_JSON.resolve()}")


if __name__ == "__main__":
    main()
