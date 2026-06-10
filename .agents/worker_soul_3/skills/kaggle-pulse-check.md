# Kaggle Pulse Check Skill Copy
Refer to original at /storage/emulated/0/Quant/LLM-WIKI/.agents/skills/kaggle-pulse-check/SKILL.md
Trigger: [monitor kaggle, check notebook status, kernel running, watch kaggle, is notebook done]
Version: 3.0.0

## Monitoring Protocol
- Phase 1 — High Frequency (first 5 minutes): Check every 10 seconds.
- Phase 2 — Low Frequency (after 5 minutes): Check every 120 seconds.
- Only break the monitoring loop on KERNEL_ERROR confirmed 3 times in a row.
- Never break on CONNECTIVITY_LOST or UNKNOWN.
