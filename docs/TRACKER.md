# TRACKER

Updated by the agent at the end of every task (see `AGENTS.md`). Last updated: 2026-10-09.

## Phase status

| Phase | Name | Status | Evidence |
|---|---|---|---|
| 0 | Data audit | DONE | `reports/data_audit.md` |
| 1 | EDA and reference baselines | DONE (follow-up in Phase 2) | `reports/phase1_eda.md` |
| 2 | Clean data and comfort models | IN PROGRESS (Human Review Gate) | `data/processed/koppen_group_map.csv`, `reports/evidence/phase2_cleaning_log.txt` |
| 3 | Simulation engine | NOT STARTED | none yet |
| 4 | Coupling and surrogates | NOT STARTED | none yet |
| 5 | Optimization | NOT STARTED | none yet |
| 6 | Explainability and dashboard | NOT STARTED | none yet |
| 7 | Packaging and reporting | NOT STARTED | none yet |

**Next action:** Awaiting human review of `data/processed/koppen_group_map.csv` and cleaning log before proceeding with `splits.json` and modeling.

## Phase 2 task checklist

- [x] Add `src/` layout, `tests/`, `reports/evidence/`
- [x] Cleaning script and cleaning log (row count after each rule)
- [x] Köppen group mapping file (**human review gate - READY FOR REVIEW**)
- [ ] `splits.json` with building-grouped and leave-one-group-out folds
- [ ] No-overlap assertion test, output saved
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
| E-005 | Complete cases: Set A 58,512 rows (India 4,642); Set B 82,789 (India 9,796) | `reports/phase1_eda.md` | 2026-10-09 |
| E-006 | 12 of 31 raw climate classes have fewer than 3 buildings | `reports/phase1_eda.md` | 2026-10-09 |
| E-007 | Reference baselines, different row subsets (not comparable to ML): PMV macro-F1 0.3999 (full); adaptive 90% 0.4597 (full), 0.4834 (naturally ventilated) | `reports/phase1_eda.md` | 2026-10-09 |
| E-008 | Data cleaning produced 58,512 clean rows x 83 cols with exact step-by-step row counts | `reports/evidence/phase2_cleaning_log.txt`, `data/processed/comfort_clean.parquet` | 2026-10-09 |
| E-009 | Köppen group map maps all 31 raw classes to groups A/B/C/D with min 30 buildings/group | `data/processed/koppen_group_map.csv` | 2026-10-09 |

## Decision log

Locked decisions D-001 to D-011 live in `PROJECT_SPEC.md` section 4. Add new decisions here with date and reason.

| ID | Date | Decision | Reason |
|---|---|---|---|
| D-003a | 2026-10-09 | Target uses the agent's cool/neutral/warm cut points (+/-0.5) instead of the earlier +/-1.5 plan | Classes are balanced (about 26/49/25), directional, and well defined |
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

## Proposals (agents add here; human decides)

None yet.

## Changelog

- 2026-10-09: Phase 0 and Phase 1 completed. Docs created (`AGENTS.md`, `PROJECT_SPEC.md`, `PHASES.md`, `TRACKER.md`).
- 2026-10-09: Phase 2 Step 1 completed: `src/data/clean.py` created, `data/processed/comfort_clean.parquet` (58,512 rows) and `data/processed/koppen_group_map.csv` generated. Halted at human review gate.
