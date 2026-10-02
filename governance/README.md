# governance

Trust anchors of the lifecycle guard. An agent never writes here: `.claude/settings.json` denies
the edit, the sandbox denies the shell write, the hook refuses it, and CODEOWNERS requires a
person to review any change in a pull request.

| File | Holds |
| :- | :- |
| `signers.yaml` | Person, role and SSH principal of everyone who may sign |
| `allowed_signers` | The public keys, in OpenSSH `allowed_signers` format, namespace `portwell-gate` |

Signing: the named person runs `python3 lib/sign_gate.py <ITEM> <stage> ...` with their own key. See
`controls/gate-signature-and-consent.md`.
