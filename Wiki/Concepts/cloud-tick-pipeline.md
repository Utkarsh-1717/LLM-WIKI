---
title: cloud-tick-pipeline
type: concept
tags:
  - "concept"
  - "quant"
  - "tick-data"
  - "pipeline"
topics: [quant, tick-data, pipeline, cloud, real-time]
created: 2026-06-02
updated: 2026-06-02
status: planned
aliases: [cloud-tick-pipeline]
---

# Cloud Tick Pipeline

> **Note**: This is the planned cloud-native tick data collection pipeline. The detailed architecture note lives at [[higher-level-tick-pipeline]]. This stub exists to resolve wikilink references.

The cloud tick pipeline is the planned successor to [[qt-tick-collector]]. It moves real-time tick data collection off the local Android device and onto cloud infrastructure, enabling continuous 24/7 collection without device dependency.

## Current Status

Planned. The scheduling layer was explored via [[kaggle-github-scheduler]] (using GitHub Actions to trigger Kaggle notebooks). The architecture is documented in `Plans/cloud-tick-pipeline.md`.

## Key Design Points

- Data source: [[fyers-api]] WebSocket tick feed
- Compute: cloud VM or serverless function (not Kaggle — Kaggle lacks persistent WebSocket support)
- Storage: publish to Kaggle dataset (same pattern as [[master-data-1min-dataset]])
- Scheduling: GitHub Actions cron → Kaggle kernel trigger

## Connections
- [[session-2026-06-02]]
- [[session-2026-06-01]]
- [[index]]
- [[higher-level-tick-pipeline]]
- [[qt-tick-collector]]
- [[kaggle-github-scheduler]]
- [[fyers-api]]
- [[master-data-1min-dataset]]
- [[kaggle-compute]]
