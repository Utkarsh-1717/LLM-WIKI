import json
import sys

def ipynb_to_py(ipynb_path, py_path):
    with open(ipynb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    code_cells = []
    for cell in nb.get('cells', []):
        if cell.get('cell_type') == 'code':
            source = cell.get('source', [])
            if isinstance(source, list):
                code_cells.append("".join(source))
            else:
                code_cells.append(source)
    
    with open(py_path, 'w', encoding='utf-8') as f:
        f.write("\n\n# ##########################################\n# NEW CELL\n# ##########################################\n\n".join(code_cells))
    print(f"Converted {ipynb_path} -> {py_path}")

if __name__ == "__main__":
    ipynb_to_py("/storage/emulated/0/Quant/LLM-WIKI/Raw/Sources/attachments/stage1-pairs-pearson-correlation.ipynb", 
                "/storage/emulated/0/Quant/LLM-WIKI/.agents/teamwork_preview_explorer_fetch_1/stage1.py")
    ipynb_to_py("/storage/emulated/0/Quant/LLM-WIKI/Raw/Sources/attachments/stage2-pairs-kalman-ou.ipynb", 
                "/storage/emulated/0/Quant/LLM-WIKI/.agents/teamwork_preview_explorer_fetch_1/stage2.py")
