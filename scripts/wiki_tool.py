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

    for f in get_files(RAW_SOURCES_DIR):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            fm, _ = parse_frontmatter(content)
            title = fm.get('Title', os.path.basename(f).replace('.md', '')) if fm else os.path.basename(f).replace('.md', '')
            covered_by = coverage_map.get(f, [])
            processed = len(covered_by) > 0 if accept_covered else (fm.get('Processed', False) if fm else False)
            entry = {
                "path": f,
                "title": title,
                "processed": processed,
                "covered_by": covered_by,
                "updated": datetime.now().strftime("%Y-%m-%d")
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
                    print(f"{entry['path']}: {entry['covered_by']}")

def cmd_search_catalog(query):
    query = query.lower()
    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip():
                    entry = json.loads(line)
                    if query in entry.get('title', '').lower() or any(query in t.lower() for t in entry.get('topics', [])):
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
    
    scan_parser = subparsers.add_parser('source-scan')
    scan_parser.add_argument('--update', action='store_true')
    scan_parser.add_argument('--accept-covered', action='store_true')
    
    subparsers.add_parser('source-lint')
    subparsers.add_parser('source-delta')
    subparsers.add_parser('source-coverage')
    
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
    elif args.command == 'source-scan':
        cmd_source_scan(args.update, args.accept_covered)
    elif args.command == 'source-lint':
        cmd_source_lint()
    elif args.command == 'source-delta':
        cmd_source_delta()
    elif args.command == 'source-coverage':
        cmd_source_coverage()
    elif args.command == 'search-catalog':
        cmd_search_catalog(args.query)
    elif args.command == 'log':
        cmd_log(args.title, args.details)
