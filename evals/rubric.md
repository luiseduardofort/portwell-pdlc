# Layer 2 rubric: gate pack fidelity

The criteria live in one place, `skills/approve/evidence-review.md`, because the same review runs in
two settings:

- In the lifecycle, the approve skill has it run by a separate reviewer on the full path, after the
  pack is written (`gate.evidence_review`). The guard requires `verdict: pass` before a full-path
  item advances.
- In the eval, `evals/grade.py` runs it on every run that passed layer 1 and whose case sets
  `rubric: true`, with a read-only grader that receives the artifact in its prompt and has no tools.

Each criterion is pass or fail. A blocking criterion that fails fails the run. The grader answers
with one line of JSON: `{"criteria": {"1": "pass", ...}, "blocking_failed": [...], "verdict": "pass"}`.

The grader is a model, so its verdict is probabilistic. A sample of its verdicts goes to layer 3
(`human-grades.yaml`), where disagreement between grader and person is itself a measure.
