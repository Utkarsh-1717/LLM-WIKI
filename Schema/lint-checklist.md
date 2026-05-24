# Lint Checklist

- [ ] All compiled notes use one of the allowed tags: `topic`, `concept`, `entity`, `project`, `log`.
- [ ] `source_count` accurately reflects the length of the `sources` array.
- [ ] Source links resolve to actual files in `Raw/Sources/`.
- [ ] Raw sources contain `Title`, `Reference`, `Created`, `Processed`, and `tags`.
- [ ] `Processed` is only true if the source is covered by at least one Wiki note.
- [ ] `audit_public.py` passes (no secret leaks).
