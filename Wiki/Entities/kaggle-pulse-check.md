---
tags:
  - "entity"
topics: [skill, monitoring, kaggle]
status: active
---

# Kaggle Pulse Check Skill

The [[kaggle-pulse-check]] skill is an agent tool used to continuously monitor Kaggle notebooks immediately after they are pushed. 
It uses rapid polling (every 10 seconds for the first 5 minutes) to quickly detect early failures, and then shifts to 60-second polling to efficiently wait for long-running notebooks to finish.

## Usage
Agents are instructed to run this automatically in the background via `manage_task` after pushing a kernel.

## Connections
- [[kaggle-compute]]
