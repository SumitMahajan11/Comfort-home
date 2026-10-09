"""
Latin Hypercube Sampler for Single-Zone Shelter Design Variables.
Generates reproducible design parameter samples for EnergyPlus simulations.
Fixed seed 42.
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc

DESIGN_VARIABLE_RANGES = {
    'roof_insulation_thickness': (0.0, 0.150),  # meters (0 to 150 mm)
    'wall_insulation_thickness': (0.0, 0.150),  # meters (0 to 150 mm)
    'wall_mass_class': ['light', 'medium', 'heavy'],
    'roof_solar_absorptance': (0.30, 0.90),
    'wwr': (0.05, 0.40),                       # Window-to-wall ratio (5% to 40%)
    'orientation': (0.0, 359.0),                # degrees
    'shading_depth': (0.0, 1.0),               # meters (0 to 1.0 m)
    'ventilation_ach': (1.0, 15.0)             # Air changes per hour
}

def sample_designs(n_samples=1000, seed=42):
    """
    Generates n_samples using Latin Hypercube Sampling.
    Returns a pandas DataFrame of design variables with design_id.
    """
    continuous_vars = [
        'roof_insulation_thickness',
        'wall_insulation_thickness',
        'roof_solar_absorptance',
        'wwr',
        'orientation',
        'shading_depth',
        'ventilation_ach'
    ]
    
    # 7 continuous dimensions + 1 discrete dimension (wall_mass_class)
    n_dim = len(continuous_vars) + 1
    sampler = qmc.LatinHypercube(d=n_dim, seed=seed)
    unit_samples = sampler.random(n=n_samples)
    
    df_samples = pd.DataFrame()
    df_samples['design_id'] = [f"D_{i:05d}" for i in range(n_samples)]
    
    # Scale continuous variables
    for i, var_name in enumerate(continuous_vars):
        low, high = DESIGN_VARIABLE_RANGES[var_name]
        df_samples[var_name] = unit_samples[:, i] * (high - low) + low
        
    # Scale discrete variable (wall_mass_class: 0->light, 1->medium, 2->heavy)
    mass_classes = DESIGN_VARIABLE_RANGES['wall_mass_class']
    discrete_idx = np.floor(unit_samples[:, -1] * len(mass_classes)).astype(int)
    discrete_idx = np.clip(discrete_idx, 0, len(mass_classes) - 1)
    df_samples['wall_mass_class'] = [mass_classes[idx] for idx in discrete_idx]
    
    return df_samples

if __name__ == "__main__":
    df_test = sample_designs(n_samples=10, seed=42)
    print("Sampled 10 designs:")
    print(df_test.to_string(index=False))
