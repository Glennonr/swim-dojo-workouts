import json

# load your by_workout dict from previous step
with open("workouts_by_category.json") as f:
    data = json.load(f)

categories = sorted({c for cats in data.values() for c in cats})

html = f"""
<!DOCTYPE html>
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
</style>
</head>
<body>

<h2>Swim Workouts</h2>

<div id="filters">
  <strong>Filter by category:</strong><br>
  {''.join(f'<label class="category-filter"><input type="checkbox" value="{c}" onchange="filter()"> {c}</label>' for c in categories)}
</div>

<table id="workouts">
  <thead>
    <tr><th>Workout</th><th>Categories</th></tr>
  </thead>
  <tbody>
"""
for w, cats in sorted(data.items()):
    html += f"<tr><td>{w}</td><td>{', '.join(cats)}</td></tr>\n"

html += """
  </tbody>
</table>

<script>
function filter() {
  const selected = [...document.querySelectorAll('#filters input:checked')].map(c => c.value);
  const rows = document.querySelectorAll('#workouts tbody tr');
  rows.forEach(r => {
    const cats = r.cells[1].innerText.split(',').map(c => c.trim());
    const match = selected.every(s => cats.includes(s));
    r.classList.toggle('hidden', selected.length && !match);
  });
}
</script>

</body></html>
"""

with open("workouts_table.html", "w", encoding="utf-8") as f:
    f.write(html)
print("✅ Generated workouts_table.html — open it in a browser.")
