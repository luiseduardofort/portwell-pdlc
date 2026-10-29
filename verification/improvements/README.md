# Evidence-based improvements

Module 4 asks for one improvement to the system, made on evidence. This is the protocol. It is the
bounded version of a self-improving harness (workbook 4.7): the evaluator is protected, the write is
small and reversible, every step is recorded, and a person approves.

## Protocol

1. **Evidence.** A recorded baseline (`evals/baseline.json`) and its results file. Name the failure
   the improvement targets, by case, trial and attribution. No improvement without a failure on
   record.
2. **Hypothesis.** One sentence: which component causes the failure, and why.
3. **One change.** A single edit to one skill, one check or one definition. Never to `evals/`,
   `governance/` or a signature. The change is a commit of its own, so it can be reverted alone.
4. **Dev re-run.** `python3 evals/run.py --mode live --set dev --trials 3 --i-authorize-live`. A
   person authorizes it.
5. **Held-out, once.** `--set heldout`. A person authorizes it. Run it once per change. A held-out
   case used to choose a change moves to `dev/` and is replaced.
6. **Decision.** Keep the change only if the dev pass rate of the targeted case improves, no dev
   case falls below its threshold, and no held-out case regresses. A person records the decision in
   the record, with their name and date. Otherwise revert the commit and record why.
7. **New baseline.** If kept: `python3 evals/run.py --record-baseline <the dev results>`. The diff
   of `baseline.json` is the audit trail.

## Record

One file per improvement, `NNN-<short-name>.md`, from `000-template.md`.
