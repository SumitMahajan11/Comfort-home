"""
tools/run_leh_pipeline.py

Master execution pipeline for LEH:
1. Stage 1: Pilot simulation (1,000 LHS designs, 2,000 E+ runs), surrogate training (Optuna 40 trials), NSGA-II (Pop=100, Gen=200, Seed=42, Clamped).
2. Stage 2: Active learning loop (3 rounds, 100 designs per round, per-stage timing, surrogate retraining, Gen=200 NSGA-II).
3. Stage 3: Baselines (R1/R2/R3) + Summary table generation (Table 1: Baselines vs Verified vs 100 Candidates with Top<5C and Top>35C; Table 2: Error metrics abs & % median O2; Table 3: Final verified Pareto front; Table 4: Bound positioning analysis).
"""

import os
import sys
import subprocess
import time

def run_step(script_name):
    print(f"\n{'#'*80}")
    print(f"RUNNING: {script_name}")
    print(f"{'#'*80}\n")
    t0 = time.time()
    res = subprocess.run([sys.executable, script_name], check=True)
    elapsed = time.time() - t0
    print(f"\n{script_name} FINISHED in {elapsed:.2f} s ({elapsed/60:.2f} min).\n")

def main():
    t_start = time.time()
    print("STARTING FULL LEH REPRODUCIBLE PIPELINE")
    run_step("tools/run_leh_pilot.py")
    run_step("tools/run_active_learning_leh.py")
    run_step("tools/run_leh_baselines_and_summary.py")
    tot_elapsed = time.time() - t_start
    print(f"\n{'='*80}")
    print(f"LEH COMPLETE IN {tot_elapsed:.2f} s ({tot_elapsed/60:.2f} min).")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()
