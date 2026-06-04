# Skill: Maintain

Before every meaningful commit, run the maintenance gate:
```bash
python3 scripts/wiki_tool.py doctor
python3 scripts/wiki_tool.py build
python3 scripts/wiki_tool.py lint
python3 scripts/wiki_tool.py link-check
python3 scripts/wiki_tool.py source-lint
python3 scripts/audit_public.py
```
After source ingestion, also run:
```bash
python3 scripts/wiki_tool.py source-scan --update --accept-covered
python3 scripts/wiki_tool.py source-lint
```
Always run `audit_public.py` to ensure no sensitive data or machine-local paths are committed.
