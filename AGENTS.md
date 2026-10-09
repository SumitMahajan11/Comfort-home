# AGENTS.md: rules for every AI agent session in this repo

Project: ClimateAdapt-Comfort. Repo root: `D:\Projects\Comfort home`. Shell: Windows PowerShell.

**Start of every session, read in this order:**
1. `docs/PROJECT_SPEC.md` (what we are building, locked decisions)
2. `docs/PHASES.md` (what each phase must deliver and how it is verified)
3. `docs/TRACKER.md` (current status, risks, evidence)

## Hard rules

1. **Evidence gating.** Never state a number, result, or "done" without literal command output behind it. Save that output under `reports/evidence/` and reference the file. If you did not run it, write `Not verified`. Files under `reports/evidence/` are written only by re-running the producing command; never hand-edited.
2. **Raw data is immutable.** Never edit, move, rename, or delete anything under `data/raw/`. All derived files go to `data/processed/`.
3. **Stay in the current phase.** Work only on the phase marked `IN PROGRESS` in `docs/TRACKER.md`. Do not start the next phase.
4. **Locked decisions are not yours to change.** If a decision looks wrong, add an entry under "Proposals" in `docs/TRACKER.md` with the evidence, then stop and ask the human.
5. **No random train/test splits.** Use only the grouped splits defined in Phase 2 (`data/processed/splits.json`). Assert in code that no `building_id` appears in both train and test.
6. **Free and local only.** No paid APIs, no cloud credits, no accounts requiring payment.
7. **Reproducible.** Fixed seed `42`. Code lives in `src/`, run via documented commands. No logic that exists only in a notebook or a one-off `python -c`.
8. **Do not fabricate to fill gaps.** Missing data stays missing unless the spec says how to handle it. No imputing `tr = ta`.
9. **Failures are reported, not hidden.** Failed runs, bad metrics, and negative results go in the report as they are.

## End of every task (mandatory)

1. Update `docs/TRACKER.md`: task checkboxes, evidence ledger rows (claim, evidence file, date), new risks, changelog line.
2. Print the final `git diff --stat` (or file list if not a git repo) and the tracker rows you changed.
3. Finish with: **What ran** (commands) / **Literal results** / **What failed** / **Not verified** / **Next action**.

## Style

- Plain, short reports. Tables for metrics. No claims of superiority without a same-rows comparison.
- Every report states the data path, row counts after each filter, and the seed.
