import json
from pathlib import Path

INPUT_JSON = Path("workouts_by_category.json")
OUTPUT_HTML = Path("index.html")


def categorize_filters(categories):
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


def build_html(data):
    all_categories = sorted({c for v in data.values() for c in v.get("Distance", []) + v.get("Difficulty", []) + v.get("Stroke", []) + v.get("Other", [])})
    grouped = categorize_filters(all_categories)

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

    rows_html = ""
    for name, info in sorted(data.items()):
        link = info.get("url")
        link_html = f'<a href="{link}" target="_blank">{name}</a>' if link else name
        distance = ", ".join(info.get("Distance", []))
        difficulty = ", ".join(info.get("Difficulty", []))
        stroke = ", ".join(info.get("Stroke", []))
        other = ", ".join(info.get("Other", []))
        total_distance = info.get("TotalDistance", "")
        summary_full = info.get("summary", "")
        if len(summary_full) > 150:
            summary_display = summary_full[:150] + "…"
            truncated_attr = 'data-truncated="true"'
        else:
            summary_display = summary_full
            truncated_attr = 'data-truncated="false"'
        rows_html += (
            f"<tr>"
            f"<td>{link_html}</td>"
            f"<td>{distance}</td>"
            f"<td>{difficulty}</td>"
            f"<td>{stroke}</td>"
            f"<td>{other}</td>"
            f"<td>{total_distance}</td>"
            f'<td class="summary" {truncated_attr} data-full="{summary_full}">{summary_display}</td>'
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
th, td {{ border: 1px solid #ccc; padding: 6px; text-align: left; vertical-align: top; }}
th {{ background: #f5f5f5; }}
.category-filter {{ display: inline-block; margin: 5px 10px 5px 0; font-size: 1.1em; }}
.category-filter input {{ transform: scale(1.5); margin-right: 8px; vertical-align: middle; }}
.hidden {{ display: none; }}
a {{ color: #0073e6; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

td.summary {{
  word-wrap: break-word;
  max-width: 400px;
  white-space: normal;
  position: relative;
  cursor: pointer;
}}

td.summary[data-truncated="true"]:hover::after {{
  content: attr(data-full);
  position: absolute;
  left: 0;
  top: 100%;
  background: #fff;
  border: 1px solid #ccc;
  padding: 8px;
  max-width: 400px;
  white-space: normal;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}}

.table-container {{ overflow-x: auto; }}

@media (max-width: 600px) {{
    #filters {{ display: flex; flex-direction: column; }}
    .category-filter {{ margin: 5px 0; }}
    table {{ display: block; width: 100%; }}
    th, td {{ white-space: normal; }}
}}
</style>
</head>
<body>
<h2>Swim Workouts</h2>
<div id="filters">
  <strong>Filter by category:</strong><br>
  {filters_html}
</div>

<div id="workout-count" style="margin:10px 0; font-weight:bold;">Total Workouts: {len(data)}</div>

<div class="table-container">
<table id="workouts">
  <thead>
    <tr>
      <th>Workout</th>
      <th>Distance</th>
      <th>Difficulty</th>
      <th>Stroke</th>
      <th>Other</th>
      <th>Total Distance</th>
      <th>Summary</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
</div>

<script>
function filter() {{
  const selected = [...document.querySelectorAll('#filters input:checked')].map(c => c.value);
  const rows = document.querySelectorAll('#workouts tbody tr');
  let visibleCount = 0;
  rows.forEach(r => {{
    const cats = [
        r.cells[1].innerText,
        r.cells[2].innerText,
        r.cells[3].innerText,
        r.cells[4].innerText
    ].join(',').split(',').map(c => c.trim()).filter(Boolean);
    const match = selected.every(s => cats.includes(s));
    const hidden = selected.length && !match;
    r.classList.toggle('hidden', hidden);
    if (!hidden) visibleCount += 1;
  }});
  document.getElementById("workout-count").innerText = "Total Workouts: " + visibleCount;
}}
</script>
</body>
</html>"""


def main():
    data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    OUTPUT_HTML.write_text(build_html(data), encoding="utf-8")
    print(f"✅ index.html regenerated from {INPUT_JSON}")


if __name__ == "__main__":
    main()
