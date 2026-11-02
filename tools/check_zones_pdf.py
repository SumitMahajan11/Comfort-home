import os
import sys
import re
import pypdf

REPO_ROOT = os.path.abspath(".")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

target_cities = [
    ("Gangtok", ["Gangtok"], "Gang"),
    ("Jammu", ["Jammu"], "Jamm"),
    ("Varanasi", ["Varanasi", "Benares", "Banaras"], "Vara"),
    ("Agra", ["Agra"], "Agra"),
    ("Port Blair", ["Port Blair", "Portblair"], "Port"),
    ("Bhuj", ["Bhuj"], "Bhuj"),
    ("Bhuntar", ["Bhuntar"], "Bhun")
]

pdfs = [
    ("ECBC 2017", "data/docs/ECBC_2017.pdf"),
    ("ENS 2024", "data/docs/ENS_2024.pdf"),
    ("ECSBC 2024", "data/docs/ECSBC_2024.pdf")
]

print("Extracting text from PDFs once...")
pdf_docs = {}
for doc_name, pdf_path in pdfs:
    if os.path.exists(pdf_path):
        print(f"Reading {doc_name} ({pdf_path})...")
        reader = pypdf.PdfReader(pdf_path)
        pages_text = []
        for p_idx, page in enumerate(reader.pages):
            t = page.extract_text() or ""
            pages_text.append(t)
        pdf_docs[doc_name] = pages_text

print("\n" + "=" * 100)
print("ITEM 5: PDF TEXT SEARCH FOR CLIMATE ZONE SPECIFICATION")
print("=" * 100)

city_results = {}

for norm_name, spellings, prefix in target_cities:
    print(f"\n{'*'*80}\nCITY: {norm_name.upper()}\n{'*'*80}")
    print(f"Spellings searched: {spellings}")
    print(f"Prefix (first 4 letters) searched: '{prefix}'")
    
    hits = []
    for doc_name, pages_text in pdf_docs.items():
        for p_idx, page_text in enumerate(pages_text):
            lines = page_text.split("\n")
            for line_idx, line in enumerate(lines):
                # Search prefix as word start
                m_pref = re.search(r'\b' + re.escape(prefix), line, re.IGNORECASE)
                m_spell = any(re.search(r'\b' + re.escape(s) + r'\b', line, re.IGNORECASE) for s in spellings)
                if m_pref or m_spell:
                    start = max(0, line_idx - 1)
                    end = min(len(lines), line_idx + 2)
                    context_lines = [lines[k].strip() for k in range(start, end)]
                    hits.append({
                        'doc': doc_name,
                        'page': p_idx + 1,
                        'line': line_idx + 1,
                        'matched_line': line.strip(),
                        'context': context_lines
                    })
    
    city_results[norm_name] = hits
    if not hits:
        print("  NO HITS FOUND in any PDF.")
    else:
        for h in hits:
            print(f"\n  [HIT in {h['doc']}, Page {h['page']}, Line {h['line']}]:")
            for cl in h['context']:
                print(f"    | {cl}")

# Print summary table of zone_source
print("\n" + "=" * 80)
print("ZONE SOURCE DETERMINATION PER CITY")
print("=" * 80)
# A city is STANDARD if it appears in ECBC Table 11-1 or ENS Appendix defining climate zones.
# Otherwise, it is ASSUMED.
