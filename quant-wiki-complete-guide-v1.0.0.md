# Quant Wiki System — Complete Reference Guide v1.0.0

> This file serves two purposes:
> 1. Give to agy for final self-evaluation + ingest + backup (Section A)
> 2. Keep as your personal daily reference (Section B onwards)

---

# SECTION A — GIVE THIS TO AGY (one time only)

## Master Self-Evaluation & Finalization Prompt

Give agy exactly this:

```
Read this file completely. Execute Part 1, then Part 2, then Part 3 in order.
Do not stop until every acceptance criterion in every part passes.
If anything fails, fix it and re-check before moving on.

---

PART 1 — DEEP SELF-EVALUATION

Read every file listed below and verify the implementation is correct,
complete, and consistent. For each item report PASS or FAIL with reason.

Files to read first:
- llms-core-setup.md (original wiki guide)
- quant-agent-setup-v1.0.0.md (quant system guide)
- quant-wiki-multiformat-v1.0.0.md (multiformat ingest guide)
- AGENTS.md (current implementation)
- All files in .agents/skills/
- _temp-skills/README.md
- scripts/wiki_tool.py
- scripts/temp_skill_manager.py
- scripts/audit_public.py

Check every item:

WIKI STRUCTURE
- [ ] Raw/Sources/ exists and contains only .md source notes
- [ ] Raw/Sources/attachments/ exists for non-md files
- [ ] Raw/Files/ — if exists and not in original guide, clean up correctly
- [ ] Wiki/ contains Topics/ Concepts/ Projects/ Logs/
- [ ] Schema/ contains all documentation files (not stubs)
- [ ] _templates/ contains all 6 note templates
- [ ] .agents/skills/ contains all 5 fixed skills
- [ ] _temp-skills/ folder and README exist
- [ ] scripts/ contains wiki_tool.py, temp_skill_manager.py, audit_public.py

AGENTS.MD RULES
- [ ] HARDWARE CONSTRAINTS section present and complete
- [ ] TOKEN EFFICIENCY RULES section present and complete
- [ ] TEMP-SKILL AUTO-CREATION RULE present and complete
- [ ] API CREDENTIALS note present

FIXED SKILLS — verify each has correct trigger + rules
- [ ] fyers-auth: 5-step auth flow, sources ~/.quant_env
- [ ] fyers-historical: chunking + SQLite + single-threaded
- [ ] kaggle-notebook-run: mandatory LaTeX+code cell structure baked in
- [ ] kaggle-db-update: dataset versioning + wiki update
- [ ] multi-format-ingest: all 8 formats (.py .pdf .ipynb .jpg .png .csv .json .xlsx)

TEMP-SKILLS SYSTEM
- [ ] scripts/temp_skill_manager.py runs: stats, list, promote, kill
- [ ] Kill switch requires CONFIRM input
- [ ] Frontmatter standard correct in README

TOOLS
- [ ] wiki_tool.py doctor passes
- [ ] wiki_tool.py build passes
- [ ] wiki_tool.py lint passes
- [ ] wiki_tool.py source-lint passes
- [ ] wiki_tool.py attachment-scan passes (new command)
- [ ] audit_public.py passes

Fix every FAIL before continuing to Part 2.

---

PART 2 — INGEST EVERYTHING INTO WIKI

After all checks pass, ingest these files as wiki sources:

1. Ingest llms-core-setup.md
   Title: LLM Wiki Core Setup Guide
   Tags: [wiki, methodology, setup]

2. Ingest quant-agent-setup-v1.0.0.md
   Title: Quant Agent System Setup
   Tags: [quant, setup, agy, skills]

3. Ingest quant-wiki-multiformat-v1.0.0.md
   Title: Multi-Format Ingest Extension
   Tags: [wiki, ingest, multiformat]

4. Ingest AGENTS.md current state
   Title: Agent Rules and Constraints
   Tags: [agents, rules, hardware]

For each ingested file:
- Create proper source note in Raw/Sources/
- Compile into relevant Wiki/ notes
- Link related topics together

Then run:
- wiki_tool.py build
- wiki_tool.py lint
- wiki_tool.py source-scan

All must pass.

---

PART 3 — FULL MAINTENANCE + GIT BACKUP

Run complete maintenance gate in this exact order:
1. python3 scripts/wiki_tool.py doctor
2. python3 scripts/wiki_tool.py build
3. python3 scripts/wiki_tool.py lint
4. python3 scripts/wiki_tool.py source-lint
5. python3 scripts/wiki_tool.py source-scan
6. python3 scripts/wiki_tool.py attachment-scan
7. python3 scripts/audit_public.py
8. python3 scripts/temp_skill_manager.py stats

Fix any failure before continuing.

Then commit and push:
git add -A
git commit -m "quant-wiki-system-v1-final-complete"
git push origin main

Report final status:
- Total wiki notes
- Total raw sources
- Total fixed skills
- Total temp-skills
- Git commit hash
- GitHub URL
```

