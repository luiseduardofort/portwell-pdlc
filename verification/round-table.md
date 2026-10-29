# Round table and limits

## Workbook 4.8, answered from this repository

| Question | Answer the repository supports |
| :- | :- |
| Where does the verification queue currently form? | At the human gate. OPPORTUNITY-04 waits on named people (`reports/operating-report.md`): G2 unsigned and past its 2026-08-31 deadline, BLOCKER-01 waiting on Tomas Silva since 2026-07-11, an escalation with no target. Layers 1 and 2 cannot shorten that wait. They make sure the pack the decider reads is true |
| Which prose rules should be tested checks? | Done in Module 3 and 4: signature, consent words, append-only, exit checks, routing. Still prose: "no row reads no without a signed waiver", the truthfulness of a consent response, that a `risk_inputs` source says what its value says (layer 2 only) |
| Which harness components have no owner? | The Module 2 inventory is not in this repository, so this cannot be answered from it. Of what is here: the CODEOWNERS owner is a placeholder, nobody is enrolled as a signer, and `evals/human-grades.yaml` has no grader assigned |
| What must be measured before an agentic delivery claim to a client? | At least: the live eval baseline on dev and held-out, cost per accepted output, the correction ratio and escaped defects from human grades, and the lifecycle measures over more than one item. Today only the lifecycle measures and the scorer self-test exist. One item is not a sample |
| Which single change would move accepted change per unit of human attention most? | Naming an escalation target. Every open wait in the report ends at "not named" or at the decider. A faster or more accurate agent does not move a wait on a person. This is an organizational change, not a harness change |

## Workbook 4.6, deployment observability and rollback: not covered

The PDLC analogue is the wave rollback in 06-release and the measures in 07-monitoring. No item has
reached those stages, the adoption measures are a draft "not agreed", and the rollback plan has
`tested_on: unknown`. In this repository:

- `exit_checks` of 06-release require the wave to be confirmed and to match the G3 wave. They do not
  sample any health signal after release.
- There is no automated rollback condition. A rollback that has never been executed is a document,
  not a control (workbook 4.6), and that is what the readiness checklist has today.
- There is no recorded trace from a released wave back to the G3 pack that approved it, beyond the
  artifacts themselves.

What would close it: a monitoring window and threshold per measure in the G3 wave plan, a check in
07-monitoring that moves the item to correction-required when a measure crosses it, and a rollback
exercised once before G3 can be signed.
