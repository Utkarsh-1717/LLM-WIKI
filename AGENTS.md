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

All credentials stored in `~/.quant_env` — never committed to git, never hardcoded.
Load with: `source ~/.quant_env`

Credentials in use:
- FYERS_APP_ID, FYERS_SECRET_KEY, FYERS_TOTP_KEY, FYERS_USERNAME, FYERS_PIN, FYERS_REDIRECT
- KAGGLE_USERNAME, KAGGLE_KEY

Never ask the user for credentials — always read from ~/.quant_env.
