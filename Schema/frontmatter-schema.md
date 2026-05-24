# Frontmatter Schema

Defines allowed frontmatter tags for the LLM wiki.

## Raw Source Notes
```yaml
---
Title: "Title of the source"
Author: "Author Name"
Reference: "URL or ID"
ContentType:
  - "markdown"
Created: YYYY-MM-DD
Processed: false
tags:
  - "source"
---
```

## Compiled Wiki Notes
```yaml
---
tags:
  - "concept" # must be one of: topic, concept, entity, project, log
topics: []
status: seed
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: ["Raw/Sources/source.md"]
source_count: 1
aliases: []
---
```
