# Wiki Multi-Format Ingest Extension v1.0.0

> Give this file to agy to extend the existing LLM Wiki with multi-format
> source ingestion. Builds on top of the existing wiki system.
> Follow steps 00 → 03 in order. Stop when ACCEPTANCE CRITERIA passes.

---

## CONTEXT

Extends Raw/Sources/ to accept and auto-convert these formats:
.py | .pdf | .ipynb | .jpg | .png | .csv | .json | .xlsx

Every file dropped into Raw/Sources/attachments/ gets:
1. Auto-scanned and detected
2. Converted to a .md summary in Raw/Sources/
3. Compiled into Wiki/ notes as normal
4. Tracked in source-manifest.jsonl with format field
5. Original file preserved in attachments/ always

---

## SETUP ORDER

---

## Step 00 — Create Attachments Folder

Run:
```
mkdir -p Raw/Sources/attachments
```

Create Raw/Sources/attachments/.gitkeep so folder is tracked by git.

Create Raw/Sources/attachments/README.md:

```markdown
# Attachments

Drop any file here for wiki ingestion:
.py .pdf .ipynb .jpg .png .csv .json .xlsx

agy will auto-detect and convert to wiki source notes.
Original files are never modified or deleted.
```

Commit: `multiformat-00-attachments-folder`

---

## Step 01 — Update scripts/wiki_tool.py

Open scripts/wiki_tool.py and make these exact changes:

### 01-A: Add format field to source-scan

Find the source-scan command. Update it to also scan
Raw/Sources/attachments/ for these extensions:
.py .pdf .ipynb .jpg .png .csv .json .xlsx

For each file found in attachments/, check if a corresponding
.md summary already exists in Raw/Sources/ with same base name.

Add field to source-scan JSON output:
```
{
  "path": "Raw/Sources/attachments/file.py",
  "format": "python",
  "has_md_summary": true or false,
  "md_summary_path": "Raw/Sources/file-py.md" or null,
  "processed": true or false
}
```

### 01-B: Add new command: attachment-scan

Add command attachment-scan to wiki_tool.py:

```python
def cmd_attachment_scan():
    """Scan Raw/Sources/attachments/ and report all files needing md summaries."""
    attachments = Path("Raw/Sources/attachments")
    SUPPORTED = {
        ".py": "python",
        ".pdf": "pdf",
        ".ipynb": "notebook",
        ".jpg": "image",
        ".png": "image",
        ".csv": "csv",
        ".json": "json",
        ".xlsx": "spreadsheet"
    }
    results = []
    for f in sorted(attachments.iterdir()):
        if f.suffix.lower() not in SUPPORTED:
            continue
        if f.name.startswith("."):
            continue
        md_name = f.stem.lower().replace(" ", "-").replace("_", "-") + "-" + f.suffix[1:] + ".md"
        md_path = Path("Raw/Sources") / md_name
        results.append({
            "file": str(f),
            "format": SUPPORTED[f.suffix.lower()],
            "needs_summary": not md_path.exists(),
            "md_target": str(md_path)
        })
    for r in results:
        status = "❌ NEEDS SUMMARY" if r["needs_summary"] else "✅ has summary"
        print(f"{status} | {r['format']:<12} | {r['file']}")
    pending = sum(1 for r in results if r["needs_summary"])
    print(f"\nTotal attachments: {len(results)} | Pending summaries: {pending}")
```

### 01-C: Update source-manifest.jsonl schema

Update any manifest-writing code to include format field.
If format field missing from existing entries, default to "markdown".

Run after changes:
```
python3 scripts/wiki_tool.py doctor
python3 scripts/wiki_tool.py lint
python3 scripts/wiki_tool.py attachment-scan
```

All must pass without errors.

Commit: `multiformat-01-wiki-tool-updated`

---

## Step 02 — Create Multi-Format Ingest Skill

Create file: .agents/skills/multi-format-ingest/SKILL.md

