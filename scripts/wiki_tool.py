import os
import sys
import json
import argparse
import re
from datetime import datetime

WIKI_DIRS = ['Wiki/Topics', 'Wiki/Concepts', 'Wiki/Entities', 'Wiki/Projects', 'Wiki/Logs']
ALLOWED_TAGS = {'topic', 'concept', 'entity', 'project', 'log'}
CATALOG_PATH = 'Wiki/catalog.jsonl'
MANIFEST_PATH = 'Schema/source-manifest.jsonl'
RAW_SOURCES_DIR = 'Raw/Sources'

def parse_frontmatter(content):
    if not content.startswith('---'):
        return None, content
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None, content
    
    fm_text = parts[1]
    body = parts[2]
    
    fm = {}
    lines = fm_text.strip().split('\n')
    current_key = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        if line.startswith('- '):
            if current_key and isinstance(fm[current_key], list):
                val = line[2:].strip().strip('"\'')
                fm[current_key].append(val)
        elif ':' in line:
            k, v = line.split(':', 1)
            k = k.strip()
            v = v.strip()
            current_key = k
            if v == '':
                fm[k] = []
            elif v == '[]':
                fm[k] = []
            elif v.lower() == 'false':
                fm[k] = False
            elif v.lower() == 'true':
                fm[k] = True
            else:
                fm[k] = v.strip('"\'')
    
    return fm, body

def get_files(directory):
    files = []
    if not os.path.exists(directory):
        return files
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            if f.endswith('.md'):
                files.append(os.path.join(root, f).replace('\\', '/'))
    return files

def cmd_doctor():
    print("Running doctor...")
    for d in WIKI_DIRS + [RAW_SOURCES_DIR, 'Schema']:
        if not os.path.exists(d):
            print(f"Missing directory: {d}")
    print(f"Python version: {sys.version}")
    
    wiki_notes = []
    for d in WIKI_DIRS:
        wiki_notes.extend(get_files(d))
    print(f"Wiki notes: {len(wiki_notes)}")
    print(f"Raw sources: {len(get_files(RAW_SOURCES_DIR))}")
    print("Doctor check complete.")

def cmd_build():
    catalog = []
    for d in WIKI_DIRS:
        files = get_files(d)
        for f in files:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
                fm, _ = parse_frontmatter(content)
                if fm:
                    tags = fm.get('tags', [])
                    if isinstance(tags, str): tags = [tags]
                    tag = tags[0] if tags else ''
                    title = os.path.basename(f).replace('.md', '')
                    entry = {
                        "path": f,
                        "title": title,
                        "tag": tag,
                        "topics": fm.get('topics', []),
                        "sources": fm.get('sources', []),
                        "updated": fm.get('updated', '')
                    }
                    catalog.append(entry)
    
    with open(CATALOG_PATH, 'w', encoding='utf-8') as file:
        for c in catalog:
            file.write(json.dumps(c) + '\n')
            
    with open('Wiki/index.md', 'w', encoding='utf-8') as f:
        f.write("# Wiki Index\n\n")
        for d in WIKI_DIRS:
            folder_name = os.path.basename(d)
            f.write(f"- [[{folder_name}/index|{folder_name}]]\n")
            
    for d in WIKI_DIRS:
        folder_name = os.path.basename(d)
        with open(f"{d}/index.md", 'w', encoding='utf-8') as f:
            f.write(f"# {folder_name} Index\n\n")
            files = get_files(d)
            for file in files:
                if not file.endswith("index.md"):
                    name = os.path.basename(file).replace('.md', '')
                    f.write(f"- [[{name}]]\n")

