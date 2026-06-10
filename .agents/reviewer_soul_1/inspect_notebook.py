import json
import os

notebook_path = "/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb"
output_path = "/storage/emulated/0/Quant/LLM-WIKI/.agents/reviewer_soul_1/notebook_dump.md"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

cells = nb.get('cells', [])
dump_lines = []

dump_lines.append(f"# Notebook Dump of `{os.path.basename(notebook_path)}`")
dump_lines.append(f"Total cells: {len(cells)}")
dump_lines.append("")

for idx, cell in enumerate(cells):
    cell_type = cell.get('cell_type', 'unknown')
    cell_id = cell.get('id', 'NONE')
    source = cell.get('source', [])
    if isinstance(source, list):
        source_str = "".join(source)
    else:
        source_str = str(source)
        
    dump_lines.append(f"## Cell {idx} ({cell_type}) - ID: `{cell_id}`")
    dump_lines.append("")
    if cell_type == 'code':
        dump_lines.append("```python")
        dump_lines.append(source_str)
        dump_lines.append("```")
    else:
        dump_lines.append(source_str)
    dump_lines.append("\n---\n")

with open(output_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(dump_lines))

print(f"Dumped {len(cells)} cells to {output_path}")

# Check v4.5+ cell IDs
invalid_ids = []
id_set = set()
for idx, cell in enumerate(cells):
    cell_id = cell.get('id', None)
    if cell_id is None:
        invalid_ids.append(f"Cell {idx}: No ID")
    elif len(cell_id) != 8:
        invalid_ids.append(f"Cell {idx}: ID '{cell_id}' length is {len(cell_id)} (expected 8)")
    elif cell_id in id_set:
        invalid_ids.append(f"Cell {idx}: ID '{cell_id}' is a duplicate")
    else:
        id_set.add(cell_id)

if invalid_ids:
    print("Invalid/Missing cell IDs found:")
    for err in invalid_ids:
        print(f"  - {err}")
else:
    print("All cell IDs are valid and unique (8-character strings).")
