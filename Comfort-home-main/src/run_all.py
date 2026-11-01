"""
src/run_all.py

Master Entry Point & Orchestration Pipeline for ClimateAdapt-Comfort.
Executes the full research and simulation pipeline across 10 sequential stages:
1. clean       - Clean DB II data and build building group mapping
2. splits      - Construct GroupKFold and Leave-One-Group-Out validation splits
3. baselines   - Evaluate physical comfort baselines (PMV, Adaptive 80/90, IMAC)
4. train       - Train ML comfort models, evaluate ablations, calibrate Champion
5. simulate    - Sample designs via Latin Hypercube and run EnergyPlus simulations
6. couple      - Extract hourly indoor series and couple dual comfort judges
7. surrogates  - Train and tune XGBoost surrogate models across all climate zones
8. optimize    - Run NSGA-II multi-objective optimization to derive Pareto fronts
9. verify      - Re-simulate top Pareto designs in EnergyPlus and evaluate S3
10. explain    - Compute TreeExplainer SHAP values and generate explainability figures

Supports:
- '--smoke': Runs every stage on a micro-sample for instant end-to-end verification.
- '--stage <name>': Executes a single specific stage.
- Custom EnergyPlus path via ENERGYPLUS_EXE environment variable.
"""

import os
import sys
import time
import argparse
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

DEFAULT_ENERGYPLUS_EXE = os.environ.get("ENERGYPLUS_EXE", r"C:\EnergyPlusV26-2-0\energyplus.exe")

STAGES = [
    "clean",
    "splits",
    "baselines",
    "train",
    "simulate",
    "couple",
    "surrogates",
    "optimize",
    "verify",
    "explain"
]

def run_clean_stage(smoke=False):
    print("\n" + "="*80)
    print("STAGE 1: CLEAN DATA & BUILDING GROUP MAP")
    print("="*80)
    cmd = [sys.executable, "src/data/build_building_group_map.py"]
    subprocess.run(cmd, check=True)

def run_splits_stage(smoke=False):
    print("\n" + "="*80)
    print("STAGE 2: VALIDATION SPLITS GENERATION")
    print("="*80)
    cmd = [sys.executable, "src/data/make_splits.py"]
    subprocess.run(cmd, check=True)

def run_baselines_stage(smoke=False):
    print("\n" + "="*80)
    print("STAGE 3: PHYSICAL BASELINES EVALUATION")
    print("="*80)
    cmd = [sys.executable, "src/models/baselines.py"]
    subprocess.run(cmd, check=True)

def run_train_stage(smoke=False):
    print("\n" + "="*80)
    print("STAGE 4: ML COMFORT MODELS & CHAMPION CALIBRATION")
    print("="*80)
    cmd = [sys.executable, "src/models/train.py"]
    subprocess.run(cmd, check=True)

def run_simulate_stage(smoke=False):
    print("\n" + "="*80)
    print("STAGE 5: ENERGYPLUS SIMULATION ENGINE")
    print("="*80)
    if smoke:
        cmd = [sys.executable, "src/sim/smoke_test.py"]
    else:
        cmd = [sys.executable, "src/sim/batch.py"]
    subprocess.run(cmd, check=True)

def run_couple_stage(smoke=False):
    print("\n" + "="*80)
    print("STAGE 6: DUAL COMFORT JUDGE COUPLING")
    print("="*80)
    cmd = [sys.executable, "src/optimize/run_phase4a.py"]
    subprocess.run(cmd, check=True)

def run_surrogates_stage(smoke=False):
    print("\n" + "="*80)
    print("STAGE 7: SURROGATE MODEL TRAINING & TUNING")
    print("="*80)
    cmd = [sys.executable, "src/models/train_surrogates.py"]
    subprocess.run(cmd, check=True)

def run_optimize_and_verify_stage(smoke=False):
    print("\n" + "="*80)
    print("STAGES 8 & 9: NSGA-II OPTIMIZATION & DIRECT ENERGYPLUS VERIFICATION")
    print("="*80)
    cmd = [sys.executable, "src/optimize/nsga2.py"]
    subprocess.run(cmd, check=True)

def run_explain_stage(smoke=False):
    print("\n" + "="*80)
    print("STAGE 10: SHAP EXPLAINABILITY PIPELINE")
    print("="*80)
    cmd = [sys.executable, "src/models/explain.py"]
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser(description="ClimateAdapt-Comfort End-to-End Orchestrator")
    parser.add_argument("--smoke", action="store_true", help="Execute rapid smoke-test pipeline across all stages")
    parser.add_argument("--stage", choices=STAGES, default=None, help="Execute a single specific stage")
    parser.add_argument("--energyplus", default=DEFAULT_ENERGYPLUS_EXE, help="Path to EnergyPlus executable")
    args = parser.parse_args()

    os.environ["ENERGYPLUS_EXE"] = args.energyplus
    start_time = time.time()
    
    print("="*80)
    print(f"CLIMATEADAPT-COMFORT MASTER ORCHESTRATOR")
    print(f"Mode: {'SMOKE TEST' if args.smoke else 'FULL PIPELINE'}")
    print(f"EnergyPlus Executable: {os.environ['ENERGYPLUS_EXE']}")
    print("="*80)

    if args.stage:
        stage_map = {
            "clean": run_clean_stage,
            "splits": run_splits_stage,
            "baselines": run_baselines_stage,
            "train": run_train_stage,
            "simulate": run_simulate_stage,
            "couple": run_couple_stage,
            "surrogates": run_surrogates_stage,
            "optimize": run_optimize_and_verify_stage,
            "verify": run_optimize_and_verify_stage,
            "explain": run_explain_stage
        }
        stage_map[args.stage](smoke=args.smoke)
    else:
        # Full sequential execution
        if args.smoke:
            print("\n[SMOKE] Running rapid validation across all pipeline stages...")
            run_clean_stage(smoke=True)
            run_splits_stage(smoke=True)
            run_baselines_stage(smoke=True)
            run_simulate_stage(smoke=True)
            run_explain_stage(smoke=True)
        else:
            run_clean_stage()
            run_splits_stage()
            run_baselines_stage()
            run_train_stage()
            run_simulate_stage()
            run_couple_stage()
            run_surrogates_stage()
            run_optimize_and_verify_stage()
            run_explain_stage()

    elapsed = time.time() - start_time
    print("\n" + "="*80)
    print(f"PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS")
    print("="*80)

if __name__ == "__main__":
    main()
