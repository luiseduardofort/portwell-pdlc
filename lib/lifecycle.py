#!/usr/bin/env python3
"""The only writer of a stage exit.

  lifecycle.py advance ITEM STAGE [--date YYYY-MM-DD]

Reads the signed record next to the artifact, runs the guard on the artifact as it would look
after the exit, and only then writes it. Edits are textual so comments and layout survive.
Creating the next stage's artifact stays with the intake skill.
"""
import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing  # noqa: E402
import validate_gate as guard  # noqa: E402


def top_level_end(lines, start):
    """Index of the first top-level key after `start`, or len(lines)."""
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line and not line[0].isspace() and not line.startswith("#") and ":" in line:
            return index
    return len(lines)


def set_scalar(lines, key, value, block=None, indent=0):
    """Replace the value of a scalar key, keeping a trailing comment. Optionally inside a block."""
    start, end = 0, len(lines)
    if block:
        start = next(i for i, l in enumerate(lines) if re.match(rf"{block}:", l))
        end = top_level_end(lines, start)
    pattern = re.compile(rf"^(\s{{{indent}}}{key}:\s*)(\"[^\"]*\"|[^\s#]*)(\s*#.*)?$")
    for index in range(start, end):
        match = pattern.match(lines[index])
        if match:
            lines[index] = f"{match.group(1)}{value}{match.group(3) or ''}"
            return
    raise ValueError(f"could not find '{key}' to update")


def append_status_line(lines, record, target, date, number):
    start = next(i for i, l in enumerate(lines) if re.match(r"status_log:", l))
    end = top_level_end(lines, start)
    if lines[start].strip() == "status_log: []":
        lines[start] = "status_log:"
    reason = (f"exited to {target} on {record.get('gate') or 'stage exit'}"
              f" outcome {record.get('outcome')}, signed by {record.get('person')} on {record.get('date')}")
    entry = [
        f"  - n: {number}", "    status: exited", f"    since: \"{date}\"", "    until: null",
        f"    reason: \"{reason}\"", "    waiting_on: null", f"    owner: {record.get('person')}",
        "    asks: []", "    limit: null", "    escalate_to: null", "    return_to: null",
    ]
    insert_at = end
    while insert_at > start + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines[insert_at:insert_at] = entry


def advance(item, stage, date):
    path = signing.root() / "lifecycle" / stage / f"{item}.yaml"
    if not path.exists():
        print(f"BLOCKED: {path} does not exist.", file=sys.stderr)
        return 2
    text = path.read_text()
    old = yaml.safe_load(text)
    record = signing.load_record(path)
    definition = guard.load_definition(stage)
    if not isinstance(record, dict) or definition is None:
        print(guard.message(path, ["no signed record next to the artifact, or no stage definition"]),
              file=sys.stderr)
        return 2

    in_gate = bool(definition.get("gate"))
    outcome = record.get("outcome")
    if record.get("kind") == "gate":
        transition = guard.find_transition(definition, outcome)
        target = transition.get("to") if transition else None
    else:
        targets = [t.get("to") for t in (guard.non_gate_transitions(definition) if in_gate
                   else definition.get("allowed_transitions") or [])
                   if t.get("to") not in (None, "terminal") and not t.get("status")]
        target = targets[0] if len(targets) == 1 else None
    if target is None:
        print(guard.message(path, [f"no single allowed transition for the signed outcome '{outcome}'"]),
              file=sys.stderr)
        return 2

    lines = text.split("\n")
    set_scalar(lines, "status", "exited")
    set_scalar(lines, "status_since", f'"{date}"')
    set_scalar(lines, "exited", f'"{date}"')
    set_scalar(lines, "exited_to", target)
    if record.get("kind") == "gate" and "gate" in old:
        set_scalar(lines, "outcome", outcome, block="gate", indent=2)
    append_status_line(lines, record, target, date, len(old.get("status_log") or []) + 1)
    new_text = "\n".join(lines)

    problems = guard.validate(yaml.safe_load(new_text), record, old)
    if problems:
        print(guard.message(path.relative_to(signing.root()), problems), file=sys.stderr)
        return 2

    handle, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(handle, "w") as out:
        out.write(new_text)
    os.replace(tmp, path)
    print(f"ok  {item} exited {stage} to {target}. Next: run intake for {item} in {target}"
          if target != "terminal" else f"ok  {item} reached a terminal state from {stage}")
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    adv = sub.add_parser("advance")
    adv.add_argument("item")
    adv.add_argument("stage")
    adv.add_argument("--date", default=signing.today())
    args = parser.parse_args(argv)
    return advance(args.item, args.stage, args.date)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as error:
        print(f"BLOCKED: lifecycle.py failed internally and wrote nothing: "
              f"{type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(2)
