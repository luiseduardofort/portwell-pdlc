# What this repository is

Module 3 asks for the terms to be defined at first use. This page does that for the group.

## Three things that are easy to confuse

| Term | Means here | In this repository |
| :- | :- | :- |
| Coding-agent harness | The runtime that runs the model in a loop with tools: Claude Code. It supplies context loading, tools, permissions, hooks, subagents | Not built here. Configured through `.claude/settings.json` |
| Agentic Delivery System (ADS) | The organization-specific system that turns intent into accepted change through one or more harnesses. It owns lifecycle state, routing, context, controls, verification, approvals, evidence and learning | This repository. The Portwell PDLC is its lifecycle |
| Meta-harness | Two competing meanings. (1) The organizational layer above a harness: skills, hooks, conventions, evals. That overlaps with the ADS control layer. (2) A harness that edits its own scaffolding and validates the change, which the course calls a self-improving harness | We use ADS for (1). We do not build (2). The one bounded improvement in Module 4 is made by a person under `verification/improvements/` |

## The control layer, by workbook item

| ADS control layer element (Module 3, 3.2) | Where |
| :- | :- |
| Lifecycle stages and named skills | `states/`, `skills/` |
| Versioned project context | `CLAUDE.md`, `skills/constitution/SKILL.md`, `lifecycle/` |
| Specification formats | `states/schema.yaml`, `states/*/template.yaml` |
| Task routing | `states/routing.yaml`, `lib/route_risk.py` |
| Quality and approval gates | G1 to G4, `lib/validate_gate.py`, `lib/sign_gate.py` |
| Reusable specialist instructions | `skills/approve/evidence-review.md` |
| Metrics, retrospectives and learning | `evals/`, `lib/measures.py`, `reports/`, `verification/improvements/` |
| Provider adapters | `.claude/` is the only adapter. Everything in `lib/`, `states/`, `governance/`, `evals/` and `.github/` runs without Claude Code |

Principle 8 says the methodology should survive a change of harness. The test is concrete: delete
`.claude/` and the guard, the signatures, the CI, the eval scoring and the measures still run. What
is lost is local prevention (the hook, permissions and sandbox) and the live eval runner, which
calls `claude -p`. A second harness would need its own adapter for those two.

## Which framework the group borrows from

Module 3 asks each participant to name the control problem their team most needs solved, pick the
framework that addresses it, and say what is lost. The design borrows deliberately, with this
repository as the single lifecycle owner:

| Borrowed from | Pattern | Where |
| :- | :- | :- |
| GitHub Spec Kit | A constitution and a traceable artifact chain | `skills/constitution/SKILL.md`, one artifact per stage |
| Superpowers | Verification as a skill, review before advancing | `skills/verify/`, the evidence review |
| BMAD | Variable planning depth by work profile | Two-speed routing |

What is not borrowed: any framework's own state, gates or commands. Stacking them would duplicate
artifacts and contradict the gates (Module 3, 3.3).

Each participant's choice, to be filled in by that person:

| Participant | Control problem the team most needs solved | Framework | What would be lost |
| :- | :- | :- | :- |
| Luis Fortunato | | | |
| Bruna Goulart | | | |
| Tabi Thuler | | | |
| Guilherme Losso | | | |
