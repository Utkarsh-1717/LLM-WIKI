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
