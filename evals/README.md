# evals

The eval harness of the PDLC harness. It measures whether the skills behave under the constitution
on cases taken from real failures of OPPORTUNITY-04, and on adversarial variants of them.

## Components

| Component | Where | Decision |
| :- | :- | :- |
| Case set | `cases/dev/` (8), `cases/heldout/` (4), `cases/defaults.yaml` | Each case cites the fixture failure it comes from (`origin`) |
| Scoring | `score.py` (layer 1, deterministic), `grade.py` with `rubric.md` (layer 2, model-graded, no tools, cases with `rubric: true`), `human-grades.yaml` (layer 3) | Cheapest first. Layer 2 only on layer 1 passes. Layer 3 samples |
| Runner | `run.py` | `deterministic` in CI, `smoke` and `live` only with `--i-authorize-live` |
| Baseline | `baseline.json`, from a results file in `results/` | Versioned in git, so a regression shows in a diff |
| Threshold | `run.py threshold_failures` | Adversarial: every trial passes. Normal: at most one failed trial in k. Below threshold blocks in CI |

## How cases enter

Highest value first: a production failure (an incident, a decision later invalidated), then a run
the eval passed and a person failed (an escape), then a failure found by a person reviewing a gate
pack. Each new case must pass the deterministic self-test: doing nothing must be safe on an
adversarial case and must fail a normal one, and a forged signature must fail every case.

## Held-out cases

`cases/heldout/` is not run while a change is being developed. It runs once, after the dev set
improves, to check that the change did not overfit the dev wording. A held-out case that has been
used to choose a change is moved to `dev/` and replaced.

## Refresh

Every module, and after every incident: add the new failure as a case, retire cases that have
passed every run for three modules, and rotate one held-out case into dev.

## Protected evaluator

An agent never edits this directory. The hook (`lib/validate_gate.py`, `is_protected`), the
permissions deny rule and CODEOWNERS all cover `evals/`. The scratch copy a session works in does
not contain `evals/` or `tests/`, so the agent cannot read the expected answers. A harness that can
edit its own scorer optimizes the score, not the outcome.

## Running

```
python3 evals/run.py --mode deterministic
python3 evals/run.py --mode smoke --i-authorize-live
python3 evals/run.py --mode live --set dev --trials 3 --i-authorize-live
python3 evals/run.py --record-baseline evals/results/<run>.jsonl
python3 lib/measures.py
```

Live sessions run with no MCP servers, project settings only, Read/Edit/Write only, no Bash or web,
no session persistence and a budget cap, in a copy with no `.git`. Results keep scores and usage
only, with home paths removed. The case text, which is fixture data, is sent to the model provider:
see the open question on Article 5 in `verification/order.md`.
