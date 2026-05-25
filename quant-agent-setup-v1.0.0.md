# Quant Agent System — Master Setup Guide v1.0.0

> Give this file to agy when you want it to build the complete Quant Agent System
> on top of an existing LLM Wiki vault. Follow the setup order exactly.
> Commit after each major step. Stop once ACCEPTANCE CRITERIA passes.

---

## CONTEXT

This guide builds a self-improving quant agentic system on Android (Termux + agy).
Heavy compute runs on Kaggle. Android is thin client only.
All credentials live in ~/.quant_env — never in committed files.

**Existing foundation (already complete):**
- LLM Wiki vault at /storage/emulated/0/Quant/LLM-WIKI
- agy v1.0.2 working
- Git connected to Utkarsh-1717/LLM-WIKI

---

## HARDWARE CONSTRAINTS (hardcode everywhere, never override)

Device: Realme GT 6T
Processor: Snapdragon 7+ Gen 3
RAM: 8GB physical — max 2GB for any Termux process
Storage: 128GB — alert user if free space below 5GB
Rule 1: NEVER use multiprocessing, ThreadPoolExecutor, or parallel jobs locally
Rule 2: NEVER run any local task expected to exceed 30 minutes
Rule 3: NEVER use GPU locally — no CUDA, no torch.cuda, no tensorflow-gpu
Rule 4: ALL heavy backtesting, parallel computation, large data processing → Kaggle only
Rule 5: Local scripts: single-threaded, memory-efficient pandas only, chunked reads
Rule 6: Sleep 0.5s between all API calls to avoid rate limits and bans

---

## SETUP ORDER

Execute steps 00 → 05 in exact order.
Do not skip steps. Commit after each step.

---

## Step 00 — Environment Bootstrap

### 00-A: Create credentials file

Create file at ~/.quant_env with exact contents:

```
FYERS_APP_ID=G0NX5M08ZG-100
FYERS_SECRET_KEY=D07VJ80FLH
FYERS_TOTP_KEY=4QXQQACGALLZNFISHC5G7WU76AERBNYC
FYERS_USERNAME=FAI84454
FYERS_PIN=7475
FYERS_REDIRECT=https://trade.fyers.in/api-login/redirect-uri/index.html
KAGGLE_USERNAME=utkarshpatelthefirst
KAGGLE_KEY=fbef16329099428205f671dd5de8337b
```

Set permissions: chmod 600 ~/.quant_env

Add to ~/.bashrc if not present:
```
source ~/.quant_env
```

### 00-B: Install required packages

Run in Termux:
```
pip install kaggle pyotp fyers-apiv3 requests --break-system-packages
```

Verify each package imports without error:
```
python3 -c "import kaggle, pyotp, fyers_apiv3, requests; print('OK')"
```

### 00-C: Configure Kaggle CLI

Run:
```
mkdir -p ~/.config/kaggle
echo '{"username":"utkarshpatelthefirst","key":"fbef16329099428205f671dd5de8337b"}' > ~/.config/kaggle/kaggle.json
chmod 600 ~/.config/kaggle/kaggle.json
kaggle datasets list --max-size 1
```

Expected: list of datasets without auth error.

### 00-D: Verification

- [ ] ~/.quant_env exists with chmod 600
- [ ] All packages import without error
- [ ] kaggle CLI responds without auth error
- [ ] ~/.bashrc sources ~/.quant_env

Commit: `setup-00-environment-bootstrap`

---

## Step 01 — Update AGENTS.md

Open existing AGENTS.md and append these two sections exactly.
Do not remove existing content.

```markdown
---

## HARDWARE CONSTRAINTS

Device: Realme GT 6T | Snapdragon 7+ Gen 3 | 8GB RAM | 128GB storage
These rules apply to EVERY task. No exceptions.

- Never use multiprocessing or parallel processing locally
- Never exceed 2GB RAM in any local script
- Never run any local task over 30 minutes
- Never use GPU locally
- All heavy compute → Kaggle only
- Single-threaded, chunked, memory-efficient code for all local scripts
- Sleep 0.5s between all external API calls
- Check free storage before any download — warn if below 5GB

---

## TOKEN EFFICIENCY RULES

- Load only the skill whose trigger keyword matches the current task
- Never load all skills simultaneously
- Never read entire Wiki on startup
- Read only files directly relevant to current task
- Credentials always from ~/.quant_env — never ask user for them
- After every completed task: check if a pattern was repeated 3+ times
  If yes → create a temp-skill automatically, do not ask user for permission
```

