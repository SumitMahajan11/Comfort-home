# Phase 2 Report: Clean Data, Comfort Models, and Baselines

**Date:** 2026-10-09  
**Status:** COMPLETE (Acceptance checks verified, literal output saved)  
**Evidence Files:**
- `reports/evidence/phase2_cleaning_log.txt`
- `reports/evidence/splits_assertion_test.txt`
- `reports/evidence/phase2_baselines_output.txt`
- `reports/evidence/phase2_models_output.txt`
- `data/processed/building_group_map.csv`
- `data/processed/splits.json`
- `models/champion_comfort_model.joblib`

---

## 1. Executive Summary & Success Criterion S1

| Assessment | Result | Required | Status |
|---|---|---|---|
| **D-012 Champion ML Model** | **Ablation A3 (XGBoost + Outdoor Temp)** (Mean Holdout A/B Macro-F1 = **0.4785**) | Highest mean macro-F1 on Holdouts A & B | **Selected** |
| **Primary Core Feature ML Model** | **XGBoost CC** (Mean Holdout A/B Macro-F1 = **0.4517**) | Core complete-case features (`ta, tr, rh, vel, clo, met`) | **Evaluated** |
| **Best Baseline Model** | **Adaptive 90% Acceptability** (Mean Holdout A/B Macro-F1 = **0.4939**) | PMV / Adaptive 80% / Adaptive 90% | **Benchmark** |
| **Success Criterion S1** | Margin = **-0.0154** (A3 vs Adaptive 90%) / **-0.0422** (Core XGB vs Adaptive 90%) | ML beats best baseline by $\ge +0.05$ macro-F1 | **FAIL (Honest Negative Result)** |

> [!NOTE]
> Per **AGENTS.md Hard Rule 9** and **PROJECT_SPEC.md Section 9**, negative results are reported plainly without fabrication. On group-held-out evaluation across climate zones (Tropical & Arid), field occupants exhibit strong adaptive behavior captured directly by the ASHRAE 55 Adaptive model (macro-F1 0.4939). Adding outdoor temperature context to ML (Ablation A3) raises ML performance from 0.4517 to 0.4785, but fails to clear the +0.05 margin requirement over the adaptive baseline on out-of-distribution climate holdouts.

---

## 2. Dataset Splitting & Zero-Leakage Integrity

- **Valid TSV Dataset (`comfort_tsv_all.parquet`):** 106,171 rows across 806 buildings.
- **Complete-Case Dataset (`comfort_clean.parquet`):** 58,512 rows across 610 buildings.
- **Evaluation Rule (D-007):** 100% of ML models and physical baselines are evaluated on **identical test rows** across all splits.

### Zero-Leakage Assertion Test Output
From `reports/evidence/splits_assertion_test.txt`:
```text
================================================================================
NO-LEAKAGE AND EVALUATION INTEGRITY ASSERTION TESTS ON SPLITS
================================================================================
Total TSV rows: 106,171 | Total Complete-Case rows: 58,512 | Distinct Buildings: 806

--- 1. Testing 5-Fold GroupKFold (by building_id) ---
  [PASS] fold_0: Train=644 bldgs (84,936 TSV rows) | Test=162 bldgs (12,548 complete cases) | Overlap=0
  [PASS] fold_1: Train=645 bldgs (84,937 TSV rows) | Test=161 bldgs (12,223 complete cases) | Overlap=0
  [PASS] fold_2: Train=645 bldgs (84,937 TSV rows) | Test=161 bldgs (11,882 complete cases) | Overlap=0
  [PASS] fold_3: Train=645 bldgs (84,937 TSV rows) | Test=161 bldgs (10,569 complete cases) | Overlap=0
  [PASS] fold_4: Train=645 bldgs (84,937 TSV rows) | Test=161 bldgs (11,290 complete cases) | Overlap=0
  [PASS] 5-Fold GroupKFold cleanly partitions exact 806 buildings and 58,512 complete-case test rows.

--- 2. Testing Leave-One-Köppen-Major-Group-Out ---
  [PASS] holdout_A_tropical (Group A: Tropical): Train=553 bldgs (84,317 TSV rows) | Test=253 bldgs (8,968 complete cases) | Overlap=0
  [PASS] holdout_B_arid (Group B: Arid): Train=635 bldgs (89,861 TSV rows) | Test=171 bldgs (7,890 complete cases) | Overlap=0
  [PASS] holdout_C_temperate (Group C: Temperate): Train=464 bldgs (45,720 TSV rows) | Test=342 bldgs (36,136 complete cases) | Overlap=0
  [PASS] holdout_D_continental (Group D: Continental): Train=766 bldgs (98,615 TSV rows) | Test=40 bldgs (5,518 complete cases) | Overlap=0
  [PASS] All 4 Leave-One-Group-Out holdout sets strictly isolated with zero building leakage.
```