---

# SECTION B — YOUR PERSONAL REFERENCE GUIDE

## System Architecture

```
YOU
 ↓ (one instruction)
agy — reads AGENTS.md rules automatically
 ↓
Loads matching skill only (token efficient)
 ↓
┌─────────────────────────────────────────┐
│           SKILLS AVAILABLE              │
│                                         │
│  fyers-auth       → Fyers login         │
│  fyers-historical → Download OHLCV      │
│  kaggle-nb-run    → Run backtest        │
│  kaggle-db-update → Upload database     │
│  multi-fmt-ingest → Process any file    │
│                                         │
│  + Temp-skills (auto-grows over time)   │
└─────────────────────────────────────────┘
 ↓
LLM Wiki (permanent memory)
 ↓
Kaggle (heavy compute — backtesting, data)
```

---

## Folder Structure Explained

```
LLM-WIKI/
│
├── Raw/                     ← INPUTS (you bring stuff here)
│   └── Sources/             ← .md summaries of everything ingested
│       └── attachments/     ← original files (.py .pdf .ipynb etc)
│
├── Wiki/                    ← OUTPUTS (agy builds and maintains)
│   ├── Topics/              ← broad topic pages
│   ├── Concepts/            ← specific concept definitions
│   ├── Projects/            ← strategy/project notes
│   └── Logs/                ← activity logs
│
├── Schema/                  ← RULES (how wiki works)
├── _templates/              ← note templates
├── .agents/skills/          ← fixed permanent skills
├── _temp-skills/            ← auto-learned skills (grows over time)
├── scripts/                 ← maintenance tools
│   ├── wiki_tool.py         ← doctor, build, lint, scan
│   ├── temp_skill_manager.py← list, promote, kill
│   └── audit_public.py      ← security check
└── AGENTS.md                ← master rules file
```

---

## Daily Workflow — 5 Steps

### 1. Launch (always)
```bash
wiki
```

### 2. Health check (30 seconds)
```
Run doctor, lint, source-lint, audit_public.py and temp-skills stats.
Fix anything broken. Report one line per check.
```

### 3. Add new knowledge
Drop file into attachments folder:
```bash
cp ~/storage/shared/Download/[anyfile] \
   ~/storage/shared/Quant/LLM-WIKI/Raw/Sources/attachments/
```
Then tell agy:
```
Process all attachments
```
Or single file:
```
Ingest Raw/Sources/attachments/[filename]
```

### 4. Quant work (see prompts below)

### 5. End of session
```
Run full maintenance gate. Ingest any new findings from today.
Commit and push to origin main.
```

---

## Complete Prompt Cheat Sheet

### Maintenance
| Task | Prompt |
|---|---|
| Health check | `Run doctor, lint, source-lint, audit_public.py, temp-skills stats. Fix anything broken.` |
| Full backup | `Run maintenance gate and push to origin main` |
| Check wiki size | `Run doctor and report wiki notes, sources, temp-skills count` |

