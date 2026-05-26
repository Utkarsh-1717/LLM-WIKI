---
tags:
  - "project"
topics: [termux, antigravity, android, binary-patching, agy]
status: evergreen
created: 2026-05-25
updated: 2026-05-26
sources:
  - Raw/Sources/Termux guided installation setup.md
  - Raw/Sources/termux-guided-installation-setup-html.md
source_count: 2
aliases: [agy-setup, antigravity-termux, termux-install]
---

# Termux AGY Setup

Installing Antigravity CLI (`agy`) on Android Termux requires a multi-phase binary patching process. The standard `agy` binary is compiled for standard Linux glibc with 48-bit VA space — Android provides 39-bit VA, Bionic libc, and a restricted kernel. Six distinct incompatibilities must each be fixed.

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
pkg install -y git wget curl python proot termux-tools
```

### Phase 1 — Install glibc Layer
```bash
pkg install -y glibc-repo
pkg install -y glibc
```

### Phase 2 — Download agy Binary
```bash
wget https://github.com/Antigravity-corp/antigravity-cli/releases/latest/download/agy-linux-amd64
chmod +x agy-linux-amd64
```

### Phase 3 — Binary Patches (Two Patches)

**Patch 1 — TCMalloc VA space (39-bit fix):**
```bash
printf '\x00\x00\x00\x80' | dd of=agy-linux-amd64 bs=1 seek=<offset> conv=notrunc
```

**Patch 2 — faccessat2 syscall block:**
```bash
# Replace faccessat2 (439) with faccessat (21) in syscall table
```

### Phase 4 — Wrapper Script
```bash
cat > ~/.local/bin/agy << 'EOF'
#!/bin/bash
unset LD_PRELOAD
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
exec proot --bind=/etc/resolv.conf \
  /path/to/glibc/ld-linux-x86-64.so.2 \
  /path/to/agy-patched "$@"
EOF
chmod +x ~/.local/bin/agy
```

### Phase 5 — Verify
```bash
agy --version
```

## Credentials Setup

All credentials in `~/.quant_env` — see [[agent-rules]] for full list.
```bash
echo 'source ~/.quant_env' >> ~/.bashrc
```

## LLM Wiki Initialized In This Session

The [[llm-wiki]] system was created during this setup session. See [[session-2026-05-25]] for full session log.

## Connections

- [[llm-wiki]] — the system installed alongside agy in this project
- [[agent-rules]] — credentials and hardware rules configured here
- [[quant-agent-system]] — the quant system that agy powers
- [[session-2026-05-25]] — session log for this installation
- [[quant-wiki-system-v1]] — follows on from this project
