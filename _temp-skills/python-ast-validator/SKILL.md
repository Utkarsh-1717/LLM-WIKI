---
type: temp-skill
created: 2026-06-04
name: python-ast-validator
trigger: [validate python, check syntax, ast parse, check notebook code]
description: A method to programmatically validate the Python syntax of generated code or Jupyter Notebook cells without actually executing them.
use_count: 1
last_used: 2026-06-04
---
type: temp-skill
created: 2026-06-04

## Description
When programmatically generating Python code or building Jupyter Notebooks (`.ipynb`), string replacement errors or indentation bugs can easily create invalid Python syntax that will crash at runtime.

To prevent pushing broken code (especially to remote environments like Kaggle), validate the syntax locally using the built-in `ast` (Abstract Syntax Tree) module.

## Boilerplate Code

### For standard `.py` files:
```bash
python3 -c "import ast; ast.parse(open('script.py').read()); print('✅ Code parses cleanly')"
```

### For Jupyter Notebooks (`.ipynb`):
```bash
python3 -c "
import json, ast
nb = json.load(open('notebook.ipynb'))
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        src = ''.join(cell['source'])
        try:
            ast.parse(src)
        except SyntaxError as e:
            print(f'❌ SyntaxError in cell {i}: {e}')
            exit(1)
print('✅ All code cells parse cleanly')
"
```

## Rules
1. **Run before push**: Always run the AST validator before pushing a dynamically generated notebook to Kaggle or committing code to a critical repository.
2. **Fail Fast**: If `ast.parse()` throws a `SyntaxError`, the script will exit with a non-zero status code, correctly failing the CI/CD or agent tool call pipeline immediately.
