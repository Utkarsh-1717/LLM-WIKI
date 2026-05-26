---
name: kaggle-db-update
trigger: [upload to Kaggle, update database, store on Kaggle, push dataset, new version dataset]
description: Publishes or updates a SQLite database as a Kaggle dataset, entirely from within a Kaggle notebook. Never downloads files locally.
version: 2.0.0
last_updated: 2026-05-26
---

# Kaggle DB Update Skill

## CRITICAL RULES

1. **Never download large output files locally** — all publishing happens inside the Kaggle notebook using the Kaggle Python API.
2. **Prefer doing this inside the same notebook that generated the data** — see `kaggle-notebook-run` skill.
3. Hardcode Kaggle credentials directly inside the notebook — no credential files on Kaggle.

## Publishing a NEW Dataset (First Time)

```python
import os, json, shutil
from kaggle.api.kaggle_api_extended import KaggleApi

os.environ['KAGGLE_USERNAME'] = 'utkarshpatelthefirst'
os.environ['KAGGLE_KEY']     = 'fbef16329099428205f671dd5de8337b'

api = KaggleApi()
api.authenticate()

export_dir = '/kaggle/working/dataset_export'
os.makedirs(export_dir, exist_ok=True)

# Copy the target file into the export directory
shutil.copy('/kaggle/working/MyData.sqlite', f'{export_dir}/MyData.sqlite')

# Initialize and customize metadata
api.dataset_initialize(export_dir)
with open(f'{export_dir}/dataset-metadata.json') as f:
    meta = json.load(f)

meta['title']    = 'My-Dataset-Title'          # Human-readable name
meta['id']       = 'utkarshpatelthefirst/my-dataset-slug'  # URL slug
meta['licenses'] = [{'name': 'CC0-1.0'}]

with open(f'{export_dir}/dataset-metadata.json', 'w') as f:
    json.dump(meta, f, indent=2)

api.dataset_create_new(export_dir, dir_mode='zip', quiet=False)
print("✅ New dataset created!")
```

## Updating an EXISTING Dataset (New Version)

```python
api.dataset_create_version(
    export_dir,
    version_notes=f"update-{datetime.now().strftime('%Y-%m-%d')}",
    dir_mode='zip',
    quiet=False
)
print("✅ New version uploaded!")
```

## Verifying Publication (No Local Download)

Check via the API without downloading anything:
```python
datasets = api.dataset_list(user='utkarshpatelthefirst')
for d in datasets:
    size_mb = d._total_bytes / (1024*1024)
    print(f"{d._ref} | {d._title} | {size_mb:.1f} MB | updated: {d._last_updated}")
```

## After Publishing

Record in Wiki at `Wiki/Entities/<dataset-name>.md`:
- Dataset URL
- `_ref` slug (for future use in notebooks)
- Date published
- Tables included, row counts
- File size (compressed)

## Connections
- [[kaggle-notebook-run]]
- [[kaggle-pulse-check]]
- [[fyers-historical-kaggle]]
