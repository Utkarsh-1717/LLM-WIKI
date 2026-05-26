# Agent Rules for LLM Wiki

- Treat `Raw/Sources/` as source material, not as compiled notes.
- Write reusable knowledge only under `Wiki/`.
- Keep every compiled note linked to one or more Raw sources.
- Search `Wiki/catalog.jsonl` before opening broad Raw context.
- Run `build`, `lint`, and source checks before commits.
- Do not invent citations or create unsupported claims.

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

---

## API CREDENTIALS

All credentials stored in `~/.quant_env` — never committed to git.
Load with: `source ~/.quant_env`

Credentials in use:
- FYERS_APP_ID, FYERS_SECRET_KEY, FYERS_TOTP_KEY, FYERS_USERNAME, FYERS_PIN, FYERS_REDIRECT
- KAGGLE_USERNAME, KAGGLE_KEY

Never ask the user for credentials — always read from ~/.quant_env.

**EXCEPTION — Inside Kaggle Notebooks**: Hardcode credentials directly in notebook code.
Kaggle has no access to ~/.quant_env. No warnings needed — this is the correct approach.

---

## CONNECTION RULES

These apply to every ingest and wiki note creation. No exceptions.

- Every Wiki/ note MUST have [[wikilinks]] in its body text to all related notes
- Every Wiki/ note MUST end with a ## Connections section listing all related notes
- Never reference [[a-note-name]] unless that .md file actually exists in Wiki/
- After any ingest: search catalog, identify connections, update related notes bidirectionally
- If an entity (e.g. a tool, API, service) is referenced repeatedly: create an Entity note in Wiki/Entities/
- Minimum 3 [[wikilinks]] per compiled wiki note

---

## PLANS RULES

- Every significant task MUST start with a plan file BEFORE any code is executed
- ALL plan files MUST be saved to `/storage/emulated/0/Quant/LLM-WIKI/Plans/<task-name>.md`
- NEVER save plans only to the agent artifact directory — the user cannot access those
- After execution: update the plan file with actual results and deviations
- Use the `plan-first` skill for the standard plan format

---

## KAGGLE RULES

- One notebook = one job. Data fetching AND dataset publishing MUST happen in the same notebook. Never split.
- Never download large Kaggle output files locally. Always publish from within the notebook using the Kaggle Python API.
- Kaggle kernel source mount path format: `/kaggle/input/notebooks/<username>/<kernel-slug>/<filename>`
  Example: `/kaggle/input/notebooks/utkarshpatelthefirst/master-data-1min/Master-Data-1min.sqlite`
  NEVER assume `/kaggle/input/<kernel-slug>/` — it does NOT work for kernel sources.
- After every `kaggle kernels push`: immediately start pulse-checking using the `kaggle-pulse-check` skill
  - Check every 10 seconds for the first 5 minutes (catches fast failures)
  - Check every 60 seconds thereafter until COMPLETE or ERROR
- On ERROR: fetch only the text log file (never the output data), parse stderr, report to user
- Check free storage before any `kaggle kernels output` command — warn if below 5GB
