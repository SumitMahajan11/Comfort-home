import pytest
import numpy as np
import pandas as pd
from tools.run_city_pipeline import compute_non_dominated_front

def test_pareto_front_assembly_dedup():
    """
    Synthetic front test containing:
    (i) a repeated design ID (row 0 and row 1 have same ID and params)
    (ii) two different IDs with identical parameter vectors (row 0 and row 2)
    (iii) two near-duplicates that must NOT be removed (row 3 and row 4 differ by < 1e-3)
    """
    base_params = {
        'roof_insulation_thickness': 0.050,
        'wall_insulation_thickness': 0.025,
        'wall_mass_class': 'medium',
        'roof_solar_absorptance': 0.3000,
        'wwr': 0.2000,
        'orientation': 0.0,
        'shading_depth': 0.400,
        'ventilation_ach': 2.00,
    }

    # Near duplicate params (differs slightly by 0.0001, within near-duplicate 1e-3 relative tolerance)
    near_params = base_params.copy()
    near_params['wwr'] = 0.2001

    # Tradeoff params for non-dominance
    tradeoff_params = base_params.copy()
    tradeoff_params['roof_insulation_thickness'] = 0.100

    data = [
        # (i) & (ii) Row 0: Original D1
        {
            'design_id': 'D1',
            **base_params,
            'O1_ml': 10.0,
            'O1_adapt': 10.0,
            'O2': 20.0
        },
        # (i) Row 1: Repeated design ID D1 with identical params and objectives
        {
            'design_id': 'D1',
            **base_params,
            'O1_ml': 10.0,
            'O1_adapt': 10.0,
            'O2': 20.0
        },
        # (ii) Row 2: Different ID D2 with identical parameter vector and identical objectives
        {
            'design_id': 'D2',
            **base_params,
            'O1_ml': 10.0,
            'O1_adapt': 10.0,
            'O2': 20.0
        },
        # (iii) Row 3: Tradeoff design D3
        {
            'design_id': 'D3',
            **tradeoff_params,
            'O1_ml': 8.0,
            'O1_adapt': 12.0,
            'O2': 22.0
        },
        # (iii) Row 4: Near-duplicate D4 to D3 (must NOT be dropped, parameters differ)
        {
            'design_id': 'D4',
            **{**tradeoff_params, 'wwr': 0.2001},
            'O1_ml': 8.01,
            'O1_adapt': 11.99,
            'O2': 21.99
        }
    ]

    df_synth = pd.DataFrame(data)

    # Compute assembled Pareto front
    result = compute_non_dominated_front(df_synth)

    # Assert expected output: exactly 3 rows kept: D1 (first occurrence), D3, and D4
    assert len(result) == 3, f"Expected 3 designs after dedup, got {len(result)}"
    assert list(result['design_id']) == ['D1', 'D3', 'D4'], f"Expected ['D1', 'D3', 'D4'], got {list(result['design_id'])}"

    # Assert no parameter duplicates remain
    param_cols = [
        'roof_insulation_thickness',
        'wall_insulation_thickness',
        'wall_mass_class',
        'roof_solar_absorptance',
        'wwr',
        'orientation',
        'shading_depth',
        'ventilation_ach'
    ]
    assert not result.duplicated(subset=param_cols).any(), "Duplicate parameter vectors still present!"

