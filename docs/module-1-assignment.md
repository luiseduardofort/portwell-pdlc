# Enunciado original do Módulo 1

Texto do `README.md` original do template, preservado aqui quando o README passou a documentar a
arquitetura. É o enunciado da atividade, não a descrição do sistema.

---

# Module 1: Build the lifecycle skills

This repository is the working space for the Module 1 group assignment. The group will design a
simple agentic lifecycle for one real process in its assigned Portwell track and create one Claude
Code skill for each lifecycle stage.

The assigned track repository is a context source. Do not copy the application, data project,
knowledge base, or product workspace into this repository, and do not change the track repository
as part of this assignment.

## Outcome for the week

By the next class, the repository should contain:

1. A completed lifecycle worksheet in `lifecycle.md`.
2. One completed skill for each stage in `skills/`.
3. One Portwell work item traced through the whole lifecycle.
4. At least one point where a skill stops, refuses to continue, or requests a human decision.
5. One group pull request containing the design, trace, limitations, and participant contributions.

The skills do not need integrations, hooks, a state engine, or production automation. They are
prompt-level procedures for Module 1. Later modules will add tools, permissions, guards, and
verification.

## Repository contents

```text
README.md                 Assignment instructions
track.yaml                Group, track, process, and context location
lifecycle.md              Current-process and proposed-lifecycle worksheet
skills/
  intake/SKILL.md         Accept and bound the work item
  context/SKILL.md        Assemble the required context
  route/SKILL.md          Choose the path and level of autonomy
  act/SKILL.md            Perform the stage's domain work
  verify/SKILL.md         Check the result and produce evidence
  approve/SKILL.md        Prepare or record an approval decision
  handoff/SKILL.md        Transfer or publish the result
  observe/SKILL.md        Inspect the outcome after handoff
  recover/SKILL.md        Handle blocked, failed, or ambiguous work
traces/
  worked-case.md          End-to-end record of one fixture item
```

## 1. Choose the track process

Complete `track.yaml`. Use the process assigned to the track:

| Track | Primary process |
| :- | :- |
| SDLC | A customer-reported bug reaches the code and then reaches customers |
| DDLC | The month's figures are produced |
| KDLC | A service-review pack is made and then used |
| PDLC | A product decision is made |

Choose one real work item from the assigned repository's tracker, interviews, incident records,
or fixture data.

## 2. Trace what happens today

Read the track repository before designing the lifecycle:

1. `docs/how-we-work-today.md`, or the equivalent document.
2. The relevant interview.
3. The tracker or operational record in `data/`.
4. Related incidents, policies, identifiers, and dependency notes.

Complete the current-process table in `lifecycle.md`. Record unknown and contradictory facts as
such. Do not invent a missing fact to complete the map.

## 3. Design the lifecycle

Use the common stages as a starting point:

```text
Intake -> Context -> Route -> Act -> Verify -> Approve -> Handoff -> Observe
                                  |                         |
                                  +------ Recover <---------+
```

The group may rename stages for the track, but the lifecycle must still make these concerns
visible. Add waiting, failure, escalation, and terminal states to the worksheet where the process
requires them.

For every stage, decide:

- What must be true before it begins.
- Which context may be read.
- What work is performed.
- What evidence is produced.
- What allows the item to advance.
- When the skill must stop or escalate.
- Which decisions require a human.

## 4. Write the skills

Complete every `SKILL.md` in `skills/`. Each skill should be short enough for another participant
to inspect and should contain:

- A clear purpose.
- Entry conditions.
- Required and prohibited context.
- An ordered procedure.
- Evidence produced.
- The proposed next state.
- Stop and escalation conditions.
- Any human judgment boundary.

A skill may produce evidence and recommend a transition. It must not claim that a human approval
occurred when it did not.

## 5. Run one worked case

Use `traces/worked-case.md` to record one item moving through the skills. The trace may be run
manually in Claude Code. Preserve:

- The item and intended outcome.
- Each skill invoked.
- Context read.
- Evidence produced.
- Decisions and interventions.
- One refusal, failure, ambiguity, or recovery.
- Final state and unresolved limitations.

Do not repair the Portwell fixture to make the trace succeed. The problems in the fixture are the
material for the exercise.

## Suggested group workflow

During class:

1. Select the work item and trace the existing process.
2. Agree on the proposed states and the evidence needed to advance.
3. Divide the skills among participants.
4. Open a draft group pull request.

During the week:

1. Complete the assigned skills in smaller branches or commits.
2. Review the skills against the complete lifecycle, not only their individual stage.
3. Run the worked case as a group.
4. Reconcile terminology and transitions before submitting the pull request.

## Definition of done

The assignment is complete when:

- All nine skill files contain track-specific procedures rather than placeholders.
- Every skill names its entry conditions, output evidence, next state, and stop conditions.
- Human judgment is visible and assigned to a role.
- Failure and recovery appear in the lifecycle and worked trace.
- The final state represents the real track outcome, not completion in one tool.
- The track repository was used as evidence and was not modified.
- The pull request records contributions, trade-offs, known limitations, and the next improvement.
