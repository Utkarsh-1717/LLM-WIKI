import os
import sys

def audit():
    failed = False
    for root, _, files in os.walk("."):
        if ".git" in root: continue
        for file in files:
            path = os.path.join(root, file)
            if "id_rsa" in file or ".pem" in file or "secret" in file.lower():
                print(f"Audit failed: potential secret found in {path}")
                failed = True
            
            if ".obsidian/plugins" in path or ".obsidian/cache" in path:
                print(f"Audit failed: obsidian plugin/cache state found in {path}")
                failed = True
                
    if failed:
        sys.exit(1)
    print("Audit passed.")

if __name__ == "__main__":
    audit()
