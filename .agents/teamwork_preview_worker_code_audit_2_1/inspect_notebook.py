import json

notebook_path = "/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb"

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

target_ids = ["e9cf67b2", "ca17c2f1", "c138afc1"]

for cell in nb.get("cells", []):
    cell_id = cell.get("id")
    if cell_id in target_ids:
        print(f"=== Cell ID: {cell_id} ===")
        print("".join(cell.get("source", [])))
        print("\n" + "="*40 + "\n")