---

## 3. Physical Baselines Benchmark (Identical Test Rows)

All baselines were executed with `pythermalcomfort` using ISO 7730 / ASHRAE 55 equations without input truncation (`limit_inputs=False`).

| Split | Test Rows / Bldgs | PMV Macro-F1 (95% CI) | Adaptive 80% Macro-F1 (95% CI) | Adaptive 90% Macro-F1 (95% CI) |
|---|---|---|---|---|
| **Fold 0** | 12,548 / 162 | 0.4087 [0.3610, 0.4709] | 0.3889 [0.2895, 0.4864] | 0.4377 [0.3502, 0.5204] |
| **Fold 1** | 12,223 / 161 | 0.4480 [0.4068, 0.4817] | 0.3868 [0.3001, 0.4596] | 0.4434 [0.3722, 0.4930] |
| **Fold 2** | 11,882 / 161 | 0.4512 [0.4129, 0.4884] | 0.3868 [0.3340, 0.4469] | 0.4244 [0.3703, 0.4816] |
| **Fold 3** | 10,569 / 161 | 0.4241 [0.3914, 0.4574] | 0.3979 [0.3249, 0.4692] | 0.4343 [0.3755, 0.4905] |
| **Fold 4** | 11,290 / 161 | 0.4338 [0.3946, 0.4672] | 0.3894 [0.3268, 0.4495] | 0.4588 [0.4035, 0.4949] |
| **5-Fold CV Mean** | **58,512 / 610** | **0.4332 ± 0.0156** | **0.3900 ± 0.0041** | **0.4397 ± 0.0114** |
| **Holdout A (Tropical)** | 8,968 / 253 | 0.4598 [0.4123, 0.4800] | 0.4174 [0.3445, 0.4516] | 0.4565 [0.3845, 0.4850] |
| **Holdout B (Arid)** | 7,890 / 171 | 0.4765 [0.4066, 0.5349] | 0.5625 [0.4594, 0.6211] | 0.5313 [0.4311, 0.6032] |
| **Holdout C (Temperate)** | 36,136 / 342 | 0.4212 [0.4021, 0.4423] | 0.3450 [0.3123, 0.3832] | 0.4060 [0.3735, 0.4405] |
| **Holdout D (Continental)** | 5,518 / 40 | 0.3866 [0.3246, 0.5068] | 0.3342 [0.2490, 0.4514] | 0.4066 [0.3222, 0.4967] |
| **D-012 Mean A & B** | **16,858 / 424** | **0.4681** | **0.4899** | **0.4939** |

---

## 4. Machine Learning Models Benchmark

Models trained with fixed seed `42`, class weighting for imbalance, and Optuna tuning inside training partitions only.

### 5-Fold GroupKFold Cross-Validation (In-Distribution Building Holdout)

| Model | Mean Macro-F1 (± Std) | Fold 0 | Fold 1 | Fold 2 | Fold 3 | Fold 4 |
|---|---|---|---|---|---|---|
| **Logistic Regression** | 0.4357 ± 0.0182 | 0.4284 | 0.4650 | 0.4442 | 0.4187 | 0.4223 |
| **MLP Classifier** | 0.4538 ± 0.0046 | 0.4578 | 0.4542 | 0.4510 | 0.4485 | 0.4573 |
| **Ablation A1 (No $T_r$)** | 0.4564 ± 0.0144 | 0.4589 | 0.4746 | 0.4646 | 0.4462 | 0.4377 |
| **XGBoost NaN-Tolerant (D-004a)** | 0.4580 ± 0.0155 | 0.4640 | 0.4782 | 0.4616 | 0.4496 | 0.4367 |
| **Random Forest** | 0.4614 ± 0.0169 | 0.4567 | 0.4866 | 0.4689 | 0.4495 | 0.4452 |
| **XGBoost CC (Primary Core)** | **0.4649 ± 0.0137** | 0.4644 | 0.4861 | 0.4725 | 0.4534 | 0.4483 |
| **Ablation A3 (Outdoor Temp)** | **0.4733 ± 0.0052** | 0.4764 | 0.4770 | 0.4660 | 0.4783 | 0.4690 |
| **Ablation A2 (Cooling Type)** | 0.3127 ± 0.0079 | 0.3087 | 0.3113 | 0.3197 | 0.3204 | 0.3032 |

---

### Leave-One-Köppen-Major-Group-Out Holdouts (Out-of-Distribution Transfer)

