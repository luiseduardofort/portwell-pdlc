---
name: route
description: Proposes the item's type, lists the policies its facts trigger, runs the deterministic checks with input and result, and derives who must sign the next gate. Proposes release waves. Never decides the type or the label of a change.
---

# Route

## Purpose
Turn the manifest into a route: what kind of item this is, which company rules it touches, who
therefore has to sign, and how it could be released. The route is a proposal. A person confirms
it at the gate.

## Parameters
`item`, `stage`. Runs in 01-backlog for `type_hypothesis`, in 02-discovery for `route_note`, and
in 05-review for `policy_check` and the wave plan.

## Entry conditions
- Context has run in this stage and `evidence_manifest` is written.
- `states/types.yaml` and `docs/Policies.docx` are readable.

## Reads
- `states/types.yaml`, `states/<stage>/definition.yaml`.
- `evidence_manifest`, `stakeholder_positions`, `decision_draft` if it exists.
- `docs/Policies.docx`, for the literal condition of each policy, its owner, its status and its
  supersession date.
- `data/people/headcount.xlsx`, to write roles as the company records them.

## Prohibited context
- Any reading of a policy beyond its literal text. Where the text and the case do not match
  cleanly, that is a contradiction to record, not a judgment to make.
- Any source outside the two repositories.

## Writes
`route_note` in 02-discovery: `type_proposed`, `type_rationale`, `policies_triggered`,
`deterministic_checks`, `signatories_g2`, `signatories_g3`, `waves_proposed`, `risk_inputs`,
`path`. `policy_check` in
05-review. `opportunity.type_hypothesis` in 01-backlog.

## Never writes
`type` in the header, which changes only when G2 is signed. Any label such as "scope change" or
"launch" as a conclusion. Any signature.

## Procedure
1. Type. Read `states/types.yaml`. Match the manifest against each type's purpose: a feasibility
   question is a poc, a time-boxed learning release with criteria is a pilot, an increment on
   something in monitoring is a feature, a withdrawal is a deprecation. Write `type_proposed` and
   a `type_rationale` that cites manifest IDs. Where two types fit, write both and stop for the
   decider.
2. Policies. For each policy in `docs/Policies.docx`, test its literal condition against the
   manifest. POLICY-01: is this a billing answer to a Business or Enterprise account. POLICY-03:
   does customer data leave the EU region. POLICY-08: does the account count exceed 25.
   POLICY-11: is a resolution time being quoted. Write each triggered policy with `why`, its
   `owner` as the document names them, and `enforced_by: nothing`, because the document says
   "Nothing checks any of them." Where a superseded policy is cited anywhere in the evidence,
   name its successor.
3. Deterministic checks. Article 4. For each check, write `input` and `result` and nothing else:
   the account count against 25, with the source of the count; each cited policy's status on the
   date of the check; each fact's date against each incident's date. If the count is not on
   record, the result is `cannot count` and the check fails.
4. Signatories. The decider comes from the stage definition. Consents are derived: the owner of
   every triggered policy; support where the outcome lands on the support team; legal where
   personal data is processed; engineering for feasibility at G2 and for rollback at G3; customer
   success where account managers must be briefed. Write each with `because`.
5. Waves. Where the release touches more than one region or more than one tranche of accounts,
   propose waves so that a consent pending for one region blocks only that wave. Each wave has
   accounts, regions and a `go_criteria` that must come from a registered measure.
6. In 05-review, write `policy_check` for every policy the checklist or the draft cites:
   `current`, `superseded_by`, `applies`, `owner`.
7. Path. Write `route_note.risk_inputs`: `accounts`, `personal_data_regions`,
   `prior_decision_of_type` and `reversibility`, each as `{value, source}` or `unknown`. Then run
   `python3 lib/route_risk.py lifecycle/<stage>/<item>.yaml --gate <next gate>` and copy its `path`
   and `fired` rules into `route_note.path` verbatim. The path is decided by `states/routing.yaml`,
   not by this skill. An unknown input fires its rule.
8. Propose the next skill in the sequence.

## Evidence produced
A route note a reader can audit line by line: this type because these facts, these policies
because these conditions, these people because these policies, these waves because these regions.

## Proposed transition
None between stages. Proposes act, or escalated through recover when the classification is
disputed in writing.

## Stop and escalation conditions
- Two types fit and the manifest does not separate them: write both, stop, ask the decider.
- A policy's literal wording does not match the case. Example: POLICY-03 says data "leaving the
  EU region" and Tomas Silva applies it to LATAM accounts. Record both readings under
  `contradictions` with `depends` set to the gate. The policy owner decides.
- The account count cannot be established from any document: the POLICY-08 check fails and the
  route says so. Do not take the count from the draft's intention.
- A signatory has no role in `headcount.xlsx`: write the name and `role: unknown`.

## Human judgment boundary
Confirming the type at G2. Interpreting a policy whose text does not match the case. Deciding
whether a change is a scope change or a launch, which a person does with the count in front of
them. The count itself is not a judgment.

## Worked example
OPPORTUNITY-04. Manifest says 28 accounts requested in DECISION-0028 and 40 in the brief. Check:
input 28, threshold 25, result exceeds. POLICY-08 triggered, owner Ana Fialho. POLICY-03
triggered for LATAM, owner Tomas Silva, with the wording mismatch recorded. Signatories for G3:
Ana Fialho decides, Rui Bastos for review capacity, Tomas Silva per region, Kofi Adjei for
rollback and per-account enablement, Gabriela Rocha for account managers and POLICY-11. Waves
proposed: EU and NA first, LATAM when POLICY-03 is signed.
