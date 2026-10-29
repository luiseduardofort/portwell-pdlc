#!/usr/bin/env python3
"""A person signs a gate decision or a stage exit with their own SSH key.

  sign_gate.py ITEM STAGE --person "Ana Fialho" --statement "words" [--outcome build] [--key PATH]

Run it yourself, in your own terminal outside Claude Code: the project sandbox denies shell
writes to signature files, and the signer's key must stay out of the agent's reach.
It shows exactly what is being signed and asks for confirmation on the terminal. Skills never
run it: they do not hold the key. The record is written next to the artifact and is immutable
once committed.
"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing  # noqa: E402
import validate_gate as guard  # noqa: E402


def build_record(item, stage, person, statement, outcome, date):
    path = signing.root() / "lifecycle" / stage / f"{item}.yaml"
    artifact = yaml.safe_load(path.read_text())
    definition = guard.load_definition(stage)
    entry = signing.signer_for(person)
    in_gate = bool(definition.get("gate"))
    kind = "gate" if outcome and in_gate else "exit"
    wanted = guard.required_signer(definition, kind)
    if wanted.get("person") and wanted["person"] != person:
        raise SystemExit(f"{kind} of {stage} must be signed by {wanted['person']}, not {person}")
    if entry is None:
        raise SystemExit(f"{person} is not enrolled in governance/signers.yaml")
    return path, {
        "kind": kind, "item": item, "stage": stage,
        "gate": (artifact.get("gate") or {}).get("id") if kind == "gate" else None,
        "outcome": outcome if kind == "gate" else "exit",
        "person": person, "role": entry.get("role") or wanted.get("role"),
        "statement": statement, "date": date,
        "sections_sha256": signing.sections_digest(artifact, guard.signed_sections(definition)),
    }


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("item")
    parser.add_argument("stage")
    parser.add_argument("--person", required=True)
    parser.add_argument("--statement", required=True)
    parser.add_argument("--outcome")
    parser.add_argument("--date", default=signing.today())
    parser.add_argument("--key", default=str(Path.home() / ".ssh" / "id_ed25519"))
    parser.add_argument("--yes", action="store_true", help="skip the terminal confirmation (tests)")
    args = parser.parse_args(argv)

    path, record = build_record(args.item, args.stage, args.person, args.statement,
                                args.outcome, args.date)
    target = signing.signature_path(path)
    if target.exists():
        raise SystemExit(f"{target.name} already exists. A signed record is immutable.")
    print("You are signing this record with your own key:\n")
    print(yaml.safe_dump({k: v for k, v in record.items()}, sort_keys=False))
    if not args.yes:
        if not sys.stdin.isatty():
            raise SystemExit("Refusing: confirmation needs an interactive terminal.")
        if input("Type 'sign' to confirm: ").strip() != "sign":
            raise SystemExit("Not signed.")
    signed = signing.sign(record, args.key)
    target.write_text(yaml.safe_dump(signed, sort_keys=False))
    problems = signing.verify(signed)
    if problems:
        target.unlink()
        raise SystemExit("The signature does not verify, nothing was kept: " + "; ".join(problems))
    print(f"Signed. Wrote {target}. Next: python3 lib/lifecycle.py advance {args.item} {args.stage}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