| Model | Holdout A (Tropical) | Holdout B (Arid) | Holdout C (Temperate) | Holdout D (Continental) | **D-012 Mean A & B** |
|---|---|---|---|---|---|
| **Ablation A2 (Cooling Type)** | 0.3165 [0.2947, 0.3374] | 0.2597 [0.2265, 0.2884] | 0.3393 [0.3233, 0.3554] | 0.3323 [0.2787, 0.3500] | 0.2881 |
| **Logistic Regression** | 0.4178 [0.3781, 0.4426] | 0.4371 [0.3598, 0.5179] | 0.4329 [0.4144, 0.4496] | 0.3658 [0.3129, 0.4669] | 0.4274 |
| **XGBoost NaN-Tolerant (D-004a)** | 0.4252 [0.3893, 0.4457] | 0.4552 [0.3874, 0.5209] | 0.4111 [0.3930, 0.4282] | 0.3547 [0.3164, 0.4395] | 0.4402 |
| **MLP Classifier** | 0.3479 [0.3106, 0.3646] | 0.5338 [0.4411, 0.6009] | 0.4134 [0.3954, 0.4339] | 0.3477 [0.3064, 0.4161] | 0.4408 |
| **Ablation A1 (No $T_r$)** | 0.4235 [0.3792, 0.4587] | 0.4711 [0.4015, 0.5336] | 0.4086 [0.3914, 0.4266] | 0.3507 [0.3166, 0.4208] | 0.4473 |
| **Random Forest** | 0.4381 [0.4006, 0.4622] | 0.4621 [0.3870, 0.5323] | 0.4072 [0.3888, 0.4258] | 0.3554 [0.3169, 0.4324] | 0.4501 |
| **XGBoost CC (Primary Core)** | 0.4304 [0.3939, 0.4562] | 0.4730 [0.4013, 0.5393] | 0.4190 [0.4016, 0.4359] | 0.3603 [0.3206, 0.4231] | **0.4517** |
| **Ablation A3 (Outdoor Temp)** | 0.4741 [0.4247, 0.5103] | 0.4829 [0.4075, 0.5533] | 0.3915 [0.3631, 0.4209] | 0.4055 [0.3523, 0.4514] | **0.4785** |

---

## 5. Decision D-012 Selection & Key Physical Findings

### 1. D-012 Selection
Per Decision D-012:
- The model selected as the pipeline champion for Phase 4 coupling is **Ablation A3 (XGBoost with Outdoor Temperature)** with Mean Holdout A/B Macro-F1 = **0.4785**.
- The primary environmental-only model (complete-case features `ta, tr, rh, vel, clo, met`) is **XGBoost CC** with Mean Holdout A/B Macro-F1 = **0.4517**.
- Serialized champion artifact: `models/champion_comfort_model.joblib`.

### 2. Radiant Temperature Verification (D-005 & Ablation A1)
- Removing mean radiant temperature $T_r$ in Ablation A1 caused an immediate drop in 5-fold CV macro-F1 (0.4649 $\to$ 0.4564) and Holdout A/B score (0.4517 $\to$ 0.4473).
- This confirms that $T_r$ provides essential independent physical signal for radiant discomfort. Never imputing $T_r = T_a$ (Decision D-005) is validated.

### 3. Cooling Type Overfitting (Ablation A2)
- Introducing categorical cooling type caused catastrophic collapse under climate holdout (Mean A/B macro-F1 collapsed to 0.2881). In DB II, cooling strategy is strongly confounded with geographic regions; conditioning directly on discrete cooling categories causes the tree to memorize regional conventions rather than physical heat balance.

### 4. Outdoor Thermal History (Ablation A3)
- Including outdoor prevailing temperature lifted Holdout A (Tropical) macro-F1 from 0.4304 to 0.4741 and Holdout D (Continental) from 0.3603 to 0.4055. This aligns directly with adaptive thermal comfort theory: occupant comfort sensation shifts with seasonal outdoor temperatures.

---

## 6. Confusion Matrices (Holdouts A & B)

### Champion Model (Ablation A3) on Holdout A (Tropical)
| True \ Pred | Cool (-1) | Neutral (0) | Warm (+1) | Recall |
|---|---|---|---|---|
| **Cool (-1)** (1,348 rows) | 513 | 424 | 411 | **38.06%** |
| **Neutral (0)** (4,036 rows) | 682 | 2,294 | 1,060 | **56.84%** |
| **Warm (+1)** (3,584 rows) | 545 | 1,407 | 1,632 | **45.54%** |

### Champion Model (Ablation A3) on Holdout B (Arid)
| True \ Pred | Cool (-1) | Neutral (0) | Warm (+1) | Recall |
|---|---|---|---|---|
| **Cool (-1)** (1,778 rows) | 1,330 | 258 | 190 | **74.80%** |
| **Neutral (0)** (3,678 rows) | 1,223 | 920 | 1,535 | **25.01%** |
| **Warm (+1)** (2,434 rows) | 260 | 480 | 1,694 | **69.60%** |
