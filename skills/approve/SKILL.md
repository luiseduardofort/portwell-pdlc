---
name: approve
description: Prepares the gate pack a decider needs and records each required signatory's response verbatim with its date. Never signs, never recommends an outcome, never treats silence or a checklist tick as consent. Runs before G1, G2, G3 and G4.
---

# Approve

## Purpose
Make the decision possible and leave it to the person. The pack says what is known, what is
unknown and what is contradicted. The consents list says who has to agree and what each one
actually said. The signature stays empty until a person writes it.

## Parameters
`item`, `stage`. Runs in 01-backlog for G1, 02-discovery for G2, 05-review for G3 and
07-monitoring for G4.

## Entry conditions
- Verify has run in stages that have verify checks, and its `outcome` is written, passed or
  failed.
- The stage definition names the gate, its options and its decider.
- The route note, or the definition's `consents_rule`, names the consents.

## Reads
- The stage definition's `gate` block and `exit_conditions`.
- `route_note.signatories_*`, `stakeholder_positions`, `evidence_manifest`, `contradictions`,
  `unknowns`, `verification` or `verification_v2`.
- The written responses of each signatory: stakeholder requests, decision records, interview
  lines, anything dated and attributable.

## Prohibited context
- Meeting outcomes that are not on paper. "Nobody objected" is not a response.
- A checklist tick as a response. A tick is what a row owner believed, not what a signatory said.
- Any inference about what a person would probably agree to.

## Writes
`gate.consents`, `gate.pack`, `gate.deadline`, `gate.deadline_source`. In 07-monitoring,
`gate.spawned_item` as a proposal only.

## Never writes
`gate.outcome`. `gate.signature`. `gate.discovery_deadline`, `gate.revisit_date`. Any
`consents[].state: consented` without a written, dated response that says so. `pack.recommendation`,
which stays null.

## Procedure
1. State the exit conditions first. If verification failed, the pack opens with that sentence
   and says which options remain: more-discovery, defer, reject at G2; hold or reject-release at
   G3. Do not remove the failed checks from view.
2. Consents. For each person the route names, write `person`, `role`, `because`. Search the
   written record for a response. Quote it verbatim under `response` with `responded_on`. Set
   `state`: `consented` only if the text agrees explicitly; `objected` if it declines or
   conditions; `pending` if a request was sent and no answer is on record; `not-on-record` if
   nothing was ever asked in writing. An objection stays `objected` until the same person writes
   otherwise. Article 3.
3. Pack. `summary` is one paragraph: what is being decided, for whom, with what scope. `known` is
   a list of manifest IDs with their values. `unknown` copies `unknowns`. `contradictions` copies
   the entries whose `depends` is this gate. `recommendation` is null.
4. Evidence review, full path only. Run `python3 lib/route_risk.py lifecycle/<stage>/<item>.yaml
   --gate <gate>`. If the path is `full`, have a separate reviewer apply
   `skills/approve/evidence-review.md` to the artifact and write its result, verbatim, under
   `gate.evidence_review`. Never review your own pack. A `fail` verdict returns the pack to step 3
   with the findings. The guard refuses a full-path exit without `verdict: pass`.
5. Deadline. Copy the deadline the previous gate set or a request on record states, with its
   source. If today is past it and `signature.date` is null, propose `blocked` through recover
   with reason "awaiting decision", waiting on the decider.
6. Stop. Write in the trace the question the decider must answer and the options. End the skill.
   The signature, if it comes, is written by the person into `gate.signature` with `outcome`.
7. When a signature exists, do nothing more. Handoff reads the outcome.

## Evidence produced
A gate block in which a reader sees, without asking anyone, what the decider was shown, who had
to agree, what each one said and when, and whether the decision was taken.

## Proposed transition
None. Approve always ends at the signature. Where a consent is pending past the ask limit, it
proposes `escalated` through recover.

## Stop and escalation conditions
- Always stops before the signature. This is the point where a person decides.
- The deadline has passed without a signature: `blocked`, reason awaiting decision.
- A consent is `pending` after three recorded asks: `escalated`. If no escalation target is
  named, say so in the artifact.
- A consent is `objected` and any other record claims the matter is settled: add a contradiction,
  keep `objected`, and name the objector as the only person who can change it.
- Verification failed and the decider asks for the option `build` or `release`: not available.
  The pack says why. A waiver at G3 is a signed entry under `waivers`, not a change to the pack.

## Human judgment boundary
The outcome. Closing an objection, by the objector only. Waiving a failed row. Naming the
escalation target.

## Worked example
OPPORTUNITY-04, G3. Decider Ana Fialho, no release decision on record. Rui Bastos: "I am against
doing it in that order." 2026-08-08, `objected`. Tomas Silva: "Until I do I cannot sign off on
those accounts." 2026-08-11, `objected` for LATAM, EU and NA "not affected". Kofi Adjei:
`not-on-record`. Gabriela Rocha: checklist row 8 yes without evidence, `not-on-record`. Pack opens
with "verification failed on rows 2, 4, 6, 7". Options: hold or reject-release. The skill stops.
