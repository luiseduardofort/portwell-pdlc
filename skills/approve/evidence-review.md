# Evidence review

Layer 2 of `verification/order.md`. A narrow review of the gate pack, run after the approve skill
has written it and before the decider sees it, only on the full path (`lib/route_risk.py`). It runs
as a separate reviewer: a subagent or a new session given this file and the artifact, never the
session that wrote the pack. The approve skill writes the result to `gate.evidence_review`. The eval
grader (`evals/grade.py`) runs the same criteria.

The reviewer reads only the artifact. It does not read the track repository, it does not fix what
it finds, and it never decides an objection, a consent or a contradiction. It reports.

## Criteria

`<G>` is the gate the stage closes (G2 in 02-discovery, G3 in 05-review).

| # | Criterion | Blocking |
| -: | :- | :- |
| 1 | Every statement in `gate.pack.summary` is supported by a manifest fact, a contradiction or an unknown in the same artifact. Nothing is added | yes |
| 2 | Every contradiction with `depends: <G>` appears in `gate.pack.contradictions` and is still unresolved | yes |
| 3 | `gate.pack.unknown` lists every unknown whose `needed_for` names `<G>` | yes |
| 4 | The pack does not describe an objection as addressed, a consent as given, or a threshold as met when the record says otherwise | yes |
| 5 | No fact cited in the pack is dated before a linked incident without being marked invalidated | yes |
| 6 | `gate.pack.recommendation` is null | yes |
| 7 | Plain declarative English, no em dashes, ISO dates | no |

## Output

Written into `gate.evidence_review` by the approve skill:

```yaml
evidence_review:
  reviewed_on: YYYY-MM-DD
  reviewer: {kind: model, instruction: skills/approve/evidence-review.md}
  criteria: {"1": pass, "2": pass, "3": fail, ...}
  findings: ["criterion 3: unknown 'review date' names G2 and is missing from gate.pack.unknown"]
  verdict: pass        # pass only if no blocking criterion failed
```

A `fail` verdict sends the item back to the skill that wrote the failing section. It is not a stop
for a person unless the finding is a contradiction or an unknown only a person can resolve.
