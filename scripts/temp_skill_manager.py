#!/usr/bin/env python3
"""
Temp-Skill Manager — tracks, lists, promotes, and kills temp-skills.
Usage:
  python3 scripts/temp_skill_manager.py stats
  python3 scripts/temp_skill_manager.py list
  python3 scripts/temp_skill_manager.py promote <skill-name>
  python3 scripts/temp_skill_manager.py kill
"""

import sys
import os
import shutil
from pathlib import Path
from datetime import date

VAULT = Path(__file__).parent.parent
TEMP_DIR = VAULT / "_temp-skills"
PERM_DIR = VAULT / ".agents" / "skills"
ARCHIVE_DIR = TEMP_DIR / "archive"


def parse_frontmatter(path):
    """Parse YAML frontmatter from a markdown file."""
    lines = path.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def get_all_skills():
    skills = []
    for f in TEMP_DIR.glob("*/SKILL.md"):
        fm = parse_frontmatter(f)
        if fm.get("type") == "temp-skill":
            skills.append((f, fm))
    return sorted(skills, key=lambda x: int(x[1].get("use_count", 0)), reverse=True)


def cmd_stats():
    skills = get_all_skills()
    print(f"\nTemp-Skills Stats")
    print(f"─────────────────")
    print(f"Total skills : {len(skills)}")
    if not skills:
        print("No temp-skills found.")
        return
    print(f"\nTop 5 by usage:")
    for f, fm in skills[:5]:
        print(f"  [{fm.get('use_count',0):>4} uses]  {fm.get('name','?')}  —  {fm.get('description','')}")
    newest = sorted(skills, key=lambda x: x[1].get("created", ""), reverse=True)
    if newest:
        print(f"\nNewest : {newest[0][1].get('name')} (created {newest[0][1].get('created')})")
    print()


def cmd_list():
    skills = get_all_skills()
    if not skills:
        print("No temp-skills found.")
        return
    print(f"\n{'Rank':<5} {'Uses':<6} {'Ver':<5} {'Name':<30} {'Last Used':<12} Description")
    print("─" * 90)
    for i, (f, fm) in enumerate(skills, 1):
        print(f"{i:<5} {fm.get('use_count',0):<6} {fm.get('version',1):<5} "
              f"{fm.get('name','?'):<30} {fm.get('last_used','?'):<12} "
              f"{fm.get('description','')}")
    print()


def cmd_promote(name):
    target = TEMP_DIR / name / "SKILL.md"
    if not target.exists():
        print(f"ERROR: Temp-skill '{name}' not found.")
        sys.exit(1)
    dest = PERM_DIR / name
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(target, dest / "SKILL.md")
    shutil.rmtree(TEMP_DIR / name)
    print(f"✅ Promoted '{name}' to .agents/skills/{name}/SKILL.md")
    print(f"   Removed from _temp-skills/")


def cmd_kill():
    skills = get_all_skills()
    print(f"\n⚠️  KILL SWITCH — This will permanently delete ALL {len(skills)} temp-skills.")
    print("This cannot be undone.")
    confirm = input("\nType CONFIRM to proceed: ").strip()
    if confirm != "CONFIRM":
        print("Aborted.")
        sys.exit(0)
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        TEMP_DIR.mkdir()
        (TEMP_DIR / "README.md").write_text("# Temp-Skills\n\nAll temp-skills were deleted via kill switch.\n")
    print(f"✅ All temp-skills deleted.")
    print(f"   _temp-skills/ folder reset.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        cmd_stats()
    elif cmd == "list":
        cmd_list()
    elif cmd == "promote" and len(sys.argv) > 2:
        cmd_promote(sys.argv[2])
    elif cmd == "kill":
        cmd_kill()
    else:
        print(__doc__)
