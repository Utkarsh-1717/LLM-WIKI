# Skill: Lint

When linting the Wiki, ensure the following minimum lint behaviors:
- Compiled Wiki notes must use one allowed tag: `topic`, `concept`, `entity`, `project`, or `log`.
- Compiled Wiki notes must keep `source_count` equal to the number of `sources`.
- Compiled Wiki note source links should point to existing files under `Raw/Sources/`.
- Raw source notes should include `Title`, `Reference`, `Created`, `Processed`, and `tags`.
- Run `python3 scripts/wiki_tool.py lint` and `python3 scripts/wiki_tool.py source-lint` to validate these behaviors.
- Ensure that if a source is marked processed, it has Wiki coverage.
