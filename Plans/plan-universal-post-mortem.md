# Plan: Universal Knowledge & Post-Mortem Mechanism

## Objective
To implement a universal framework that forces any agent to document its own mistakes, hallucinations, and human corrections permanently into the Wiki, so that the entire AI system continuously learns and never repeats the same logic flaw twice on *any* project.

## Proposed Changes

### 1. Update `AGENTS.md`
We will add a new global rule to `AGENTS.md` that applies to every agent instance across all projects:

**THE POST-MORTEM KNOWLEDGE RULE**
Whenever the user halts an agent due to a hallucination, flawed logic, or failure to follow reference code:
1. The agent MUST explicitly document the failure before writing any new code.
2. The agent must create or update a dedicated `Wiki/QC/Post_Mortems/` document.
3. The documentation must strictly contain:
   - **The AI's Hallucination**: What the agent incorrectly assumed or did.
   - **The Human Correction**: What the user explicitly pointed out.
   - **The Structural Root Cause**: Why the AI's logic was wrong in the context of the specific domain.
   - **The Permanent Rule**: A strict directive to prevent this specific failure globally.
4. Update `Wiki/catalog.jsonl` and interlink the Post-Mortem to the project entity.

### 2. Create Universal Skill: `hallucination-post-mortem`
**Path**: `.agents/skills/hallucination-post-mortem/SKILL.md`

I will create a brand new agentic skill that triggers universally on keywords like "you hallucinated", "wrong logic", "look at the reference", or "incorrect implementation". 

When this skill is triggered, it will force the agent to:
- Suspend all code execution.
- Analyze the user's rebuttal.
- Execute the **POST-MORTEM KNOWLEDGE RULE** by synthesizing the correction into the Wiki.
- Ask the user to verify the Post-Mortem log before proceeding with the code fix.

### 3. Create Wiki Structure
- Create the `Wiki/QC/Post_Mortems/` directory.
- Add an index note linking all past AI failures and lessons learned, ensuring they are injected into the context window whenever related entities are queried.

## Verification Plan
1. I will write these structural changes into your repository.
2. We will test the system by reviewing how the `AGENTS.md` and the new skill interact.
3. Any future agent that makes a mistake will automatically pivot to this skill, ingest your correction, and permanently grow the Wiki's intelligence.
