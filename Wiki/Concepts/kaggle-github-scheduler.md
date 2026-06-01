---
title: Kaggle GitHub Scheduler Architecture
tags:
  - concept
topics: [kaggle, github, scheduler, cron, automation]
status: evergreen
created: 2026-06-01
updated: 2026-06-01
source_count: 1
sources:
  - Raw/Sources/agents-rules.md
---

# Kaggle GitHub Scheduler Architecture

## Overview
Kaggle's native notebook scheduler has a hard limitation: scheduled notebooks expire after approximately 10 runs. This makes it impossible to use for set-and-forget, autonomous trading data collection pipelines like the [[cloud-tick-pipeline]]. 

To bypass this limit, we decouple the scheduling logic from Kaggle and offload it to **GitHub Actions**.

## Architecture
- **Kaggle Kernel**: Acts as the execution engine and storage container (100GB limit).
- **GitHub Actions**: Acts as the Cron Trigger. It is configured to run a Python script daily.
- **Kaggle REST API**: Used by the GitHub Action to pull the latest kernel source and push it as a new version. Pushing a new version automatically and immediately queues the kernel for execution on Kaggle.

### The Trigger Logic
A Python script (`trigger.py`) runs in the GitHub Action runner:
1. Validates Kaggle API credentials via `/kernels/status`.
2. Checks if the kernel is already `running` or `queued` to prevent double-execution.
3. Pulls the latest notebook source using `/kernels/pull`.
4. Pushes the exact same source back using `/kernels/push`. This creates a new version and triggers execution.
5. Polls for 5 minutes to confirm the state changes to `running` or `complete`.

### Security and Hardcoded Credentials
For private repositories entirely controlled by the user, setting up proper GitHub Secrets using `libsodium` (PyNaCl) sealed boxes can be overly complex and prone to compilation failures on Android/Termux environments.
Instead, a highly pragmatic approach is to hardcode the `KAGGLE_USERNAME` and `KAGGLE_KEY` directly into the `.github/workflows/trigger.yml` as `env` variables. Since the repository is strictly private, there is zero security risk, and it bypasses all encryption library dependencies.

## Cron Scheduling
GitHub Actions allows using standard CRON strings. 
To run a script every single day of the week at **09:00 AM IST** (03:30 AM UTC), the string is:
`30 3 * * *`

Even on weekends or market holidays, the script triggers Kaggle. The intelligence resides within the Kaggle notebook itself, which calls `fyers.market_status()` upon waking up and exits cleanly in ~30 seconds if the market is closed, saving resources.

## Connections
- [[cloud-tick-pipeline]]
- [[higher-level-tick-pipeline]]
- [[qt-tick-collector]]
