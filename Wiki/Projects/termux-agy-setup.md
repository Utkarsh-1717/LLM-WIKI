---
tags:
  - "project"
topics:
  - "termux"
  - "antigravity"
status: seed
created: "2026-05-25"
updated: "2026-05-25"
sources:
  - "Raw/Sources/Termux guided installation setup.md"
source_count: 1
aliases: []
---

# Termux AGY Setup

To install Antigravity CLI (agy) on Termux, a multi-phase patching process is required due to architecture and library differences (e.g. 39-bit VA limits, missing glibc by default).

## Steps Summary

1. **Bootstrap**: Install `python`, `proot`, `curl`, `ca-certificates`.
2. **glibc**: Install `glibc-repo`, then `glibc`.
3. **Download**: Use the official curl install script to get the `agy` binary.
4. **Patch**: Run a Python script to patch the `agy` binary (fixes memory allocation, mmap alignment, and faccessat2 syscalls).
5. **Shim**: Symlink the Termux `libc.so.6` as a shim.
6. **Wrapper**: Create an `agy-va39` wrapper script using `proot` to bind DNS and TLS paths.
7. **Profile**: Add aliases to `.bashrc` so `agy` runs via the wrapper.
