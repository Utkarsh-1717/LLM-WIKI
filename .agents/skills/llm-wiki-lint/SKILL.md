# Skill: Lint

When linting the Wiki, ensure the following minimum lint behaviors:
- Compiled Wiki notes must use one allowed tag: `topic`, `concept`, `entity`, `project`, or `log`.
- Compiled Wiki notes must keep `source_count` equal to the number of `sources`.
- Compiled Wiki note source links should point to existing files under `Raw/Sources/`.
- Raw source notes should include `Title`, `Reference`, `Created`, `Processed`, and `tags`.
- Run `python3 scripts/wiki_tool.py lint` and `python3 scripts/wiki_tool.py source-lint` to validate these behaviors.
- **CRITICAL**: The `link-check` script (`python3 scripts/wiki_tool.py link-check`) ensures that there are no broken `[[wikilinks]]` and that all links are bidirectional. 
  - **Auto-Fix**: You can now run `python3 scripts/wiki_tool.py link-check --fix` to automatically append missing backlinks to the `## Connections` sections.
  - **Automation**: This auto-fix logic is built directly into the Git pre-commit hook. You never need to manually worry about missing backlinks again — simply run `git commit` and any missing bidirectional connections will be automatically injected and staged.
- Ensure that if a source is marked processed, it has Wiki coverage.
