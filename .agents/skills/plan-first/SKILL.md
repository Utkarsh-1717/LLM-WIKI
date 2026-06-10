---
name: plan-first
trigger: [plan, new task, new feature, build something, create dataset, run notebook, ingest]
description: Enforces the rule that any significant task must begin with a plan.md file saved in the LLM-WIKI/Plans/ folder before any code is executed.
version: 1.0.0
last_updated: 2026-05-26
---

# Plan-First Skill

## Purpose

Every significant task MUST have a plan file created BEFORE execution. This prevents trial-and-error loops and gives the user a chance to review the approach.

## Plan File Location

**ALWAYS** save plan files here:
```
/storage/emulated/0/Quant/LLM-WIKI/Plans/<task-name>.md
```

The `Plans/` folder is user-accessible via their file manager. **Never** save plans only to the agent's artifact directory (`/data/data/...`) as those are not accessible to the user.

## When to Create a Plan

Create a plan file for any task that:
- Involves creating or modifying a Kaggle notebook
- Involves fetching or storing data
- Requires more than 3 steps to complete
- Involves irreversible actions (publishing datasets, running long jobs)

## Plan File Format

```markdown
# Plan: <Task Name>

## Objective
One-paragraph description of what we are trying to achieve.

## Open Questions (for user review)
- List any design decisions the user needs to make
- List anything that could go wrong

## Proposed Approach

### Step 1 — <Step Name>
- What: ...
- Why: ...
- How: ...

### Step 2 — <Step Name>
...

## Time Estimate
~X minutes / hours on Kaggle

## Connections to Existing Skills
- [[skill-name]]
- [[skill-name]]
```

## After Creating Plan

1. **Update the Index**: Append a `[[task-name]]` link to `Plans/plans.md` so the new plan is properly indexed in the directory.
2. Tell the user: "Plan saved at `LLM-WIKI/Plans/<task-name>.md`. Please review before I proceed."
3. Wait for explicit user approval before executing
4. After execution: update the plan file with actual results and any deviations

## Connections
- [[kaggle-notebook-run]]
- [[fyers-historical-kaggle]]
