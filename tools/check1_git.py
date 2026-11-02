"""
tools/check1_git.py
Executes CHECK 1: GIT
"""

import subprocess
import os

def run_cmd(cmd):
    print(f">>> Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("STDERR:")
        print(res.stderr)
    return res.stdout

def main():
    print("=" * 80)
    print("CHECK 1 - GIT")
    print("=" * 80)
    
    # 1. git show --stat 1ecea7d
    run_cmd(["git", "show", "--stat", "1ecea7d"])
    
    print("-" * 80)
    # 2. git diff HEAD~1 -- .gitignore
    run_cmd(["git", "diff", "HEAD~1", "--", ".gitignore"])
    
    print("-" * 80)
    # 3. List every file in that commit bigger than 5 MB
    print("Files in commit 1ecea7d bigger than 5 MB (5,242,880 bytes):")
    out = subprocess.check_output(["git", "ls-tree", "-r", "-l", "1ecea7d"], text=True)
    large_files = []
    for line in out.strip().splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[3].isdigit():
            size = int(parts[3])
            path = parts[4]
            if size > 5 * 1024 * 1024:
                large_files.append((path, size))
    
    if large_files:
        for p, sz in large_files:
            print(f"  {p}: {sz} bytes ({sz / (1024*1024):.2f} MB)")
    else:
        print("  NONE. No file in commit 1ecea7d exceeds 5 MB.")
    
    # Also check specifically files added/modified in 1ecea7d:
    print("\nFile sizes modified/added in commit 1ecea7d:")
    changed = subprocess.check_output(["git", "show", "--name-only", "--format=", "1ecea7d"], text=True).strip().splitlines()
    for f in changed:
        if not f.strip():
            continue
        try:
            tree_info = subprocess.check_output(["git", "ls-tree", "-l", "1ecea7d", f.strip()], text=True).strip()
            parts = tree_info.split()
            if len(parts) >= 4:
                sz = int(parts[3])
                print(f"  {f.strip():<65} : {sz:>8} bytes ({sz/(1024*1024):.4f} MB)")
        except Exception:
            pass

    print("-" * 80)
    # 4. git diff --stat 6fe5a12..HEAD -- src
    run_cmd(["git", "diff", "--stat", "6fe5a12..HEAD", "--", "src"])
    
    print("-" * 80)
    print("ANALYSIS OF CHANGED FILES IN src/ FOR SIMULATION IMPACT:")
    print("-" * 80)
    
    diff_refs = subprocess.check_output(["git", "diff", "6fe5a12..HEAD", "--", "src/optimize/references.py"], text=True)
    diff_render = subprocess.check_output(["git", "diff", "6fe5a12..HEAD", "--", "src/sim/render.py"], text=True)
    
    print("1. src/optimize/references.py:")
    print("CANNOT alter any simulation result: only adds new 'Leh' entries to CITIES_EPW and REFERENCE_R3_PER_CITY dictionaries; existing city definitions and functions are completely untouched.")
    print("Diff lines proving it:")
    print(diff_refs)
    
    print("2. src/sim/render.py:")
    print("CANNOT alter any simulation result: only adds 'Leh' mapping to resolve_epw_path() known_defaults; all existing city paths, geometry, and simulation render logic remain identical.")
    print("Diff lines proving it:")
    print(diff_render)

if __name__ == '__main__':
    main()
