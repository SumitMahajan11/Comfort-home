# TRACKER

Updated by the agent at the end of every task (see `AGENTS.md`). Last updated: 2026-10-09.

## Phase status

| Phase | Name | Status | Evidence |
|---|---|---|---|
| 0 | Data audit | DONE | `reports/data_audit.md` |
| 1 | EDA and reference baselines | DONE (follow-up in Phase 2) | `reports/phase1_eda.md` |
| 2 | Clean data and comfort models | IN PROGRESS (Splits Built & Verified) | `data/processed/koppen_group_map.csv`, `data/processed/splits.json`, `reports/evidence/splits_assertion_test.txt` |
| 3 | Simulation engine | NOT STARTED | none yet |
| 4 | Coupling and surrogates | NOT STARTED | none yet |
| 5 | Optimization | NOT STARTED | none yet |
| 6 | Explainability and dashboard | NOT STARTED | none yet |
| 7 | Packaging and reporting | NOT STARTED | none yet |

**Next action:** Awaiting human review before launching model training and baseline benchmarking in Phase 2 (`train.py`, `baselines.py`).

## Phase 2 task checklist

- [x] Add `src/` layout, `tests/`, `reports/evidence/`
- [x] Cleaning script and cleaning log (row count after each rule)
- [x] Köppen group mapping file (**human review gate - completed & verified**)
- [x] `splits.json` with building-grouped and leave-one-group-out folds
- [x] No-overlap assertion test, output saved (`reports/evidence/splits_assertion_test.txt`)
- [ ] Baselines on identical rows
- [ ] LogReg, Random Forest, XGBoost, MLP trained and calibrated
- [ ] Ablations A1, A2, A3
- [ ] `reports/phase2_models.md` with S1 pass/fail

## Evidence ledger

| ID | Claim | Source | Date |
|---|---|---|---|
| E-001 | DB II measurements: 109,033 rows x 53 cols; metadata 809 x 23 | `reports/data_audit.md` | 2026-10-09 |
| E-002 | 1,760 EPW files across 476 Indian stations | `reports/data_audit.md` | 2026-10-09 |
| E-003 | EnergyPlus 26.2.0 ran `1ZoneUncontrolled.idf` with New Delhi EPW in 1.24 s, 0 fatal, 0 severe | `data/processed/smoke_test/` | 2026-10-09 |
| E-004 | TSV 3-class balance (global): neutral 47.51%, cool 25.51%, warm 24.35%, missing 2.62% | `reports/phase1_eda.md` | 2026-10-09 |
| E-005 | Complete cases: Set A 58,512 rows (India 2,170); Set B 82,789 (India 18,061) | `reports/evidence/phase2_cleaning_log.txt` | 2026-10-09 |
| E-006 | 12 of 31 raw climate classes have fewer than 3 buildings | `reports/phase1_eda.md` | 2026-10-09 |
| E-007 | Reference baselines, different row subsets (not comparable to ML): PMV macro-F1 0.3999 (full); adaptive 90% 0.4597 (full), 0.4834 (naturally ventilated) | `reports/phase1_eda.md` | 2026-10-09 |
| E-008 | Data cleaning produced 58,512 clean rows x 83 cols with exact step-by-step row counts | `reports/evidence/phase2_cleaning_log.txt`, `data/processed/comfort_clean.parquet` | 2026-10-09 |
| E-009 | Köppen group map maps all 31 raw classes to groups A/B/C/D with min 30 buildings/group | `data/processed/koppen_group_map.csv` | 2026-10-09 |
| E-010 | 5-fold GroupKFold and 4 Leave-One-Group-Out splits built with zero building leakage | `data/processed/splits.json`, `reports/evidence/splits_assertion_test.txt` | 2026-10-09 |

## Decision log

Locked decisions D-001 to D-011 live in `PROJECT_SPEC.md` section 4. Add new decisions here with date and reason.

| ID | Date | Decision | Reason |
|---|---|---|---|
| D-003a | 2026-10-09 | Target uses the agent's cool/neutral/warm cut points (+/-0.5) instead of the earlier +/-1.5 plan | Classes are balanced (about 26/49/25), directional, and well defined |
| D-004a | 2026-10-09 | Confirmed complete-case dataset of 58,512 rows (2,170 India rows) for primary model training; ablation A1 (no tr, 82,789 rows globally, 18,061 in India) tests radiant trade-off | Missing tr in 16,347 raw India rows cannot be imputed as ta (D-005) without masking passive envelope radiation effects |
| D-006a | 2026-10-09 | Climate holdout moved from raw Köppen classes to major groups A/B/C/D | 12 of 31 raw classes have fewer than 3 buildings |

## Open risks

| ID | Risk | Mitigation | Status |
|---|---|---|---|
| R-001 | `tr` missing in 22.27% of rows; excluding it hides radiant effects | Keep `tr` in primary model; A1 ablation quantifies its value; never impute | Open |
| R-002 | Sparse climate classes make holdout unreliable | Major-group holdout (D-006a) | Mitigated in plan |
| R-003 | Shimla has no labelled votes in DB II | Applicability-domain flag (D-011) | Open |
| R-004 | Phase 1 baselines used different subsets | Re-score on identical rows (D-007) | Open |
| R-005 | Jodhpur EPW is ISHRAE2014, others TMYx | Check for a Jodhpur TMYx; else document | Open |
| R-006 | Simulation tooling untested beyond running `energyplus.exe` | Phase 3 smoke tests before the batch | Open |
| R-007 | Agent deleted stray Uluberia EPW files in the root | Human confirms copy exists in `India_Weather_Extracted` | Open |
| R-008 | DB II is mostly non-shelter buildings | Stated limitation | Accepted |
| R-009 | Tropical row loss (53.66% global retention, Group A has 8,968 clean rows out of 22,374 raw tropical rows due to missing `tr`) | Quantified in clean log; major Group A still retains 197 buildings | Open |
| R-010 | India count discrepancy (2,170 complete-case rows vs 18,714 raw rows because 16,347 raw India rows lack `tr`; Set B without `tr` retains 18,061 India rows) | Documented filter trail; A1 ablation tests model performance without `tr` | Open |

## Proposals (agents add here; human decides)

None yet.

## Changelog

- 2026-10-09: Phase 0 and Phase 1 completed. Docs created (`AGENTS.md`, `PROJECT_SPEC.md`, `PHASES.md`, `TRACKER.md`).
- 2026-10-09: Phase 2 Step 1 completed: `src/data/clean.py` created, `data/processed/comfort_clean.parquet` (58,512 rows) and `data/processed/koppen_group_map.csv` generated. Halted at human review gate.
- 2026-10-09: Phase 2 Step 2 completed: Enhanced `koppen_group_map.csv`, resolved India row and invalid value audits, updated `.gitignore`, built `data/processed/splits.json` (5-fold GroupKFold & 4 Leave-One-Group-Out), ran `tests/test_splits.py` with 0 leakage failures. Added D-004a, R-009, R-010 to tracker.