### Knowledge Ingestion
| Task | Prompt |
|---|---|
| Ingest all pending | `Process all attachments` |
| Ingest one file | `Ingest Raw/Sources/attachments/[filename]` |
| Ingest pasted text | `Ingest this into the wiki: [paste content]` |
| Find connections | `What wiki topics connect to [topic]?` |
| Query knowledge | `What do I know about [topic]?` |

### Quant Data
| Task | Prompt |
|---|---|
| Download 1 year 1-min | `Download 1 year of 1-min OHLCV data for [SYMBOL] store as SQLite upload to Kaggle` |
| Download custom range | `Download [SYMBOL] 1-min data from [date] to [date] add to existing database` |
| Update database | `Fetch latest data for all symbols in database and update Kaggle dataset` |
| Check database | `What symbols and date ranges are in the Kaggle stock database?` |

### Quant Analysis
| Task | Prompt |
|---|---|
| Run backtest | `Load [SYMBOL] 1-min data from Kaggle. Run [strategy]. Kaggle notebook. Give me Sharpe, max drawdown, win rate, total trades.` |
| Compare strategies | `Compare all tested strategies ranked by Sharpe ratio from the wiki` |
| Find alpha | `Based on all wiki knowledge, suggest 3 mean reversion strategy variations to test on NIFTY 1-min` |
| Analyse results | `Read latest Kaggle output and extract key findings into wiki` |

### Skills Management
| Task | Command |
|---|---|
| See all temp-skills | `python3 scripts/temp_skill_manager.py list` |
| Check stats | `python3 scripts/temp_skill_manager.py stats` |
| Promote to permanent | `python3 scripts/temp_skill_manager.py promote [skill-name]` |
| Kill all temp-skills | `python3 scripts/temp_skill_manager.py kill` |

---

## Hardware Rules (never forget)

| Rule | Detail |
|---|---|
| Local max RAM | 2GB |
| Local max time | 30 min |
| No parallel locally | Single-threaded always |
| Heavy compute | Kaggle only |
| API rate limit | 0.5s sleep between calls |

---

## Self-Improvement Loop (automatic)

You do not manage this. agy does it automatically:

```
You give instruction
  ↓
agy completes task
  ↓
agy checks: was same 3-step pattern repeated?
  ↓ yes
agy creates temp-skill in _temp-skills/
  ↓
Next time same task appears: temp-skill loads automatically
  ↓
use_count increments
  ↓
You review with: python3 scripts/temp_skill_manager.py list
  ↓
Promote best ones: temp_skill_manager.py promote [name]
```

---

## Credentials Location

All credentials in `~/.quant_env` — never in any committed file.

To update credentials:
```bash
nano ~/.quant_env
```

Replace any key. Then:
```bash
source ~/.quant_env
```

---

## Emergency Commands

| Situation | Command |
|---|---|
| Too many temp-skills | `python3 scripts/temp_skill_manager.py kill` |
| Wiki broken | `python3 scripts/wiki_tool.py doctor` |
| Storage check | `df -h ~/storage/shared/Quant/` |
| Git status | `cd ~/storage/shared/Quant/LLM-WIKI && git log --oneline -10` |
| Restart fresh session | `wiki` |

---

## File Types Quick Reference

| Extension | What agy extracts |
|---|---|
| `.py` | Functions, logic, data flow, dependencies |
| `.pdf` | Summary, concepts, methodology, findings |
| `.ipynb` | Stage summaries, strategy logic, results |
| `.jpg/.png` | Description, data/chart values, interpretation |
| `.csv` | Schema, date range, data quality, use cases |
| `.json` | Structure, content summary, key fields |
| `.xlsx` | Sheet summaries, key tables |

---

## Git Reference

| Task | Command |
|---|---|
| Check status | `git status` |
| See history | `git log --oneline -10` |
| Manual backup | `git add -A && git commit -m "manual-backup" && git push` |
| Check remote | `git remote -v` |

GitHub: https://github.com/Utkarsh-1717/LLM-WIKI

---

*quant-wiki-complete-guide-v1.0.0*
*Stack: Termux + agy v1.0.2 + LLM Wiki + Kaggle*
*Device: Realme GT 6T | Android*
