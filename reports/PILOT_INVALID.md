# Pilot Run Invalidation Notice

**Date:** 2026-10-09  
**Status:** INVALIDATED

The initial pilot scaling benchmark executed via `tools/run_pilot_pipeline.py` has been invalidated and retired for the following reasons:

1. **Design Count Reduced:** The pilot used 500 Latin Hypercube sample designs instead of the 1,000 designs specified in the project baseline.
2. **Optuna Hyperparameter Search Truncated:** Surrogate model tuning used 15 trials, 3-fold cross-validation, and restricted search spaces instead of the standard 40 trials and 5-fold CV with the full search space.
3. **Proxy Comfort Formulas:** The coupling stage bypassed the ML Champion comfort model (`evaluate_ml_champion_comfort`) and ASHRAE 55 Adaptive 90% comfort model (`evaluate_adaptive_90_comfort`) across 8,760 hours, substituting in-memory scalar temperature approximations.

All future station processing must execute the full, uncompromising 5-stage pipeline calling `src/` modules directly.
