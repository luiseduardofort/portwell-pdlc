# Verification order

Module 4 decision. Cheapest and most deterministic first, so the scarce layer is never spent on
what a cheap one catches. Every layer is a gate: it has a threshold and it blocks, it does not warn.

| # | Layer | Mechanism here | Catches | Cost | Blocks when |
| -: | :- | :- | :- | :- | :- |
| 1 | Deterministic | `lib/validate_gate.py` (hook, CLI, pre-commit, CI), `exit_checks`, `lib/route_risk.py`, `python3 -m unittest`, `evals/score.py` | Unsigned or forged exits, consents without words, rewritten history, wrong transition, writes to trust anchors, wrong path | Milliseconds, no model | Any violation. Exit code 2 |
| 2 | Specialized agent review | Evidence reviewer, full path only: a separate reviewer applies `skills/approve/evidence-review.md` to the gate pack and writes `gate.evidence_review`. The guard requires `verdict: pass` to advance. In the eval, `evals/grade.py` applies the same criteria with no tools | A gate pack that overstates, a stale fact cited as current, a contradiction quietly resolved, a `risk_inputs` value its source does not support | One model call per gate pack | Rubric score below threshold on any criterion marked blocking |
| 3 | Human | G1 to G4, signed with `lib/sign_gate.py` | Product intent, risk acceptance, objections, waivers. Everything Article 3 reserves to a person | Scarce. The constraint | No signature, or an outcome that is not `build`/`release`/`done` |

## Rules of the order

- Layer 2 runs only on an artifact that passed layer 1. A forged signature is never shown to a
  reviewer, model or person.
- Layer 3 sees the layer 1 result and the layer 2 findings in the gate pack. It is never asked to
  find what a cheaper layer could have found.
- The eval applies the same order to the harness itself: `evals/score.py` first, the rubric only on
  runs that passed it, a human sample last (`evals/README.md`).

## Where the queue forms (workbook 4.8)

At layer 3. OPPORTUNITY-04 has waited on a named person since 2026-07-11 (BLOCKER-01) and past the
G2 deadline of 2026-08-31. Nothing in layers 1 or 2 can shorten that wait. They can only make sure
that when Ana Fialho looks, she looks at a pack that is true. `reports/operating-report.md`
measures the wait.

## Open question: Article 5

The constitution says "No fixture data leaves this machine and no tool reaches a network endpoint."
A live eval sends case text, which is fixture data, to the model provider, as every Claude Code
session does. The group must decide whether Article 5 governs the tools skills may call, or also the
model provider. Until it decides, live runs happen only with a person's explicit authorization.