def cmd_lint():
    failed = False
    for d in WIKI_DIRS:
        for f in get_files(d):
            if f.endswith('index.md'): continue
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
                fm, _ = parse_frontmatter(content)
                if not fm:
                    print(f"Missing frontmatter in {f}")
                    failed = True
                    continue
                tags = fm.get('tags', [])
                if isinstance(tags, str): tags = [tags]
                if not set(tags).intersection(ALLOWED_TAGS):
                    print(f"Invalid tags {tags} in {f}. Allowed: {ALLOWED_TAGS}")
                    failed = True
                sources = fm.get('sources', [])
                if isinstance(sources, str): sources = [sources]
                source_count = int(fm.get('source_count', 0))
                if len(sources) != source_count:
                    print(f"source_count ({source_count}) does not match length of sources ({len(sources)}) in {f}")
                    failed = True
                for s in sources:
                    s_path = s
                    if not s_path.startswith('Raw/Sources/'):
                        s_path = f"Raw/Sources/{s_path}"
                    if not s_path.endswith('.md'):
                        s_path += '.md'
                    if not os.path.exists(s_path):
                        print(f"Invalid source link {s} in {f} (path {s_path} not found)")
                        failed = True
    if failed:
        sys.exit(1)
    print("Lint passed.")

def cmd_link_check(fix=False):
    import glob
    all_md = []
    for d in WIKI_DIRS:
        all_md.extend(get_files(d))
    
    valid_titles = {os.path.splitext(os.path.basename(f))[0] for f in all_md}
    
    # Allow linking to agent skills
    if os.path.exists('.agents/skills'):
        valid_titles.update(os.listdir('.agents/skills'))
    
    # Known words used in prose that get caught by the regex
    PROSE_FALSE_POSITIVES = {"wikilinks", "links", "note-name", "skill-name"}
    
    broken = []
    links_from = {}
    
    for f in sorted(all_md):
        title = os.path.splitext(os.path.basename(f))[0]
        links_from[title] = set()
        with open(f, 'r', encoding='utf-8') as file:
            text = file.read()
        links = re.findall(r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', text)
        for link in links:
            link = link.strip()
            if link in PROSE_FALSE_POSITIVES or '/' in link:
                continue # Ignore prose placeholders and path-style links
            if link not in valid_titles:
                broken.append((f, link))
            else:
                links_from[title].add(link)
    
    if broken:
        print(f"❌ BROKEN LINKS FOUND ({len(broken)}):")
        for src, lnk in broken:
            print(f"   {src}  ->  [[{lnk}]]")
        sys.exit(1)
        
    missing_backlinks = []
    for src, targets in links_from.items():
        if src == 'index': continue
        for target in targets:
            if target == 'index': continue
            if target in links_from and src not in links_from[target]:
                missing_backlinks.append((src, target))
                
    if missing_backlinks:
        if fix:
            print(f"🔧 FIXING MISSING BACKLINKS ({len(missing_backlinks)}):")
            from collections import defaultdict
            missing_by_target = defaultdict(list)
            for src, target in missing_backlinks:
                missing_by_target[target].append(src)
                
            name_to_path = {}
            for f in all_md:
                name_to_path[os.path.splitext(os.path.basename(f))[0]] = f
                
            for target, srcs in missing_by_target.items():
                if target not in name_to_path:
                    continue
                fpath = name_to_path[target]
                with open(fpath, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                new_content = content
                if "## Connections" in new_content:
                    lines = new_content.split('\n')
                    conn_idx = -1
                    for i, line in enumerate(lines):
                        if line.startswith("## Connections"):
                            conn_idx = i
                            break
                    insert_idx = len(lines)
                    for i in range(conn_idx + 1, len(lines)):
                        if lines[i].startswith("## ") and i != conn_idx:
                            insert_idx = i
                            break
                    for src in reversed(srcs):
                        lines.insert(insert_idx, f"- [[{src}]]")
                    new_content = '\n'.join(lines)
                else:
                    new_content = new_content.strip() + "\n\n## Connections\n"
                    for src in srcs:
                        new_content += f"- [[{src}]]\n"
                        
                with open(fpath, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                print(f"   Updated {fpath} with {len(srcs)} missing reverse link(s)")
            print("✅ Auto-fix complete. All links are now bidirectional.")
            sys.exit(0)
        else:
            print(f"❌ MISSING BACKLINKS ({len(missing_backlinks)}):")
            for src, target in missing_backlinks:
                print(f"   [[{src}]] links to [[{target}]], but [[{target}]] does not link back.")
            print("Run with --fix to automatically resolve these.")
            sys.exit(1)
        
    print("Link check passed. All links valid and bidirectional.")

ATTACHMENT_FORMATS = {
    ".py": "python",
    ".pdf": "pdf",
    ".ipynb": "notebook",
    ".jpg": "image",
    ".png": "image",
    ".csv": "csv",
    ".json": "json",
    ".xlsx": "spreadsheet"
}

def cmd_attachment_scan():
    """Scan Raw/Sources/attachments/ and report all files needing md summaries."""
    from pathlib import Path
    attachments = Path("Raw/Sources/attachments")
    if not attachments.exists():
        print("Raw/Sources/attachments/ does not exist.")
        return
    results = []
    for f in sorted(attachments.iterdir()):
        if f.suffix.lower() not in ATTACHMENT_FORMATS:
            continue
        if f.name.startswith("."):
            continue
        md_name = f.stem.lower().replace(" ", "-").replace("_", "-") + "-" + f.suffix[1:] + ".md"
        md_path = Path("Raw/Sources") / md_name
        results.append({
            "file": str(f),
            "format": ATTACHMENT_FORMATS[f.suffix.lower()],
            "needs_summary": not md_path.exists(),
            "md_target": str(md_path)
        })
    for r in results:
        status = "\u274c NEEDS SUMMARY" if r["needs_summary"] else "\u2705 has summary"
        print(f"{status} | {r['format']:<12} | {r['file']}")
    pending = sum(1 for r in results if r["needs_summary"])
    print(f"\nTotal attachments: {len(results)} | Pending summaries: {pending}")

def cmd_source_scan(update=False, accept_covered=False):
    manifest = []

    coverage_map = {}
    for d in WIKI_DIRS:
        for f in get_files(d):
            if f.endswith('index.md'): continue
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
                fm, _ = parse_frontmatter(content)
                if fm:
                    sources = fm.get('sources', [])
                    if isinstance(sources, str): sources = [sources]
                    for s in sources:
                        s_path = s
                        if not s_path.startswith('Raw/Sources/'):
                            s_path = f"Raw/Sources/{s_path}"
                        if not s_path.endswith('.md'):
                            s_path += '.md'
                        coverage_map.setdefault(s_path, []).append(f)

    # Build attachment md-summary lookup
    from pathlib import Path
    attachments_dir = Path("Raw/Sources/attachments")
    attachment_md_map = {}
    if attachments_dir.exists():
        for att in attachments_dir.iterdir():
            if att.suffix.lower() not in ATTACHMENT_FORMATS:
                continue
            if att.name.startswith("."):
                continue
            md_name = att.stem.lower().replace(" ", "-").replace("_", "-") + "-" + att.suffix[1:] + ".md"
            md_path = Path("Raw/Sources") / md_name
            attachment_md_map[str(md_path)] = {
                "attachment_path": str(att),
                "format": ATTACHMENT_FORMATS[att.suffix.lower()],
                "md_summary_path": str(md_path) if md_path.exists() else None
            }

    for f in get_files(RAW_SOURCES_DIR):
        # Skip files inside attachments/ subdirectory
        if '/attachments/' in f:
            continue
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            fm, _ = parse_frontmatter(content)
            title = fm.get('Title', os.path.basename(f).replace('.md', '')) if fm else os.path.basename(f).replace('.md', '')
            covered_by = coverage_map.get(f, [])
            processed = len(covered_by) > 0 if accept_covered else (fm.get('Processed', False) if fm else False)
            # Determine format field
            fmt = "markdown"
            if fm and fm.get('format'):
                fmt = fm.get('format')
            elif f in attachment_md_map:
                fmt = attachment_md_map[f]['format']
            has_md_summary = f in attachment_md_map and attachment_md_map[f]['md_summary_path'] is not None
            entry = {
                "path": f,
                "title": title,
                "format": fmt,
                "processed": processed,
                "covered_by": covered_by,
                "updated": datetime.now().strftime("%Y-%m-%d")
            }
            manifest.append(entry)

    # Also scan attachments/ for unprocessed files
    if attachments_dir.exists():
        for att in sorted(attachments_dir.iterdir()):
            if att.suffix.lower() not in ATTACHMENT_FORMATS:
                continue
            if att.name.startswith("."):
                continue
            md_name = att.stem.lower().replace(" ", "-").replace("_", "-") + "-" + att.suffix[1:] + ".md"
            md_path = Path("Raw/Sources") / md_name
            has_md = md_path.exists()
            entry = {
                "path": str(att),
                "format": ATTACHMENT_FORMATS[att.suffix.lower()],
                "has_md_summary": has_md,
                "md_summary_path": str(md_path) if has_md else None,
                "processed": has_md
            }
            manifest.append(entry)

    if update:
        with open(MANIFEST_PATH, 'w', encoding='utf-8') as file:
            for c in manifest:
                file.write(json.dumps(c) + '\n')
    else:
        for m in manifest:
            print(json.dumps(m))

def cmd_source_lint():
    failed = False
    
    manifest = {}
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip():
                    entry = json.loads(line)
                    manifest[entry['path']] = entry

    for f in get_files(RAW_SOURCES_DIR):
        # Skip files inside attachments/ subdirectory
        if '/attachments/' in f:
            continue
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            fm, _ = parse_frontmatter(content)
            if not fm:
                print(f"Missing frontmatter in source {f}")
                failed = True
                continue
            for req in ['Title', 'Reference', 'Created', 'Processed', 'tags']:
                if req not in fm:
                    print(f"Missing required frontmatter {req} in source {f}")
                    failed = True
            
            processed = fm.get('Processed', False)
            if processed:
                entry = manifest.get(f)
                if not entry or len(entry.get('covered_by', [])) == 0:
                    print(f"Source {f} is marked processed but has no Wiki coverage")
                    failed = True

    if failed:
        sys.exit(1)
    print("Source lint passed.")

def cmd_source_delta():
    manifest_paths = set()
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip():
                    manifest_paths.add(json.loads(line)['path'])
    
    for f in get_files(RAW_SOURCES_DIR):
        if f not in manifest_paths:
            print(f"Unmanifested source: {f}")

def cmd_source_coverage():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip():
                    entry = json.loads(line)
                    print(f"{entry['path']}: {entry.get('covered_by', [])}")

def cmd_search_catalog(query):
    query_norm = re.sub(r'[\W_]+', '', query).lower()
    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip():
                    entry = json.loads(line)
                    title_norm = re.sub(r'[\W_]+', '', entry.get('title', '')).lower()
                    topics_norm = [re.sub(r'[\W_]+', '', t).lower() for t in entry.get('topics', [])]
                    if query_norm in title_norm or any(query_norm in t for t in topics_norm):
                        print(json.dumps(entry))

def cmd_log(title, details):
    with open('Wiki/log.md', 'a', encoding='utf-8') as f:
        f.write(f"\n## {title}\n{details}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    
    subparsers.add_parser('doctor')
    subparsers.add_parser('build')
    subparsers.add_parser('lint')
    link_parser = subparsers.add_parser('link-check')
    link_parser.add_argument('--fix', action='store_true', help='Automatically append missing backlinks to ## Connections')
    
    scan_parser = subparsers.add_parser('source-scan')
    scan_parser.add_argument('--update', action='store_true')
    scan_parser.add_argument('--accept-covered', action='store_true')
    
    subparsers.add_parser('source-lint')
    subparsers.add_parser('source-delta')
    subparsers.add_parser('source-coverage')
    subparsers.add_parser('attachment-scan')
    
    search_parser = subparsers.add_parser('search-catalog')
    search_parser.add_argument('--query', required=True)
    
    log_parser = subparsers.add_parser('log')
    log_parser.add_argument('--title', required=True)
    log_parser.add_argument('--details', required=True)
    
    args = parser.parse_args()
    
    if args.command == 'doctor':
        cmd_doctor()
    elif args.command == 'build':
        cmd_build()
    elif args.command == 'lint':
        cmd_lint()
    elif args.command == 'link-check':
        cmd_link_check(args.fix)
    elif args.command == 'source-scan':        cmd_source_scan(args.update, args.accept_covered)
    elif args.command == 'source-lint':
        cmd_source_lint()
    elif args.command == 'source-delta':
        cmd_source_delta()
    elif args.command == 'source-coverage':
        cmd_source_coverage()
    elif args.command == 'attachment-scan':
        cmd_attachment_scan()
    elif args.command == 'search-catalog':
        cmd_search_catalog(args.query)
    elif args.command == 'log':
        cmd_log(args.title, args.details)
