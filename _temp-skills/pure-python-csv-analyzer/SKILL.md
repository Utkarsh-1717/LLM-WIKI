---
type: temp-skill
created: 2026-06-04
name: pure-python-csv-analyzer
trigger: [analyze csv without pandas, read csv, pure python csv]
description: A method for loading and analyzing large CSV files in constrained environments where Pandas is not available.
use_count: 1
last_used: 2026-06-04
---
type: temp-skill
created: 2026-06-04

## Description
In highly constrained terminal environments (like Termux without global site-packages), the `pandas` library is often unavailable. Attempting to run python scripts that `import pandas as pd` will immediately fail with `ModuleNotFoundError`.

This skill provides a pure-python boilerplate using the standard library `csv` module to accomplish the most common Pandas tasks: reading, filtering, finding max/min, and summing columns.

## Boilerplate Code

```python
import csv

# 1. Load CSV into memory as a list of dictionaries
with open("data.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# 2. Iterate and sum/average columns
total_value = sum(float(r.get("column_name", 0) or 0) for r in rows)

# 3. Find row with max value
best_row = max(rows, key=lambda r: float(r.get("profit_column", -float('inf')) or -float('inf')))

# 4. Filter rows
filtered_rows = [r for r in rows if float(r.get("status_code", 0) or 0) == 200]

# 5. Formatted Printing (Pandas df.head() equivalent)
cols_to_print = ["col_a", "col_b", "col_c"]
header = "".join(f"{c:>15}" for c in cols_to_print)
print(header)
for row in rows[:10]:
    line = "".join(f"{str(row.get(c, ''))[:14]:>15}" for c in cols_to_print)
    print(line)
```
