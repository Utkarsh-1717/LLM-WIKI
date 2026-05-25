---
name: kaggle-db-update
trigger: [upload to Kaggle, update database, store on Kaggle, push dataset]
description: Uploads or updates SQLite database as a Kaggle dataset
---

## Rules

1. Dataset name: quant-stock-db (always use this name)
2. If dataset does not exist: create with kaggle datasets create
3. If dataset exists: push new version — version note: "update-YYYY-MM-DD"
4. After successful upload:
   - Record in Wiki at Raw/Sources/kaggle-datasets.md:
     dataset_url, last_updated date, tables included, row counts
5. Single-threaded upload — HARDWARE CONSTRAINT
6. Verify upload by pulling dataset metadata after push
7. Report: dataset URL, version number, file size uploaded