Commit: `setup-01-agents-updated`

---

## Step 02 — Core Fixed Skills

Create each file below exactly as specified.
Each SKILL.md must stay under 400 words — action rules only.

### 02-A: fyers-auth

Create file: .agents/skills/fyers-auth/SKILL.md

```markdown
---
name: fyers-auth
trigger: [fyers data, live feed, historical data, authenticate fyers, fyers token]
description: Authenticates with Fyers API using 5-step TOTP flow
---

## Rules

1. Source credentials from ~/.quant_env — never hardcode
2. Execute auth in exact order:
   - Step 1: POST https://api-t2.fyers.in/vagator/v2/send_login_otp — body: {fy_id, app_id:"2"}
   - Step 2: POST https://api-t2.fyers.in/vagator/v2/verify_otp — body: {request_key, otp: pyotp.TOTP(TOTP_KEY).now()}
   - Step 3: POST https://api-t2.fyers.in/vagator/v2/verify_pin — body: {request_key, identity_type:"pin", identifier:PIN}
   - Step 4: POST https://api-t1.fyers.in/api/v3/token — extract auth_code from response URL
   - Step 5: fyersModel.SessionModel — generate_token() → extract access_token
3. Return token as string: APP_ID:access_token
4. On any step failure: print exact error JSON, stop immediately, report to user
5. Never write token to any file
6. Token valid for current session only
```

### 02-B: fyers-historical

Create file: .agents/skills/fyers-historical/SKILL.md

```markdown
---
name: fyers-historical
trigger: [download historical, fetch 1-min, OHLCV, historical data, stock database]
description: Downloads historical 1-min OHLCV data via Fyers REST API into SQLite
---

## Rules

1. Always execute fyers-auth skill first to get token
2. API endpoint: GET https://api-t1.fyers.in/api/v3/data/history
   Params: symbol, resolution:"1", date_format:1, range_from, range_to, cont_flag:1
3. Chunk requests: max 100 days per call — loop until full range covered
4. Sleep 0.5s between every API call — no exceptions
5. Output: SQLite database
   - Table: ohlcv_1min
   - Columns: id INTEGER PRIMARY KEY, symbol TEXT, timestamp INTEGER,
     open REAL, high REAL, low REAL, close REAL, volume INTEGER
   - Index on (symbol, timestamp)
   - PRAGMA journal_mode=DELETE (Android compatibility)
   - PRAGMA synchronous=NORMAL
6. Single-threaded only — HARDWARE CONSTRAINT
7. On completion report: symbol, date range, total rows, file path, file size
8. If file already exists: append only new rows (check last timestamp first)
```

### 02-C: kaggle-notebook-run

Create file: .agents/skills/kaggle-notebook-run/SKILL.md

```markdown
---
name: kaggle-notebook-run
trigger: [run on Kaggle, backtest, Kaggle notebook, strategy, kaggle run]
description: Creates, runs, and retrieves results from a Kaggle notebook
---

## Mandatory Notebook Cell Structure

Every notebook built by this skill MUST follow this structure for EVERY stage.
No exceptions. Never skip markdown cells.

CELL 1 — Markdown (always first):
```
## Stage N — [Stage Name]
**Methodology:** [what this stage does in plain English]
**Input:** [exact variable names and data types entering this stage]
**Output:** [exact variable names and data types produced]
**Core Logic:** [step-by-step plain English explanation]
**Formula/Equation:**
$$ [LaTeX formula if applicable, else write: No formula — procedural logic] $$
```

CELL 2 — Code (immediately after markdown):
Implementation of that stage only. No mixing of stages in one cell.

Repeat CELL 1 + CELL 2 pattern for every stage.

## Execution Rules

1. Use credentials from ~/.quant_env
2. Create notebook via Kaggle API or push .ipynb file
3. Enable GPU accelerator: True
4. Enable internet: True
5. On Kaggle: use full parallel processing, all CPUs, GPU — no restrictions there
6. Save version after run completes
7. Download output files to ~/storage/shared/Quant/kaggle-outputs/[notebook-name]/
8. Report: notebook URL, version number, runtime, key output metrics
9. If run fails: download logs, report exact error to user
```