```markdown
---
name: multi-format-ingest
trigger: [ingest file, ingest pdf, ingest notebook, ingest image, ingest csv,
          ingest python, ingest script, ingest xlsx, ingest json, scan attachments,
          process attachments, new file in attachments]
description: Converts any supported file in Raw/Sources/attachments/ into a wiki source note
---

## Rules

### General Rules (apply to ALL formats)

1. Always preserve original file in Raw/Sources/attachments/ — never move or delete it
2. Output .md file naming: [original-name]-[ext].md
   Example: qt.py → Raw/Sources/qt-py.md
   Example: strategy.pdf → Raw/Sources/strategy-pdf.md
3. Every generated .md file MUST have this frontmatter:
   ---
   title: [descriptive title]
   format: [python|pdf|notebook|image|csv|json|spreadsheet]
   source_file: Raw/Sources/attachments/[filename]
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   tags: [inferred topic tags]
   sources: [Raw/Sources/attachments/filename]
   source_count: 1
   ---
4. After creating .md file: run python3 scripts/wiki_tool.py lint
5. Fix any lint errors before proceeding

---

### Format-Specific Rules

#### .py — Python Script

Extract in this order — structured sections:

**Section 1 — Overview**
- Script name and purpose (from module docstring or first comment block)
- Key dependencies (imports)
- Entry point if any

**Section 2 — Function Inventory**
For each function/class/method:
- Name
- Signature (parameters + types if annotated)
- Docstring or inferred purpose from code
- Inputs and outputs

**Section 3 — Core Logic Summary**
Plain English explanation of what the script does end-to-end.
No code. Just logic flow.

**Section 4 — Data Flow**
What data enters → what transformations happen → what data exits.

**Section 5 — Usage**
How to run this script. Any required environment variables or credentials.

**Section 6 — Connections**
Any APIs, databases, external services this script uses.

---

#### .pdf — PDF Document

Extract in this order:

**Section 1 — Document Summary**
Title, authors if present, date, source URL if found.
One paragraph summary of entire document.

**Section 2 — Key Concepts**
Bullet list of main concepts, terms, and definitions found.

**Section 3 — Methodology**
If technical/research paper: extract methodology, formulas (write in LaTeX), results.

**Section 4 — Key Findings**
Most important conclusions or data points.

**Section 5 — Relevance**
How this connects to quantitative trading or existing wiki topics.

---

#### .ipynb — Jupyter Notebook

Extract in this order:

**Section 1 — Notebook Purpose**
What this notebook does. Infer from title and first markdown cells.

**Section 2 — Stage Summary**
For each markdown cell found: extract heading and summary.
For each code cell found: extract what it computes (not full code).

**Section 3 — Strategy/Logic Extracted**
If notebook contains a trading strategy: extract entry/exit rules, parameters.

**Section 4 — Results Found**
Any metrics, charts described, or output tables found in output cells.

**Section 5 — Dependencies**
All imports found. Any data files or APIs used.

---

#### .jpg / .png — Image

Extract in this order:

**Section 1 — Image Description**
What is shown in the image. Be specific and precise.

**Section 2 — Data/Information Extracted**
If chart: extract axes, values, trend, time period.
If screenshot: extract text content and UI elements.
If diagram: extract relationships and flow shown.

**Section 3 — Interpretation**
What this image means in context of quantitative trading.

**Section 4 — Key Numbers**
Any specific numbers, percentages, dates visible.

---

#### .csv — Data File

Extract in this order:

**Section 1 — Dataset Overview**
Filename. Inferred purpose. Row count. Column count.

**Section 2 — Schema**
For each column: name, inferred data type, sample values, likely meaning.

**Section 3 — Date Range**
If timestamp/date column found: min date, max date, frequency.

**Section 4 — Data Quality Notes**
Any nulls, anomalies, or gaps visible from first/last rows.

**Section 5 — Potential Uses**
How this dataset could be used in backtesting or analysis.

---

#### .json — JSON File

Extract in this order:

**Section 1 — Structure Overview**
Top-level keys. Nested depth. Array lengths if any.

**Section 2 — Content Summary**
What data this JSON contains. Inferred purpose.

**Section 3 — Key Fields**
Most important fields and their meanings.

---

#### .xlsx — Spreadsheet

Extract in this order:

**Section 1 — Workbook Overview**
Sheet names. Purpose of each sheet.

**Section 2 — Per-Sheet Summary**
For each sheet: column headers, row count, data type, purpose.

**Section 3 — Key Data**
Most important tables or values found.

---

## Batch Mode

If user says "process all attachments" or "scan and ingest all":
1. Run python3 scripts/wiki_tool.py attachment-scan
2. For every file showing NEEDS SUMMARY: process it using rules above
3. Report: files processed, files skipped, any errors
```

Commit: `multiformat-02-ingest-skill`

---

## Step 03 — Final Verification

Run full maintenance gate:
```
python3 scripts/wiki_tool.py doctor
python3 scripts/wiki_tool.py build
python3 scripts/wiki_tool.py lint
python3 scripts/wiki_tool.py source-lint
python3 scripts/wiki_tool.py attachment-scan
python3 scripts/audit_public.py
```

All must pass with zero errors.

Push:
```
git add -A
git commit -m "multiformat-03-complete"
git push origin main
```

---

## ACCEPTANCE CRITERIA

- [ ] Raw/Sources/attachments/ folder exists with README.md
- [ ] wiki_tool.py attachment-scan command works without error
- [ ] wiki_tool.py source-scan includes format field in output
- [ ] .agents/skills/multi-format-ingest/SKILL.md exists
- [ ] Skill covers all 8 formats: .py .pdf .ipynb .jpg .png .csv .json .xlsx
- [ ] Skill has general rules + format-specific rules sections
- [ ] Skill has batch mode rule
- [ ] doctor, lint, source-lint all pass
- [ ] audit_public.py passes
- [ ] Pushed to origin main

---

## USER WORKFLOW AFTER SETUP

Drop any file:
```bash
cp ~/storage/shared/Download/strategy.pdf \
   ~/storage/shared/Quant/LLM-WIKI/Raw/Sources/attachments/
```

Then in agy:

Single file:
```
Ingest Raw/Sources/attachments/strategy.pdf
```

All pending files at once:
```
Process all attachments
```

Check what needs processing:
```bash
python3 scripts/wiki_tool.py attachment-scan
```

---

*quant-wiki-multiformat-v1.0.0 — extends quant-agent-setup-v1.0.0*
