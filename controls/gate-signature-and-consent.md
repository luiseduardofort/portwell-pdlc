# Control candidate: no stage exit without a signed decision and documented consents

Module 3 control record. Code in `lib/`, contract additions in `states/*/definition.yaml`
(`exit_control`), trust anchors in `governance/`, server check in `.github/workflows/guard.yml`,
tests in `tests/`.

## 1. The rule and its current source

A stage artifact may be exited only when the person the stage definition names has signed it, and
each required consent is a dated written response from that person. Records are append-only.

Sources, all prose before this control:
- `skills/constitution/SKILL.md`, Articles 3 and 6.
- `skills/handoff/SKILL.md`, step 1: "If `gate.signature.person` is null, refuse".
- `lifecycle/02-discovery/OPPORTUNITY-04.yaml`, `controls_missing`: "a consent cannot be recorded
  as given without a dated written response from that person".

The refusal was the model reading a sentence. Nothing stopped an edit that wrote `exited_to` over
a null signature, and nothing stopped anyone from typing a complete signature block.

## 2. Failure the fixture shows

- Launch readiness checklist row 2 reads as met. Rui Bastos, Support Manager, objected in writing
  on 2026-08-08. Who ticked the row and when is `unknown`.
- DECISION-0028 (2026-08-07): "Approver: Ana Fialho. No other signature." The pilot reached 28
  accounts, above the POLICY-08 threshold of 25.
- `docs/How we work today.docx`: "agreement means nobody objected in the meeting".
- Trace steps 4, 5, 12 and 13: G1 and G2 reach handoff with `signature.person: null`. Handoff
  refused only because the skill obeyed its own text.

## 3. Invariant

A stage transition exists only when the record proves, with something an agent cannot produce, that
a named person decided, and that every required consent carries that person's literal, dated words.
The control checks presence, authorship and shape. It never judges whether an objection was
addressed. That stays with the person who raised it (Article 3).

## 4. Implementation: layers, and what each one stops

| Layer | Where | Stops | Does not stop |
| :- | :- | :- | :- |
| Signed record | `lib/sign_gate.py`, `lib/signing.py`, `governance/` | Forged or edited signatures. The record is an SSH signature by the decider's own key over the item, stage, outcome, statement and a hash of the signed sections | A person with the key signing something wrong |
| Single exit writer | `lib/lifecycle.py advance` | Exits written by hand. It validates before writing and edits text so comments survive | Exits written some other way (see CI) |
| Hook | `.claude/settings.json`, `lib/validate_gate.py --hook` | `Write`, `Edit`, `NotebookEdit` that exit an artifact, write a signature file or touch `governance/`. Fails closed | Shell writes |
| Permissions | `.claude/settings.json` `permissions.deny` | Edit-tool writes to `governance/` and signature files | Shell writes |
| Sandbox | `.claude/settings.json` `sandbox` | Shell writes to `governance/` and signature files, at OS level | Shell writes to artifacts, by design (see below) |
| CI | `.github/workflows/guard.yml`, `validate_gate.py --base` | Anything that reached a pull request by any route: a forged exit, rewritten history, deleted artifact, unsigned or modified signature | Nothing, if it is not a required check (see Setup) |
| Pre-commit | `hooks/pre-commit` | The same checks before a local commit | Anyone who skips hooks. CI is the net |

Why artifacts stay writable from the shell: the CLI that advances an item runs in the shell, and
a command filter cannot tell a legitimate write from a forged one. The artifact is protected by
detection (CI recomputes everything), and the things that make a forgery valid, the signature
file and the key allowlist, are protected by prevention.

Checks, in order:
1. A consent with `state: consented` has a real response and an ISO `responded_on`.
2. Append-only: `item`, `stage`, `entered` unchanged, `status_log` lines never rewritten (only
   `until` may be set once), `sources` entries kept, any status or exit change has a new log line.
3. On exit: the signed record exists, its kind and outcome fit the stage, the signer is the
   decider (gates) or owner (other exits) named in `states/<stage>/definition.yaml`, the signer is
   enrolled, the SSH signature verifies, and the hash of `exit_control.signed_sections` still
   matches. Editing the pack, consents or attested block after signing voids the signature.
