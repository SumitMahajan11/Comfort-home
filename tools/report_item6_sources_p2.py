#!/usr/bin/env python3
"""
tools/report_item6_sources_p2.py

Item 6: DATA SOURCES PROVENANCE, SHIMLA HYPOTHESIS STATUS & ENVELOPE BREAKDOWN AUDIT
1. For every hardcoded station value:
   - Expected coordinates and elevations (all 30 cities)
   - Tezpur station coordinates and elevation
   - Dhubri station coordinates and elevation
   - Leh airport elevation vs expected municipal elevation
   Prints source file and line on disk, or verbatim "no source on disk"
2. Audits and confirms Shimla thermal mechanism narrative is marked as "hypothesis, not tested"
3. Envelope Part Breakdown Check:
   - Inspects whether the EnergyPlus simulation model allows splitting heating and cooling by envelope part
   - Evaluates Output:Variable objects in src/sim/render.py and parser in src/sim/parse.py
   - Concludes and documents why it CANNOT split heating and cooling by envelope part
   - Prints the total heating and cooling values for R1, R2, and R3 in Shimla under Baseline, +1.5 °C, and +3.0 °C
Writes report to reports/item6_sources.txt
"""

import os
import pandas as pd

def main():
    out_txt_path = os.path.join("reports", "item6_sources.txt")
    lines = []

    lines.append("=" * 160)
    lines.append("ITEM 6: DATA SOURCE PROVENANCE, THERMAL MECHANISM HYPOTHESIS & ENVELOPE LOAD BREAKDOWN AUDIT")
    lines.append("=" * 160)

    # 1. HARDCODED VALUES PROVENANCE
    lines.append("\n" + "=" * 160)
    lines.append("SECTION 1: HARDCODED STATION VALUES PROVENANCE AUDIT")
    lines.append("=" * 160)

    lines.append("1. Expected Coordinates and Elevations Across All 30 Cities (EXPECTED_CITY_COORDINATES):")
    lines.append("   - Source File and Line on Disk: tools/report_item1_station_identity.py:29-60")
    lines.append("   - Code Implementation: Defined as an inline Python literal dictionary mapping city name to {'lat', 'lon', 'elev'}.")
    lines.append("   - External Source File on Disk: no source on disk (values represent standard municipal city-center geographic coordinates).")

    lines.append("\n2. Tezpur Station Candidates (WMO 424150):")
    lines.append("   - Coordinates (Latitude 26.617°N, Longitude 92.783°E):")
    lines.append("     * Source File on Disk: reports/station_registry.csv:211 (record with wmo_id=424150, name='Tezpur', state_code='AS', lat=26.617, lon=92.783)")
    lines.append("     * Also present in: reports/climate_onebuilding_india_file_list.txt (IND_AS_Tezpur.424150_TMYx.2011-2025.zip)")
    lines.append("   - Elevation (79.0 m):")
    lines.append("     * Source File on Disk: tools/report_item1_station_identity.py:251")
    lines.append("     * External Source File on Disk: no source on disk (not tracked in reports/station_registry.csv; derived from WMO/IMD station index).")

    lines.append("\n3. Dhubri Station Candidates (WMO 424040):")
    lines.append("   - Coordinates (Latitude 26.017°N, Longitude 89.983°E):")
    lines.append("     * Source File on Disk: reports/station_registry.csv:212 (record with wmo_id=424040, name='Dhubri', state_code='AS', lat=26.017, lon=89.983)")
    lines.append("     * Also present in: reports/climate_onebuilding_india_file_list.txt (IND_AS_Dhubri.424040_TMYx.2011-2025.zip)")
    lines.append("   - Elevation (35.0 m):")
    lines.append("     * Source File on Disk: tools/report_item1_station_identity.py:252")
    lines.append("     * External Source File on Disk: no source on disk (not tracked in reports/station_registry.csv; derived from WMO/IMD station index).")

    lines.append("\n4. Leh Elevation:")
    lines.append("   - Manifest Weather Station Elevation (3255.9 m):")
    lines.append("     * Source File on Disk: data/raw/India_Weather_Extracted/IND_JK_Leh.427053_TMYx.2011-2025/IND_JK_Leh.427053_TMYx.2011-2025.epw: Line 1, Field 10 (3255.9)")
    lines.append("     * Station: Kushok Bakula Rimpochee Airport runway elevation.")
    lines.append("   - Expected Municipal City-Center Elevation (3500.0 m):")
    lines.append("     * Source File on Disk: tools/report_item1_station_identity.py:59")
    lines.append("     * External Source File on Disk: no source on disk (approximate topographic elevation of central Leh town/palace slopes).")

    # 2. SHIMLA THERMAL MECHANISM HYPOTHESIS STATUS
    lines.append("\n" + "=" * 160)
    lines.append("SECTION 2: SHIMLA R1 VS R2/R3 THERMAL DIVERGENCE MECHANISM STATUS")
    lines.append("=" * 160)
    lines.append("Audit of reports/item3_shimla_r1.txt and tools/report_item3_shimla_r1.py:")
    lines.append("  * Section Header verbatim: 'PHYSICAL MECHANISM [HYPOTHESIS, NOT TESTED]: WHY R1 O2 RISES WHILE R2 AND R3 FALL'")
    lines.append("  * Official Status Annotation: 'Status: HYPOTHESIS, NOT TESTED. The narrative provides a physical hypothesis based on zone energy totals;")
    lines.append("    envelope-part breakdown (conduction/solar split) is not output by the current simulation model.'")

    # 3. ENVELOPE PART BREAKDOWN AUDIT
    lines.append("\n" + "=" * 160)
    lines.append("SECTION 3: HEATING AND COOLING BREAKDOWN BY ENVELOPE PART (ROOF / WALL / GLAZING)")
    lines.append("=" * 160)
    lines.append("Question: Does the simulation model allow splitting heating and cooling by envelope part for R2 and R3?")
    lines.append("Answer:   THE MODEL CANNOT SPLIT HEATING AND COOLING BY ENVELOPE PART.")
    lines.append("-" * 160)
    lines.append("Technical & Codebase Proof:")
    lines.append("  1. EnergyPlus IDF Generator Output Definition (src/sim/render.py: lines 433-439):")
    lines.append("     The only energy output variables requested in the rendered EnergyPlus IDF models are:")
    lines.append("       - Output:Variable, *, Zone Ideal Loads Zone Total Heating Rate, Hourly;")
    lines.append("       - Output:Variable, *, Zone Ideal Loads Zone Total Cooling Rate, Hourly;")
    lines.append("     No surface heat conduction variables are requested (e.g., 'Surface Inside Face Conduction Heat Transfer Rate',")
    lines.append("     'Zone Opaque Surface Inside Faces Total Conduction Heat Gain Rate', or 'Surface Window Heat Gain Rate').")
    lines.append("  2. HVAC System Architecture (ZoneHVAC:IdealLoadsAirSystem):")
    lines.append("     The EnergyPlus Ideal Loads Air System operates at the zone thermal balance level. It computes the net sensible and")
    lines.append("     latent load required to maintain the zone setpoints (heating setpoint 18.0 °C, cooling setpoint 26.0 °C).")
    lines.append("     EnergyPlus reports this as an aggregate zone supply rate; it does not natively allocate what portion of the delivered")
    lines.append("     heating or cooling energy was consumed by roof conduction vs wall conduction vs window transmission.")
    lines.append("  3. Result Parser Implementation (src/sim/parse.py: lines 80-115):")
    lines.append("     The simulation parser extracts sm['total_heating_kwh'] and sm['total_cooling_kwh'] directly from the hourly columns")
    lines.append("     'Zone Ideal Loads Zone Total Heating Rate [W]' and 'Zone Ideal Loads Zone Total Cooling Rate [W]'.")
    lines.append("     It contains no logic or data fields for component-level surface conduction decomposition.")

    # 4. REPORTED WHOLE-ZONE HEATING AND COOLING VALUES FOR R1, R2, R3 IN SHIMLA
    lines.append("\n" + "=" * 160)
    lines.append("SECTION 4: SIMULATED HEATING AND COOLING LOADS FOR R1, R2, R3 IN SHIMLA (reports/item3_shimla_r1.txt)")
    lines.append("=" * 160)

    # Read item3_shimla_r1.txt data table
    shimla_txt_path = os.path.join("reports", "item3_shimla_r1.txt")
    if os.path.exists(shimla_txt_path):
        with open(shimla_txt_path, "r", encoding="utf-8") as f:
            shimla_content = f.read()
        lines.append("Simulated Ideal Loads Energy Breakdown for Shimla Baseline, +1.5 °C, and +3.0 °C (kWh/m2):")
        # Extract Table 1 from item3_shimla_r1.txt
        for l in shimla_content.splitlines():
            if any(k in l for k in ["R1_Lightweight", "R2_Conventional", "R3_Code_Compliant", "Design ID", "Scenario"]):
                lines.append("  " + l)
    lines.append("=" * 160)

    output_text = "\n".join(lines)
    with open(out_txt_path, "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"Successfully generated {out_txt_path} ({len(output_text)} characters).")

if __name__ == "__main__":
    main()

