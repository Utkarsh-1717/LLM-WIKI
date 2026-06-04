# Skill: Ingest

When the user adds a new source, follow this workflow exactly:
1. Put cleaned Markdown in `Raw/Sources/`.
2. Run `search-catalog` for likely related topics.
3. Open only the most relevant compiled Wiki notes.
4. Create or update focused notes in `Wiki/`.
5. Add Raw source links to `sources` in the frontmatter.
6. Keep `source_count` accurate.
7. Run the maintenance scripts:
   ```bash
   python3 scripts/wiki_tool.py build
   python3 scripts/wiki_tool.py lint
   python3 scripts/wiki_tool.py link-check
   python3 scripts/wiki_tool.py source-scan --update --accept-covered
   python3 scripts/wiki_tool.py source-lint
   ```
8. Add a log entry if the ingest meaningfully changed the Wiki using `scripts/wiki_tool.py log --title "title" --details "details"`.
