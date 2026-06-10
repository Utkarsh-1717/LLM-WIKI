import json
import sys

notebook_path = "/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb"

print("=== Starting Notebook Validation ===")

try:
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    print("✅ Notebook is a valid JSON file.")
except Exception as e:
    print(f"❌ JSON Parsing failed: {e}")
    sys.exit(1)

# Syntax check all code cells
has_errors = False
code_cells = 0
for idx, cell in enumerate(nb.get("cells", [])):
    if cell.get("cell_type") == "code":
        code_cells += 1
        cell_id = cell.get("id", f"index_{idx}")
        source_code = "".join(cell.get("source", []))
        try:
            compile(source_code, f"Cell_{cell_id}", "exec")
        except SyntaxError as e:
            print(f"❌ Syntax Error in code cell {cell_id}:")
            print(f"   Line {e.lineno}: {e.text.strip() if e.text else ''}")
            print(f"   {e.msg}")
            has_errors = True
        except Exception as e:
            print(f"❌ Unexpected compile error in code cell {cell_id}: {e}")
            has_errors = True

if has_errors:
    print("❌ Notebook validation failed due to syntax errors.")
    sys.exit(1)
else:
    print(f"✅ Notebook validation passed. Checked {code_cells} code cells. All compiled successfully.")
