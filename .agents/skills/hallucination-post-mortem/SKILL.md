---
name: hallucination-post-mortem
trigger: [you hallucinated, wrong logic, look at the reference, incorrect implementation, post-mortem]
description: Forces the agent to halt execution, analyze its reasoning failure, and permanently document the human correction into the Wiki before writing any more code.
version: 1.0.0
last_updated: 2026-06-12
---

# Hallucination Post-Mortem Skill

## Purpose
This skill enforces the global `POST-MORTEM KNOWLEDGE RULE`. When an AI hallucinates logic or incorrectly ignores a reference file, it must stop and explicitly synthesize the failure into the Wiki. This ensures the system continuously learns and never repeats the identical logic flaw across any project.

## Workflow Execution

When triggered by a human halting your code execution due to flawed logic:

### 1. Hard Stop
- Immediately cease generating or modifying code for the primary task.
- Acknowledge the user's rebuttal without defending the flawed logic.

### 2. Failure Synthesis
Create or update a specific Markdown file inside `Wiki/QC/Post_Mortems/` (e.g., `[Topic]_Hallucinations.md`). The file MUST contain the following sections explicitly:

- **The AI's Hallucination:** A brutally honest summary of what the agent incorrectly assumed, did, or hallucinated.
- **The Human Correction:** What the human explicitly pointed out or commanded the agent to reference instead.
- **The Structural Root Cause:** A deep analysis of *why* the AI's logic was structurally broken or misaligned with the project's architecture.
- **The Permanent Rule:** A rigid, globally applicable directive to prevent this specific failure ever again.

### 3. Catalog Integration
- Update `Wiki/catalog.jsonl` to ensure the new Post-Mortem file is tracked and searchable.
- Inject `[[wikilinks]]` between the Post-Mortem and the specific project/entity files involved.

### 4. Human Verification
- Ask the user to review the generated Post-Mortem artifact.
- Do NOT proceed to fix the original codebase until the user confirms the post-mortem accurately captures the lesson.

## Connections
- [[agent-rules]]
- [[post-mortems-index]]
