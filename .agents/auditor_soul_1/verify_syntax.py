import json
import sys

def verify_notebook_syntax(ipynb_path):
    with open(ipynb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    code_cells = [cell for cell in nb.get('cells', []) if cell.get('cell_type') == 'code']
    print(f"Found {len(code_cells)} code cells in {ipynb_path}")
    
    success = True
    for idx, cell in enumerate(code_cells):
        source = "".join(cell.get('source', []))
        try:
            compile(source, f"cell_{idx}", "exec")
            print(f"  - Cell {idx}: Compiles successfully")
        except SyntaxError as e:
            print(f"  ❌ Cell {idx} failed compilation:")
            print(f"    Line {e.lineno}: {e.text.strip() if e.text else ''}")
            print(f"    {e.msg}")
            success = False
            
    if not success:
        sys.exit(1)
    print("All code cells compiled successfully!")

if __name__ == "__main__":
    verify_notebook_syntax("/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb")
