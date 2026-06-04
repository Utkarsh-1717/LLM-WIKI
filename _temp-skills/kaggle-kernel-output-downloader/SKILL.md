---
type: temp-skill
created: 2026-06-04
name: kaggle-kernel-output-downloader
trigger: [download kaggle output, fetch kernel results, get notebook output]
description: A method to directly download the output files of a Kaggle kernel without needing it to be published as a dataset.
use_count: 1
last_used: 2026-06-04
---
type: temp-skill
created: 2026-06-04

## Description
When running Kaggle notebooks, sometimes the output files (CSVs, logs, models) are saved in the `/kaggle/working` directory but are not published as a formal Kaggle Dataset.

To retrieve these raw output files locally, use the `kaggle kernels output` command instead of `kaggle datasets download`.

## Boilerplate Command

```bash
set -a && source ~/.quant_env && set +a && kaggle kernels output <username>/<kernel-slug> -p <local-destination-path> --force
```

### Example

```bash
set -a && source ~/.quant_env && set +a && kaggle kernels output utkarshpatelthefirst/stage3-pairs-backtest -p /storage/emulated/0/Quant/LLM-WIKI/Raw/Sources/attachments/ --force
```

## Rules
1. **Always use `--force`**: This ensures that any existing files in the local directory with the same name are overwritten by the fresh outputs.
2. **Environment Variables**: Always wrap the command with `set -a && source ~/.quant_env && set +a` to ensure the Kaggle credentials are loaded before execution.
3. **Target Directory**: Download directly into `Raw/Sources/attachments/` if the files are meant to be ingested into the LLM-WIKI.
