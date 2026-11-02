import pypdf
import re

def search_pdf(pdf_path, doc_name):
    print(f"\n=================== SEARCHING {doc_name} ({pdf_path}) ===================")
    reader = pypdf.PdfReader(pdf_path)
    print(f"Total pages: {len(reader.pages)}")
    
    cities_to_search = [
        ("Gangtok", ["Gangtok"]),
        ("Jammu", ["Jammu"]),
        ("Varanasi", ["Varanasi", "Benares", "Banaras"]),
        ("Agra", ["Agra"]),
        ("Port Blair", ["Port Blair", "Portblair"]),
        ("Bhuj", ["Bhuj"]),
        ("Manali", ["Manali"]),
        ("Surat", ["Surat"]),
        ("Bhuntar", ["Bhuntar"]),
        ("Allahabad", ["Allahabad", "Prayagraj"]),
        ("Visakhapatnam", ["Visakhapatnam", "Vishakhapatnam", "Vizag"]),
        ("Bhubaneswar", ["Bhubaneswar", "Bhubaneshwar"])
    ]
    
    # First search which pages mention Climate Zone or Appendix with cities
    climate_pages = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if "Climate Zone" in text or "climatic zone" in text.lower() or "climate zone" in text.lower():
            climate_pages.append(idx + 1)
            
    print(f"Pages mentioning climate zone: {len(climate_pages)} pages: {climate_pages[:15]}...")
    
    # Search each city in all pages, especially table pages
    found_matches = {c[0]: [] for c in cities_to_search}
    
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        lines = text.split("\n")
        for line in lines:
            line_str = line.strip()
            for norm_city, variants in cities_to_search:
                for var in variants:
                    # Match whole word or exact pattern
                    if re.search(r'\b' + re.escape(var) + r'\b', line_str, re.IGNORECASE):
                        # Filter out incidental mentions if possible, but keep all for review
                        found_matches[norm_city].append((idx + 1, line_str))
                        break

    return found_matches

results_ecbc = search_pdf("data/docs/ECBC_2017.pdf", "ECBC 2017")
results_ens = search_pdf("data/docs/ENS_2024.pdf", "ENS 2024")

print("\n" + "="*80)
print("SUMMARY RESULTS FOR TARGET CITIES")
print("="*80)

for norm_city in ["Gangtok", "Jammu", "Varanasi", "Agra", "Port Blair", "Bhuj", "Manali", "Surat", "Bhuntar"]:
    print(f"\n--- {norm_city.upper()} ---")
    ecbc_m = results_ecbc.get(norm_city, [])
    ens_m = results_ens.get(norm_city, [])
    
    print("ECBC 2017 matches:")
    if not ecbc_m:
        print("  NOT_IN_TABLE / No matches")
    else:
        for p, l in ecbc_m[:10]:
            print(f"  [p.{p}] {l}")
            
    print("ENS 2024 matches:")
    if not ens_m:
        print("  NOT_IN_TABLE / No matches")
    else:
        for p, l in ens_m[:10]:
            print(f"  [p.{p}] {l}")
