"""
tools/claims_audit.py

Automated evidence audit script for ClimateAdapt-Comfort.
Extracts numerical claims from reports/final_results.md and README.md,
verifies that each appears in literal evidence files under reports/evidence/,
and reports any unmatched numbers.
"""

import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVIDENCE_DIR = os.path.join(REPO_ROOT, "reports", "evidence")
DOCS_TO_AUDIT = [
    os.path.join(REPO_ROOT, "reports", "final_results.md"),
    os.path.join(REPO_ROOT, "README.md")
]

# Patterns to ignore (years, versions, standard section numbers, markdown table syntax)
IGNORE_NUMBERS = {
    '2026', '2026-10-09', '10', '09', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
    '3.13', '3.13.7', '26.2.0', '1.0', '5.0', '2.1.0', '80', '100', '150', '200', '500', '1000'
}

def load_all_evidence_text():
    all_text = ""
    for root, _, files in os.walk(EVIDENCE_DIR):
        for f in files:
            if f.endswith(".txt") or f.endswith(".csv") or f.endswith(".json") or f.endswith(".log"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as file:
                        all_text += f"\n--- {f} ---\n" + file.read()
                except Exception as e:
                    print(f"Warning: could not read {path}: {e}")
    return all_text

def extract_numbers_from_doc(doc_path):
    with open(doc_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Find numbers with decimals, percentages, or comma-separated integers
    # e.g., 58,512, 0.4939, -0.0154, 39.08%, 240.47, 43.69
    raw_matches = re.findall(r'[-+]?\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|[-+]?\b\d+\.\d+\b', text)
    
    unique_numbers = []
    for m in raw_matches:
        clean = m.strip('+')
        if clean not in IGNORE_NUMBERS and len(clean) > 1:
            if clean not in unique_numbers:
                unique_numbers.append(clean)
    return unique_numbers

def run_claims_audit():
    print("="*80)
    print("CLIMATEADAPT-COMFORT: EVIDENCE CLAIMS AUDIT")
    print("="*80)
    
    evidence_corpus = load_all_evidence_text()
    
    total_claims = 0
    total_verified = 0
    unmatched_records = []
    
    for doc in DOCS_TO_AUDIT:
        doc_rel = os.path.relpath(doc, REPO_ROOT)
        print(f"\nAuditing claims in: {doc_rel}")
        numbers = extract_numbers_from_doc(doc)
        print(f"  Extracted {len(numbers)} numerical claims.")
        
        doc_verified = 0
        doc_unmatched = []
        
        for num in numbers:
            total_claims += 1
            # Search for number or its raw unformatted integer
            num_clean = num.replace(',', '')
            num_pattern = re.escape(num)
            num_clean_pattern = re.escape(num_clean)
            
            # Check if num or num_clean is in evidence corpus
            if re.search(num_pattern, evidence_corpus) or re.search(num_clean_pattern, evidence_corpus):
                doc_verified += 1
                total_verified += 1
            else:
                doc_unmatched.append(num)
                unmatched_records.append((doc_rel, num))
                
        print(f"  -> Verified: {doc_verified}/{len(numbers)} ({doc_verified/len(numbers)*100:.1f}%)")
        if doc_unmatched:
            print(f"  -> Unmatched numbers ({len(doc_unmatched)}): {doc_unmatched}")
            
    print("\n" + "="*80)
    print(f"AUDIT SUMMARY: {total_verified}/{total_claims} claims verified ({total_verified/total_claims*100:.1f}%)")
    print("="*80)
    
    out_path = os.path.join(EVIDENCE_DIR, "phase7_claims_audit_output.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("PHASE 7 CLAIMS AUDIT EVIDENCE OUTPUT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Total Numerical Claims Extracted: {total_claims}\n")
        f.write(f"Total Verified in Literal Evidence: {total_verified}\n")
        f.write(f"Verification Pass Rate: {total_verified/total_claims*100:.2f}%\n\n")
        if unmatched_records:
            f.write("UNMATCHED NUMBERS:\n")
            for doc, num in unmatched_records:
                f.write(f"  - {doc}: {num}\n")
        else:
            f.write("ALL NUMERICAL CLAIMS 100% MATCHED IN EVIDENCE FILES.\n")
            
    print(f"Saved audit log to {out_path}")
    return len(unmatched_records) == 0

if __name__ == "__main__":
    success = run_claims_audit()
    sys.exit(0 if success else 1)
