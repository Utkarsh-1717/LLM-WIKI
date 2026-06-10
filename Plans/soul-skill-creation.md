# Plan: Create 'Soul' Production Distillation Skill

The goal is to create a new, highly specific agent skill that bridges the gap between our messy drafting/auditing phase and the final production deployment stage. This skill will standardize how we compile all our verified math, QC reports, and corrected code into the final "Source of Truth" inside the `Soul/` directory.

## Open Questions
- What should we name the skill? (e.g., `soul-production-compiler`, `soul-distiller`, or `productionize-to-soul`)?
- Do you want this skill to automatically spawn the agent team (using `invoke_subagent`) to write the final code, or should the skill just provide strict instructions for the main agent (me) to follow to guide *you* through the teamwork prompt crafting?

## Proposed Approach

### Step 1 — Define the Target Architecture in `Soul/`
The skill will strictly enforce that any final production assets are saved into this exact structure:
- `Soul/Methodology/`: In-depth, verified mathematical logic and theoretical frameworks (incorporating all QC fixes, like the EM matrix dimension corrections).
- `Soul/Code/`: The final, bug-free, production-grade Kaggle `.ipynb` notebooks and Python scripts.
- `Soul/Conclusions/`: In-depth results, backtest analyses, limitations, and future work.

### Step 2 — Draft the Skill Markdown (`.agents/skills/soul-production-compiler/SKILL.md`)
I will write the actual skill file containing:
1. **Trigger Keywords**: e.g., "finalize to soul", "productionize", "create soul artifacts".
2. **Context Assembly Rules**: Instructions on how the agent must gather context (reading the `Plans/`, the `Raw/Sources/` QC reports, and the raw code).
3. **Agent Team Protocol**: A mandatory workflow where the agent uses the multi-agent team (similar to the `/teamwork-preview` framework) to meticulously analyze the context, write the production code, and perform a final self-correction loop before saving to `Soul/Code/`.
4. **Verification Step**: Ensuring the code implements the fixes identified during the QC audits (e.g., proper overnight scaling, correct ADF checks).

### Step 3 — Save and Register the Skill
Save the skill file and confirm it is ready to be triggered for finalizing the Pairs Trading project.

## Verification Plan
After creating the skill, we can trigger it immediately to start migrating the corrected Pairs Trading pipeline into the `Soul/` directory, testing if the team successfully outputs the final production notebooks.
