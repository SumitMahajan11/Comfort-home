import pypdf
import re

reader = pypdf.PdfReader('data/docs/ECBC_2017.pdf')
# ECBC 2017 Appendix B: Table 11-1 is on PDF page 201 (0-indexed 200)
txt = reader.pages[200].extract_text()

# Target cities (24 cities)
unverified = {
    # Cold
    "Srinagar": "Cold",
    "Manali": "Cold",
    "Gangtok": "Cold",
    # Composite
    "Jammu": "Composite",
    "Dehradun": "Composite",
    "Lucknow": "Composite",
    "Varanasi": "Composite",
    "Prayagraj": "Composite",
    "Agra": "Composite",
    "Gorakhpur": "Composite",
    "Patna": "Composite",
    "Nagpur": "Composite",
    # Warm-humid
    "Guwahati": "Warm-humid",
    "Dibrugarh": "Warm-humid",
    "Imphal": "Warm-humid",
    "Bhubaneswar": "Warm-humid",
    "Kolkata": "Warm-humid",
    "Visakhapatnam": "Warm-humid",
    "Chennai": "Warm-humid",
    "Surat": "Warm-humid",
    "Kochi": "Warm-humid",
    "Port Blair": "Warm-humid",
    # Hot-dry
    "Bhuj": "Hot-dry",
    "Jaisalmer": "Hot-dry"
}

# Also ENS 2024 Table 62 (PDF page 131)
reader_ens = pypdf.PdfReader('data/docs/ENS_2024.pdf')
txt_ens = reader_ens.pages[130].extract_text()

print("--- RAW TEXT FROM ECBC 2017 PAGE 201 ---")
for line in txt.split("\n"):
    if any(c.lower() in line.lower() for c in unverified.keys()):
        print("  ", line)

print("\n--- RAW TEXT FROM ENS 2024 PAGE 131 ---")
for line in txt_ens.split("\n"):
    if any(c.lower() in line.lower() for c in unverified.keys()):
        print("  ", line)
