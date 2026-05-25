---
Title: "Termux Guided Installation Setup — Claude Conversation Export"
Reference: "claude-termux-agy-html-export"
format: "html"
source_file: "Raw/Sources/attachments/Termux guided installation setup - Claude (25_5_2026 8：00：20 am).html"
Created: "2026-05-25"
updated: "2026-05-25"
Processed: true
tags:
  - "source"
---

# Termux Guided Installation Setup — Claude Conversation Export

Exported HTML of a Claude.ai conversation dated 2026-05-25. Covers a complete guided setup of Antigravity CLI (`agy`) on a fresh Termux environment on Android (Realme GT 6T / Snapdragon 7+ Gen 3 / ARM aarch64).

---

## Section 1 — Document Summary

- **Title**: Termux guided installation setup
- **Source**: Claude.ai conversation export (HTML)
- **Date**: 2026-05-25 08:00
- **Format**: Exported browser HTML from claude.ai

The conversation walks through installing `agy` on Termux from scratch. It covers all known Android-specific binary compatibility issues: TCMalloc VA-space crash, SIGSYS syscall blocks, ELF header issues, Bionic/glibc conflicts, DNS failures, and TLS CA bundle problems — with surgical fixes for each.

---

## Section 2 — Key Concepts

- **Termux**: Android terminal emulator providing a Linux-like shell environment
- **Antigravity CLI (`agy`)**: AI coding assistant CLI tool by Google DeepMind
- **glibc layer**: Required for running glibc-linked binaries on Android's Bionic libc
- **proot**: Userspace chroot-like tool used to bind mount DNS resolvers
- **VA-space mismatch**: Android uses 39-bit virtual address space; some binaries expect 48-bit
- **SIGSYS / faccessat2**: Android kernel blocks `faccessat2` syscall; binary must be patched
- **TCMalloc**: Memory allocator used by `agy` binary that crashes on Android's limited VA space
- **`LD_PRELOAD`**: Env var that causes Bionic/glibc conflict; must be unset before running `agy`
- **SSL_CERT_FILE**: CA bundle path differs between glibc and Termux; must be set explicitly
- **hash -r**: Bash command to clear cached paths after binary changes

---

## Section 3 — Installation Phases

### Phase 0 — Fresh Termux Bootstrap
```bash
pkg update && pkg upgrade -y
pkg install python proot curl ca-certificates -y
python3 --version; proot --version; curl --version
```

### Phase 1 — Verify glibc Exists
```bash
test -x /data/data/com.termux/files/usr/glibc/lib/ld-linux-aarch64.so.1 && echo "✅ loader OK"
test -f /data/data/com.termux/files/usr/glibc/lib/libc.so.6 && echo "✅ libc.so.6 OK"
# If missing:
pkg install glibc -y
```

### Phase 2 — Install Antigravity CLI
```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
test -x ~/.local/bin/agy && echo "✅ agy binary exists"
file ~/.local/bin/agy  # expect: ELF 64-bit LSB executable, ARM aarch64
```

### Phase 3 — Binary Patch (VA39 script)
A Python script (`patch_agy_va39.py`) surgically patches 6 issues in the binary:
1. TCMalloc VA-space flag → supports 39-bit address space
2. `faccessat2` → `faccessat` syscall substitution
3. ELF loader path → points to Termux glibc loader
4. DNS resolver → proot bind mount workaround
5. `LD_PRELOAD` unset → prevents Bionic/glibc conflict
6. `SSL_CERT_FILE` set → correct CA bundle for TLS

### Phase 4 — Wrapper Function
```bash
# In ~/.bashrc:
agy() {
    unset LD_PRELOAD
    export SSL_CERT_FILE=/data/data/com.termux/files/usr/etc/tls/cert.pem
    hash -r
    ~/.local/bin/agy.va39 "$@"
}
```

### Phase 5 — Verify Working
```bash
agy --version
agy "hello"
```

---

## Section 4 — Key Findings

- The standard `agy` binary cannot run on Android without patching
- glibc layer is required (not included in base Termux — needs `pkg install glibc`)
- Six separate incompatibilities must be fixed, each independently
- `proot` DNS workaround is necessary for name resolution in glibc context
- After patching, `agy` runs stably as a shell function wrapping the patched binary

---

## Section 5 — Connections

- **Related wiki note**: [[termux-agy-setup]] — project note covering this setup
- **Related log**: [[session-2026-05-25]] — session log for 2026-05-25
- **Tools**: `pkg`, `proot`, `curl`, `python3`, `git`, `bash`
