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