### 02-D: kaggle-db-update

Create file: .agents/skills/kaggle-db-update/SKILL.md

```markdown
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
```

Commit: `setup-02-core-skills`

---

## Step 03 — Temp-Skills System

### 03-A: Create folder structure

```
mkdir -p _temp-skills
```

### 03-B: Create _temp-skills/README.md

```markdown
# Temp-Skills

Auto-created by agy when a task pattern repeats 3+ times.
Behave identically to fixed skills but are tracked separately.

## Frontmatter Standard (required on every temp-skill)

---
type: temp-skill
name: [kebab-case-name]
version: 1
use_count: 0
created: YYYY-MM-DD
last_used: YYYY-MM-DD
description: [one line — what this skill does and when to use it]
tags: [temp-skill]
---

## Rules

- Never deleted automatically — only by explicit kill switch
- Increment use_count every time skill is used
- When version is bumped: keep old version as [name]-v[N].md archive in _temp-skills/archive/
- Promote to permanent skill via: python3 scripts/temp_skill_manager.py promote [name]
```

### 03-C: Create scripts/temp_skill_manager.py

Create this Python script:

```python
#!/usr/bin/env python3
"""
Temp-Skill Manager — tracks, lists, promotes, and kills temp-skills.
Usage:
  python3 scripts/temp_skill_manager.py stats
  python3 scripts/temp_skill_manager.py list
  python3 scripts/temp_skill_manager.py promote <skill-name>
  python3 scripts/temp_skill_manager.py kill
"""

import sys
import os
import shutil
from pathlib import Path
from datetime import date

VAULT = Path(__file__).parent.parent
TEMP_DIR = VAULT / "_temp-skills"
PERM_DIR = VAULT / ".agents" / "skills"
ARCHIVE_DIR = TEMP_DIR / "archive"


def parse_frontmatter(path):
    """Parse YAML frontmatter from a markdown file."""
    lines = path.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def get_all_skills():
    skills = []
    for f in TEMP_DIR.glob("*/SKILL.md"):
        fm = parse_frontmatter(f)
        if fm.get("type") == "temp-skill":
            skills.append((f, fm))
    return sorted(skills, key=lambda x: int(x[1].get("use_count", 0)), reverse=True)


def cmd_stats():
    skills = get_all_skills()
    print(f"\nTemp-Skills Stats")
    print(f"─────────────────")
    print(f"Total skills : {len(skills)}")
    if not skills:
        print("No temp-skills found.")
        return
    print(f"\nTop 5 by usage:")
    for f, fm in skills[:5]:
        print(f"  [{fm.get('use_count',0):>4} uses]  {fm.get('name','?')}  —  {fm.get('description','')}")
    newest = sorted(skills, key=lambda x: x[1].get("created", ""), reverse=True)
    if newest:
        print(f"\nNewest : {newest[0][1].get('name')} (created {newest[0][1].get('created')})")
    print()


def cmd_list():
    skills = get_all_skills()
    if not skills:
        print("No temp-skills found.")
        return
    print(f"\n{'Rank':<5} {'Uses':<6} {'Ver':<5} {'Name':<30} {'Last Used':<12} Description")
    print("─" * 90)
    for i, (f, fm) in enumerate(skills, 1):
        print(f"{i:<5} {fm.get('use_count',0):<6} {fm.get('version',1):<5} "
              f"{fm.get('name','?'):<30} {fm.get('last_used','?'):<12} "
              f"{fm.get('description','')}")
    print()


def cmd_promote(name):
    target = TEMP_DIR / name / "SKILL.md"
    if not target.exists():
        print(f"ERROR: Temp-skill '{name}' not found.")
        sys.exit(1)
    dest = PERM_DIR / name
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(target, dest / "SKILL.md")
    shutil.rmtree(TEMP_DIR / name)
    print(f"✅ Promoted '{name}' to .agents/skills/{name}/SKILL.md")
    print(f"   Removed from _temp-skills/")


def cmd_kill():
    skills = get_all_skills()
    print(f"\n⚠️  KILL SWITCH — This will permanently delete ALL {len(skills)} temp-skills.")
    print("This cannot be undone.")
    confirm = input("\nType CONFIRM to proceed: ").strip()
    if confirm != "CONFIRM":
        print("Aborted.")
        sys.exit(0)
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        TEMP_DIR.mkdir()
        (TEMP_DIR / "README.md").write_text("# Temp-Skills\n\nAll temp-skills were deleted via kill switch.\n")
    print(f"✅ All temp-skills deleted.")
    print(f"   _temp-skills/ folder reset.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        cmd_stats()
    elif cmd == "list":
        cmd_list()
    elif cmd == "promote" and len(sys.argv) > 2:
        cmd_promote(sys.argv[2])
    elif cmd == "kill":
        cmd_kill()
    else:
        print(__doc__)
```

