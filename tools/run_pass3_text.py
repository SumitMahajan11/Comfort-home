"""
Closure Pass 3 - Item 4: Text Audit
Recomputes Jodhpur and Jaisalmer ground-temp max/mean from variables.
Produces verbatim git log -S DEFAULT_GROUND_TEMP output.
Cites the source file for the Expected coordinates columns.
"""
from pathlib import Path
import subprocess
import sys
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.sim.render import parse_epw_ground_temperatures

def main():
    lines = []
    lines.append("=" * 120)
    lines.append("PASS 3 - ITEM 4: GROUND TEMPERATURE RECOMPUTATION, GIT AUDIT & EXPECTED CITATION")
    lines.append("=" * 120)
    lines.append("")

    # 1. Jodhpur and Jaisalmer ground temps
    jod_rel = "data/raw/India_Weather_Extracted/IND_RJ_Jodhpur.423390_TMYx.2011-2025/IND_RJ_Jodhpur.423390_TMYx.2011-2025.epw"
    jai_rel = "data/raw/India_Weather_Extracted/IND_RJ_Jaisalmer.423280_TMYx.2011-2025/IND_RJ_Jaisalmer.423280_TMYx.2011-2025.epw"

    jod_path = REPO_ROOT / jod_rel
    jai_path = REPO_ROOT / jai_rel

    jod_gt = parse_epw_ground_temperatures(str(jod_path))
    jai_gt = parse_epw_ground_temperatures(str(jai_path))

    lines.append("1. GROUND TEMPERATURE RECOMPUTATION FROM VARIABLES (EPW Header at 0.5 m depth)")
    lines.append("-" * 120)

    for city_name, rel_path, gt_dict in [("Jodhpur", jod_rel, jod_gt), ("Jaisalmer", jai_rel, jai_gt)]:
        lines.append(f"City: {city_name}")
        lines.append(f"  EPW Path: {rel_path}")
        for depth in [0.5, 2.0, 4.0]:
            if depth in gt_dict:
                vals = gt_dict[depth]
                mean_val = float(np.mean(vals))
                max_val = float(np.max(vals))
                min_val = float(np.min(vals))
                max_month = int(np.argmax(vals)) + 1
                min_month = int(np.argmin(vals)) + 1
                month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                lines.append(f"  Depth {depth:.1f} m:")
                lines.append(f"    Monthly Temperatures (C) [Jan-Dec]: {vals}")
                lines.append(f"    Mean Temperature : {mean_val:.2f} C ({mean_val:.4f} C)")
                lines.append(f"    Maximum Temperature: {max_val:.2f} C (Month {max_month}: {month_names[max_month-1]})")
                lines.append(f"    Minimum Temperature: {min_val:.2f} C (Month {min_month}: {month_names[min_month-1]})")
        lines.append("")

    lines.append("=" * 120)
    lines.append("2. LITERAL GIT LOG OUTPUT: git log -S DEFAULT_GROUND_TEMP")
    lines.append("=" * 120)
    proc = subprocess.run(
        ["git", "log", "-S", "DEFAULT_GROUND_TEMP"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    lines.append(proc.stdout.strip())
    lines.append("")
    lines.append("-" * 120)
    lines.append("Note on D-035: The commit messages of c33a954 and 6fe5a12 explicitly cite (D-035) in their subjects:")
    lines.append("  - c33a954: 'feat(sim): implement EPW ground temperature parsing for building surfaces (D-035)'")
    lines.append("  - 6fe5a12: 'feat(pilot): complete Shimla pilot and active learning loop under D-035'")
    lines.append("")

    lines.append("=" * 120)
    lines.append("3. SOURCE CITATION FOR 'EXPECTED' TABLE COLUMNS")
    lines.append("=" * 120)
    lines.append("The 'Expected Lat', 'Expected Lon', and 'Expected Elev' columns in the station identity table")
    lines.append("are derived directly from the project's canonical specification dictionary in:")
    lines.append("  Source File : tools/report_item1_station_identity.py")
    lines.append("  Lines       : 29-60")
    lines.append("  Variable    : EXPECTED_CITY_COORDINATES")
    lines.append("  Definition  : Mapping of canonical city names to expected (Latitude, Longitude, Elevation_m).")
    lines.append("=" * 120)

    out_file = REPO_ROOT / "reports" / "pass3_text.txt"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_file}")

if __name__ == "__main__":
    main()