4. `gate.signature` inside the artifact may not be filled unless it equals the signed record.
5. `exited_to` equals the transition the signed outcome allows. An outcome that keeps the item in
   the stage cannot exit.
6. `exit_control.exit_checks` of the stage hold (engineering acceptance in writing and not verbal,
   no deviation needing G2, wave confirmed and matching G3, closure owners, verification passed
   when advancing, and so on).
7. Advancing to another stage needs every consent `consented`. A terminal reject needs none.

Not checked: that a consent response is truthful, that row owners' evidence is real, and
the readiness rule "no row reads no without a signed waiver" (no machine-readable form yet). Stages
01 and 07 have signature checks but no `exit_checks`. A G3 `hold` or `reject-release` and a G4
`iterate` have no transition in the definitions, so they cannot be exited yet.

## 5. Failure message and recovery

```
BLOCKED: lifecycle/02-discovery/OPPORTUNITY-04.yaml cannot be written as an exit.
  - no signed record: lifecycle/<stage>/<ITEM>.signature.yaml is missing
  - advancing needs every consent: Rui Bastos is 'objected'
  - advancing needs every consent: Tomas Silva is 'objected'
  - advancing needs every consent: Kofi Adjei is 'not-on-record'
Recovery:
  1. Do not fill a signature, a consent or an exit field yourself. Only the named person signs.
  2. Ask the signer to run: python3 lib/sign_gate.py <ITEM> <stage> --person <name> --statement <words>
     (gates also take --outcome). Ask each missing consent for a dated written response.
  3. Exit with: python3 lib/lifecycle.py advance <ITEM> <stage>
  4. Run the recover skill to log the episode in status_log (waiting_on, asks, escalate_to).
No file was written.
```

Any internal error also exits 2 with a message. In Claude Code only exit code 2 blocks, so a
crashing guard must not return 1.

## 6. Portability

| Change | Survives | Why |
| :- | :- | :- |
| Model | Yes | Plain code and a signature. No model judgment |
| Coding harness | Mostly | Guard, signing, CLI, CI and pre-commit are harness-free. Hook, permissions and sandbox are Claude Code only and need an adapter elsewhere |
| Track repository | Partly | Signing and append-only are generic. Who must consent, the signers, `exit_checks` fields and IDs are Portwell's |

Portable core: `lib/`, `states/`, `governance/`, `.github/`. Disposable adapter: `.claude/`.

## Setup a person must do (not done by this change)

1. Enrol signers: `governance/signers.yaml` and `governance/allowed_signers`. Nobody is enrolled,
   so every exit is refused until someone is. That is the fail-closed default.
2. In GitHub, make the `lifecycle-guard` check required on `main` and require CODEOWNERS review.
   Without this, CI only reports and a push can still land.
3. Replace the proposed owner in `.github/CODEOWNERS` with the group's lifecycle owner.
4. Optional, stronger: managed settings with `allowManagedHooksOnly` and
   `allowManagedPermissionRulesOnly`, so a session cannot weaken the project settings.

## Owner

To be named by the group. Proposed: the lifecycle owner, reviewed by the policy owners.

## What was verified, and what was not

Verified by `python3 -m unittest discover tests` (33 cases, real SSH signatures, scratch git
repositories): every refusal above, the accepted paths, fail-closed behaviour, the hook protocol
including edit payloads, the CLI end to end with comments preserved, and `--base` catching a forged
exit, rewritten history and a deleted artifact written from the shell.

Not verified:
- The sandbox and permission layers. They apply to new sessions only. A live probe in the session
  that wrote them showed a shell write to `governance/` succeeding, which is why that layer is
  documented as unproven. Path and glob semantics of `sandbox.filesystem.denyWrite` are unconfirmed.
- `tests/integration_hook.sh` (live Claude Code). One run failed its edit scenario, which allowed
  `Bash`. The likely cause is a fall back to a shell write, which is allowed by design, but this was
  not confirmed. The script now isolates the hook by removing `Bash` from that scenario, and has not
  been re-run.
- The GitHub workflow has never run.
