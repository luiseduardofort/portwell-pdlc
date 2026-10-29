# Risk model

Module 4 decision. The rule lives in `states/routing.yaml` and runs as `lib/route_risk.py`. This
page explains it. Where the two disagree, the YAML wins.

## Why

A full lifecycle on a trivial item is waste. A fast path on a dangerous item is risk. Portwell has
no rule at all today: DECISION-0028 took the pilot to 28 accounts as "a scope change to the existing
pilot rather than a launch", which is a routing decision made by naming, not by profile.

## Inputs

The four routing inputs of the workbook, read from the artifact. Never from who asks or how urgent
they say it is.

| Workbook input | PDLC reading | Where it comes from |
| :- | :- | :- |
| Specification quality | Open contradictions and unknowns the next gate depends on | Computed: `contradictions[].depends`, `unknowns[].needed_for` |
| Pattern coverage | A complete DECISION record of the same type exists to follow | `route_note.risk_inputs.prior_decision_of_type`, with source |
| Blast radius | Accounts in scope against POLICY-08 (25). Regions under POLICY-03 | `route_note.risk_inputs.accounts`, `.personal_data_regions`, with source |
| Novelty | Item type: pilot, mvp and new-product are novel | Header `type` |

Plus reversibility, because a deprecation or a contractual effect is hard to undo.

## Rule

Any rule that fires sends the item to the full path. An input that is `unknown` fires its rule.
Not knowing the account count is not evidence that it is small.

| Path | Means |
| :- | :- |
| fast | Short decision draft, deterministic checks, decider's signature, consents only where a policy names an owner |
| full | Every gate, every derived consent, the evidence reviewer before the gate, an explicit review date |

## OPPORTUNITY-04 today

`python3 lib/route_risk.py lifecycle/02-discovery/OPPORTUNITY-04.yaml --gate G2` returns `full`.
Fired: R1 and R2 (account count and regions not recorded in `risk_inputs`), R3 (four G2
contradictions open: 1, 2, 6, 8), R4 (three unknowns name G2), R6 and R7 (not recorded). The
artifact predates `risk_inputs`, so four of the six firings are "unknown". That is the rule working,
not a defect: the route skill has to record those values with a source before the path can change.

## Limits

- The thresholds are policy numbers (25 accounts) or zero. None was calibrated on data. There is
  one item.
- `prior_decision_of_type` and `reversibility` are declared by the route skill. They have a source
  field, but nothing checks that the source says what the value says. That is the evidence
  reviewer's job (see `order.md`).
