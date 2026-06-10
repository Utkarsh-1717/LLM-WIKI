import json
import sys
import py_compile

notebook_path = '/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb'
output_script_path = '/storage/emulated/0/Quant/LLM-WIKI/.agents/teamwork_preview_reviewer_code_audit_2_1/temp_compiled_soul.py'

print(f"Reading notebook from: {notebook_path}")
with open(notebook_path, 'r', encoding='utf-8') as f:
    try:
        nb = json.load(f)
        print("✅ Notebook is a valid JSON file.")
    except Exception as e:
        print(f"❌ Notebook JSON validation failed: {e}")
        sys.exit(1)

# Extract code cells
code_cells = []
for idx, cell in enumerate(nb.get('cells', [])):
    if cell.get('cell_type') == 'code':
        source_lines = cell.get('source', [])
        source = "".join(source_lines)
        code_cells.append(f"# --- CELL {idx} (ID: {cell.get('id', 'N/A')}) ---\n{source}")

full_code = "\n\n".join(code_cells)

print(f"Writing compiled code to: {output_script_path}")
with open(output_script_path, 'w', encoding='utf-8') as f:
    f.write(full_code)

print("Compiling Python script...")
try:
    py_compile.compile(output_script_path, doraise=True)
    print("✅ Python syntax validation passed successfully! No syntax errors found.")
except py_compile.PyCompileError as e:
    print(f"❌ Python syntax validation failed:")
    print(e)
    sys.exit(1)
