# Skill: Query

When answering a question from the Wiki, follow this workflow:
1. Start with `Wiki/index.md`.
2. Search the catalog:
   ```bash
   python3 scripts/wiki_tool.py search-catalog --query "user topic"
   ```
3. Open the most relevant Wiki notes based on the search results.
4. Open Raw sources only when the compiled note is insufficient or the user asks for source-level verification.
5. Cite the compiled note and Raw source when the answer depends on source material.
