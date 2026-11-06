"""
tools/export_paper_tables_to_web.py

Exports all canonical paper tables and methods text into structured typed JSON artifacts
for the Next.js web application (`web/src/data/` and `web/public/data/`).
"""

import os
import json
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_SRC_DATA = REPO_ROOT / "web" / "src" / "data"
WEB_PUB_DATA = REPO_ROOT / "web" / "public" / "data"
PAPER_TABLES = REPO_ROOT / "paper" / "tables"
PAPER_METHODS = REPO_ROOT / "paper" / "methods_and_limitations.md"

WEB_SRC_DATA.mkdir(parents=True, exist_ok=True)
WEB_PUB_DATA.mkdir(parents=True, exist_ok=True)

def save_json(data, filename):
    for target_dir in [WEB_SRC_DATA, WEB_PUB_DATA]:
        target_path = target_dir / filename
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    print(f" [OK] Exported {filename}")

def run_export():
    print("=" * 80)
    print("Exporting Paper Tables and Methods to Web Frontend")
    print(f"Paper Tables: {PAPER_TABLES}")
    print(f"Target: {WEB_SRC_DATA}")
    print("=" * 80)

    # 1. Table 1 (30 Cities) merged with Table 5 coordinates
    df_t1 = pd.read_csv(PAPER_TABLES / "table1_results_30_cities.csv")
    df_t5 = pd.read_csv(PAPER_TABLES / "table5_weather_provenance.csv")
    
    merged_30 = pd.merge(
        df_t1,
        df_t5[["city", "station_name", "wmo", "latitude", "longitude", "elevation_m"]],
        on="city",
        how="left"
    )
    records_30 = merged_30.to_dict(orient="records")
    save_json(records_30, "results_30_cities.json")

    # 2. Table 2 (Flagship Climate Robustness)
    df_t2 = pd.read_csv(PAPER_TABLES / "table2_flagship_robustness.csv")
    records_t2 = df_t2.to_dict(orient="records")
    save_json(records_t2, "table2_flagship_robustness.json")

    # 3. Table 3 (Spearman Rank Correlation Preservation)
    df_t3 = pd.read_csv(PAPER_TABLES / "table3_spearman_rho.csv")
    records_t3 = df_t3.to_dict(orient="records")
    save_json(records_t3, "table3_spearman_rho.json")

    # 4. Table 4 (Reference Shelters vs Optimized)
    df_t4 = pd.read_csv(PAPER_TABLES / "table4_reference_vs_optimized.csv")
    records_t4 = df_t4.to_dict(orient="records")
    save_json(records_t4, "table4_reference_vs_optimized.json")

    # 5. Table 5 (Weather Station Provenance)
    records_t5 = df_t5.to_dict(orient="records")
    save_json(records_t5, "table5_weather_provenance.json")

    # 6. Parse Methods & Limitations into structured sections
    if PAPER_METHODS.exists():
        raw_md = PAPER_METHODS.read_text(encoding="utf-8")
        
        # Extract sections
        sections = []
        current_title = "Overview"
        current_lines = []
        
        for line in raw_md.splitlines():
            if line.startswith("## ") or line.startswith("### "):
                if current_lines:
                    sections.append({
                        "title": current_title,
                        "content": "\n".join(current_lines).strip()
                    })
                    current_lines = []
                current_title = line.lstrip("#").strip()
            else:
                current_lines.append(line)
        if current_lines:
            sections.append({
                "title": current_title,
                "content": "\n".join(current_lines).strip()
            })

        save_json({
            "raw_markdown": raw_md,
            "sections": sections
        }, "methods_and_limitations_content.json")

    print("\n[SUCCESS] All paper assets exported to web frontend successfully!")

if __name__ == "__main__":
    run_export()

