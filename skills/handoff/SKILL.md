---
name: handoff
description: Closes a stage artifact once its gate is signed or its exit condition met, opens the next stage through intake, records who received the item, and updates the board. Refuses to move an item whose gate has no signature.
---

# Handoff

## Purpose
Move the item, and only when the record says it may move. Handoff is the one skill that writes
`exited` and `exited_to`, and the one that creates the next artifact. In the borrowed stages it
also records what engineering handed back. In 08-done it writes the closure.

## Parameters
`item`, `stage`. Runs last in every stage.

## Entry conditions
- In a stage with a gate: `gate.signature` has person, role, statement and date, and
  `gate.outcome` is one of the definition's options.
- In a stage without a gate: the definition's `exit_conditions` are met and, where there are
  verify checks, `outcome: passed`.
- For a wave loop from 07-monitoring back to 06-release: the next wave's `go_criteria` are met
  in `wave_criteria` and every consent that wave requires is `consented`.

## Reads
- The stage definition's `allowed_transitions` and `exit_conditions`.
- `gate.outcome`, `gate.signature`, `verification.outcome`, `wave_criteria`.
- `states/statuses.yaml` for the `exited` status. `board.md`.
- In 03-ready-for-development: engineering's written acceptance. In 06-release: the
  communications sent.

## Prohibited context
- Any verbal report of an outcome. If it is not in the artifact, it did not happen.
- The next stage's work. Handoff opens the door and stops.

## Writes
In the current artifact: `exited`, `exited_to`, `status: exited`, `status_since`, one
`status_log` line. In 03-ready-for-development: `engineering_acceptance`. In 06-release:
`release_log[].communications`, `confirmed`. In 08-done: `closure`. `board.md`: the item's row.
The next stage's artifact, through intake.

## Never writes
Any gate field. Any section of the next artifact beyond what intake writes. Any past
`status_log` line.

## Procedure
1. Check the entry conditions against the artifact. If `gate.signature.person` is null, refuse:
   write in the trace "handoff refused, gate <id> unsigned" and end. This is not a stop for
   information. It is a refusal.
2. Map `gate.outcome` or the exit condition to one entry of `allowed_transitions`. If no entry
   matches, refuse and report the mismatch to the stage owner.
3. For a terminal outcome, reject or retire: set `status` accordingly, `exited_to: terminal`,
   append the status line with the signature's date and person, and end. No next artifact.
4. For a move: run `python3 lib/lifecycle.py advance <item> <stage>`. It reads the signed record
   `lifecycle/<stage>/<item>.signature.yaml`, runs the guard, and only then writes `exited`,
   `exited_to`, `status: exited` and the status line. Do not edit those fields by hand: the hook
   refuses it. If the command exits 2, relay its message and stop. The signature file is written
   only by the named person with `lib/sign_gate.py`. This skill never runs it.
5. Invoke intake for `item` in the next stage. Intake fills the entry ticket from this gate.
6. For a G4 outcome `iterate`: the new item needs an ID from the product repository. Write the
   proposed item under `gate.spawned_item` with `links.spawned_by` set, and stop for the ID. Do
   not coin one.
7. In 03-ready-for-development, copy engineering's acceptance verbatim into
   `engineering_acceptance.accepted`. In 06-release, record each communication with date and
   sender, and `confirmed` from engineering's confirmation.
8. Update `board.md`: one row per item, stage, type, status, since, owner. Remove nothing;
   move the row.
9. In 08-done, write `closure` with the G4 reference, the verdict summary, spawned items, and
   every remaining measure with the item that now owns it. If a measure has no owning item, the
   closure is incomplete and the item stays in 07-monitoring.

## Evidence produced
A closed artifact whose last status line names the gate, the outcome, the signer and the date. An
open artifact in the next stage whose entry ticket points back. A board row that agrees with both.

## Proposed transition
The one the signed outcome names. Nothing else.

## Stop and escalation conditions
- Unsigned gate: refuse.
- Outcome not in options, or transition not allowed: refuse, report.
- Next stage's entry conditions fail, for example engineering has not accepted: the item stays,
  and recover opens a `blocked` line waiting on the receiving team.
- An ID is needed for a spawned item: stop and ask.
- A remaining measure has no owner at closure: the item does not reach done.

## Human judgment boundary
None inside handoff. Every judgment it depends on was signed upstream. That is the point of it.

## Worked example
OPPORTUNITY-04 in 02-discovery, 2026-09-24. G2 signature null. Handoff refuses. The item stays in
discovery, status blocked, and the trace records the refusal as the run's stopping point.
