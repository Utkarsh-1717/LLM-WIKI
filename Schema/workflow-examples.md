# Workflow Examples

## Ingesting a Source
1. Source is added to `Raw/Sources/my-source.md`.
2. Agent searches catalog to find related topics.
3. Agent updates `Wiki/Topics/existing.md` and creates `Wiki/Concepts/new-concept.md`.
4. Both notes add `Raw/Sources/my-source.md` to their `sources` array and update `source_count`.
5. Run `python3 scripts/wiki_tool.py source-scan --update --accept-covered` to mark the source as processed.
