---
tags:
  - "entity"
topics: [skill, monitoring, kaggle]
status: active
updated: 2026-06-02
---

# Kaggle Pulse Check Skill

The [[kaggle-pulse-check]] skill monitors Kaggle kernels immediately after they are pushed. Uses rapid polling (every 10s for first 5 min) to detect early failures, then shifts to 60s polling until completion.

## Critical Rule (Learned 2026-06-02)

**Always parse the real kernel slug from the push output URL** — never use the `id` field from `kernel-metadata.json`. Kaggle generates the slug from the notebook title, which may differ from the `id` field. Using the wrong slug gives `Cannot access kernel` silently forever.

```
Kernel version N pushed. Check progress at:
https://www.kaggle.com/code/utkarshpatelthefirst/<REAL-SLUG>
```

See [[kaggle-notebook-hardening]] for the full failure taxonomy.

## Connections
- [[session-2026-06-02b]]
- [[index]]
- [[kaggle-compute]]
- [[kaggle-notebook-run]]
- [[kaggle-notebook-hardening]]
- [[pairs-trading-pipeline]]
