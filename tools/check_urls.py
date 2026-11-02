import os
import re

content_path = r"C:\Users\SUMIT\.gemini\antigravity-ide\brain\b09c13ca-8bc8-4b7a-9872-b61c6c7989f9\.system_generated\steps\1094\content.md"
with open(content_path, "r", encoding="utf-8") as f:
    text = f.read()

# Pattern matching relative url to zip
matches = re.findall(r'href="([^"]*?IND_[^"]*?\.zip)"', text)
file_to_relpath = {}
for m in matches:
    fname = os.path.basename(m)
    file_to_relpath[fname] = m

print(f"Mapped {len(file_to_relpath)} files to relative paths.")
# Check a few
for k in list(file_to_relpath.keys())[:5]:
    print(k, "->", file_to_relpath[k])