### 03-D: Add auto-creation rule to AGENTS.md

Append to AGENTS.md:

```markdown
---

## TEMP-SKILL AUTO-CREATION RULE

After completing any task:
1. Check if the same sequence of 3+ steps was executed before
2. If yes → automatically create a temp-skill in _temp-skills/[skill-name]/SKILL.md
3. Use the standard frontmatter from _temp-skills/README.md
4. Set use_count to 1 on creation
5. On every subsequent use of that skill → increment use_count and update last_used
6. On any revision needed → bump version, archive old version to _temp-skills/archive/
7. Never delete temp-skills — only the kill switch can do that
```

### 03-E: Verify temp-skill manager

Run:
```
python3 scripts/temp_skill_manager.py stats
```

Expected: "Total skills: 0" — no error.

Commit: `setup-03-temp-skills-system`

---

## Step 04 — Full Maintenance Gate

Run every check:

```
python3 scripts/wiki_tool.py doctor
python3 scripts/wiki_tool.py build
python3 scripts/wiki_tool.py lint
python3 scripts/wiki_tool.py source-lint
python3 scripts/audit_public.py
python3 scripts/temp_skill_manager.py stats
```

All must pass with zero errors.

Commit: `setup-04-maintenance-gate-passed`

---

## Step 05 — Final Push

```
git add -A
git commit -m "quant-agent-system-v1-complete"
git push origin main
```

---

## ACCEPTANCE CRITERIA

Every item must be PASS before this setup is considered complete.

- [ ] ~/.quant_env exists, chmod 600, all 8 credentials present
- [ ] ~/.config/kaggle/kaggle.json configured, kaggle CLI responds
- [ ] All Python packages import: kaggle, pyotp, fyers_apiv3, requests
- [ ] AGENTS.md contains: HARDWARE CONSTRAINTS section
- [ ] AGENTS.md contains: TOKEN EFFICIENCY RULES section
- [ ] AGENTS.md contains: TEMP-SKILL AUTO-CREATION RULE section
- [ ] .agents/skills/fyers-auth/SKILL.md exists with 5-step auth rules
- [ ] .agents/skills/fyers-historical/SKILL.md exists with chunking + SQLite rules
- [ ] .agents/skills/kaggle-notebook-run/SKILL.md exists with mandatory LaTeX+code structure
- [ ] .agents/skills/kaggle-db-update/SKILL.md exists with dataset rules
- [ ] _temp-skills/ folder exists with README.md
- [ ] scripts/temp_skill_manager.py runs without error
- [ ] python3 scripts/wiki_tool.py doctor passes
- [ ] python3 scripts/wiki_tool.py lint passes
- [ ] python3 scripts/audit_public.py passes
- [ ] All changes pushed to origin main

---

## USER DAILY WORKFLOW (after setup)

One-word launch:
```
wiki
```

Download data:
```
Download 1 year of 1-min data for NIFTY futures
```

Run backtest:
```
Run a mean reversion backtest on NIFTY 1-min data on Kaggle.
Give me Sharpe ratio, max drawdown, win rate.
```

Check temp-skills:
```bash
python3 scripts/temp_skill_manager.py list
```

Promote a temp-skill to permanent:
```bash
python3 scripts/temp_skill_manager.py promote [skill-name]
```

Kill all temp-skills (emergency only):
```bash
python3 scripts/temp_skill_manager.py kill
```

---

*quant-agent-setup-v1.0.0 — built for Termux + agy + LLM Wiki on Android*
