# Command Reference

Reference for `wiki_tool.py` commands:
- `doctor`: Health check for folders, catalog, and basic counts.
- `build`: Generate `catalog.jsonl` and index files.
- `lint`: Validate Wiki frontmatter, tags, and source links.
- `source-scan`: List Raw sources and optionally update `source-manifest.jsonl`.
- `source-lint`: Validate source frontmatter and coverage.
- `source-delta`: Show Raw sources not in manifest.
- `source-coverage`: Show Wiki coverage for Raw sources.
- `search-catalog --query "text"`: Search the compiled Wiki notes.
- `log --title "title" --details "details"`: Append to `Wiki/log.md`.
