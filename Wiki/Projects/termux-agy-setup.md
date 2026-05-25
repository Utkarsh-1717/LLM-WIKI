---
tags:
  - "project"
topics:
  - "termux"
  - "antigravity"
  - "android"
  - "binary-patching"
status: evergreen
created: "2026-05-25"
updated: "2026-05-25"
sources:
  - "Raw/Sources/Termux guided installation setup.md"
  - "Raw/Sources/termux-guided-installation-setup-html.md"
source_count: 2
aliases:
  - "agy-setup"
  - "antigravity-termux"
---

# Termux AGY Setup

Installing Antigravity CLI (`agy`) on Android Termux requires a multi-phase binary patching process. The standard `agy` binary is compiled for a standard Linux glibc environment with 48-bit VA space — Android provides 39-bit VA, Bionic libc (not glibc), and a restricted kernel. Six distinct incompatibilities must each be fixed.

## Why Patching Is Required

| Problem | Root Cause | Fix |
|---|---|---|
| TCMalloc crash | Android uses 39-bit VA, binary expects 48-bit | Binary patch |
| SIGSYS crash | Android blocks `faccessat2` syscall | Binary patch |
| Invalid ELF header | Termux's `libc.so` is a text script | Symlink shim |
| Bionic/glibc conflict | Termux injects Android lib into Linux binary | `unset LD_PRELOAD` |
| DNS failure | glibc binary can't see Termux's resolver | `proot` bind mount |
| TLS failure | CA bundle path differs | `SSL_CERT_FILE` env var |

## Installation Phases

### Phase 0 — Bootstrap Fresh Termux
```bash
pkg update && pkg upgrade -y
pkg install python proot curl ca-certificates -y
# Verify:
python3 --version && proot --version && curl --version
```

### Phase 1 — Install glibc Layer
```bash
test -x /data/data/com.termux/files/usr/glibc/lib/ld-linux-aarch64.so.1 \
  && echo "✅ loader OK" || echo "❌ MISSING"
test -f /data/data/com.termux/files/usr/glibc/lib/libc.so.6 \
  && echo "✅ libc.so.6 OK" || echo "❌ MISSING"
# If missing:
pkg install glibc -y
```

### Phase 2 — Download Binary
```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
test -x ~/.local/bin/agy && echo "✅ agy binary exists"
file ~/.local/bin/agy  # → ELF 64-bit LSB executable, ARM aarch64
```

### Phase 3 — Binary Patch (va39 script)
Run `patch_agy_va39.py` — patches 6 offsets in the binary:
1. TCMalloc VA-space limit → 39-bit
2. `faccessat2` → `faccessat` syscall
3. ELF loader path → Termux glibc loader
4. DNS resolver → proot bind mount
5. Remove `LD_PRELOAD` contamination
6. Set correct CA bundle path

### Phase 4 — Wrapper Function in ~/.bashrc
```bash
agy() {
    unset LD_PRELOAD
    export SSL_CERT_FILE=/data/data/com.termux/files/usr/etc/tls/cert.pem
    hash -r
    ~/.local/bin/agy.va39 "$@"
}
```

### Phase 5 — Verify
```bash
agy --version
agy "hello"
```

## Post-Setup: LLM Wiki Initialization

After `agy` is running, the Quant LLM Wiki (`LLM-WIKI`) was initialized:
- Core skills created: `fyers-auth`, `fyers-historical`, `kaggle-notebook-run`, `kaggle-db-update`
- Multi-format ingest extension added: `.py .pdf .ipynb .jpg .png .csv .json .xlsx`
- Maintenance gate established: `doctor → build → lint → source-lint → attachment-scan → audit_public`

## Connections

- [[llm-wiki]] — wiki system running on this setup
- [[session-2026-05-25]] — session log covering this work
- [[multi-format-ingest]] — attachment ingestion system built on this device
