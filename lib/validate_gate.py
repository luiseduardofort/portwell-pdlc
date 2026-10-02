#!/usr/bin/env python3
"""Lifecycle guard. Deterministic, no model judgment, fails closed.

It enforces, by reading fields and verifying a signature:
  - an exit needs a signed record from the person the stage definition names, bound to the
    sections they attested to (lib/signing.py)
  - a consent counts as given only with the person's own dated words
  - the stage's machine-readable exit_checks hold
  - records are append-only (Article 6)
It never judges whether an objection was addressed (Article 3).

Usage:
  validate_gate.py FILE [FILE ...]    validate artifacts on disk
  validate_gate.py --all              validate every lifecycle/*/*.yaml
  validate_gate.py --base REF         validate what changed since REF (CI and pre-commit)
  validate_gate.py --hook             Claude Code PreToolUse hook, JSON on stdin

Exit 0 passes. Exit 2 blocks. Any internal error also exits 2: the control never fails open.
"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing  # noqa: E402

NO_RESPONSE = {"", "not on record", "unknown", "none", "null"}
STATE_FIELDS = ("status", "status_since", "exited", "exited_to")
PROTECTED = ("governance/", "lifecycle/")  # prefixes; lifecycle only for *.signature.yaml
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def blank(value):
    return value is None or (isinstance(value, str) and value.strip().lower() in NO_RESPONSE)


def is_date(value):
    if isinstance(value, datetime.date):
        return True
    try:
        datetime.date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def load_definition(stage):
    path = signing.root() / "states" / stage / "definition.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text())


def find_transition(definition, outcome):
    """Transition for a gate outcome. An explicit `outcome:` key wins over the `when` text."""
    transitions = definition.get("allowed_transitions") or []
    for transition in transitions:
        if transition.get("outcome") == outcome:
            return transition
    for transition in transitions:
        match = re.search(r"outcome (\S+?)(?:[,\s]|$)", str(transition.get("when", "")))
        if match and match.group(1) == outcome:
            return transition
    return None


def non_gate_transitions(definition):
    """Exits that no gate outcome decides, e.g. the wave loop from 07-monitoring to 06-release."""
    return [
        t for t in definition.get("allowed_transitions") or []
        if t.get("to") not in (None, "terminal") and t.get("when") and not t.get("status")
        and not t.get("outcome")
        and not re.search(r"outcome \S+", str(t.get("when", "")))
        and "signed" not in str(t.get("when", ""))
    ]


# ---------------------------------------------------------------- exit_checks

def _items(artifact, path):
    value = signing.get_path(artifact, path)
    return value if isinstance(value, list) else []


def run_exit_checks(artifact, definition, advancing):
    problems = []
    for check in (definition.get("exit_control") or {}).get("exit_checks") or []:
        if check.get("only_if_advancing") and not advancing:
            continue
        label = check.get("because", json.dumps(check, default=str))
        if "present" in check:
            if blank(signing.get_path(artifact, check["present"])):
                problems.append(f"exit check failed: {check['present']} is empty ({label})")
        elif "blank" in check:
            if not blank(signing.get_path(artifact, check["blank"])):
                problems.append(f"exit check failed: {check['blank']} must be empty ({label})")
        elif "equals" in check:
            path, wanted = check["equals"]
            if signing.get_path(artifact, path) != wanted:
                problems.append(f"exit check failed: {path} is not '{wanted}' ({label})")
        elif "forbid_where" in check:
            path, where = check["forbid_where"]
            if any(isinstance(i, dict) and all(i.get(k) == v for k, v in where.items())
                   for i in _items(artifact, path)):
                problems.append(f"exit check failed: an entry in {path} matches {where} ({label})")
        elif "each_present" in check:
            path, field = check["each_present"]
            for index, entry in enumerate(_items(artifact, path)):
                if not isinstance(entry, dict) or blank(entry.get(field)):
                    problems.append(f"exit check failed: {path}[{index}].{field} is empty ({label})")
        elif "last_present" in check:
            path, field = check["last_present"]
            entries = _items(artifact, path)
            if not entries or blank(signing.get_path(entries[-1], field)):
                problems.append(f"exit check failed: last entry of {path} has empty {field} ({label})")
        elif "last_equals" in check:
            path, field, wanted = check["last_equals"]
            entries = _items(artifact, path)
            if not entries or signing.get_path(entries[-1], field) != wanted:
                problems.append(f"exit check failed: last entry of {path} {field} is not {wanted} ({label})")
        else:
            problems.append(f"exit check has an unknown operator: {check}")
    return problems


# ---------------------------------------------------------------- append-only

def check_append_only(old, new):
    """Article 6. Compare a previous version of an artifact with the proposed one."""
    problems = []
    if not isinstance(old, dict):
        return problems
    for key in ("item", "stage", "entered", "entered_from"):
        if old.get(key) != new.get(key):
            problems.append(f"append-only: header field '{key}' was changed")
    old_log, new_log = old.get("status_log") or [], new.get("status_log") or []
    if len(new_log) < len(old_log):
        problems.append("append-only: status_log lines were removed")
    for index, line in enumerate(old_log[: len(new_log)]):
        for key, value in (line or {}).items():
            changed = (new_log[index] or {}).get(key) != value
            if changed and not (key == "until" and value is None):
                problems.append(f"append-only: status_log line {index + 1} field '{key}' was rewritten")
    if any(old.get(k) != new.get(k) for k in STATE_FIELDS) and len(new_log) <= len(old_log):
        problems.append("append-only: status or exit fields changed without a new status_log line")
    old_sources, new_sources = old.get("sources") or [], new.get("sources") or []
    if new_sources[: len(old_sources)] != old_sources:
        problems.append("append-only: existing sources entries were changed or removed")
    return problems


# ---------------------------------------------------------------- signature

def required_signer(definition, kind):
    if kind == "gate":
        return (definition.get("gate") or {}).get("decider") or {}
    return definition.get("owner") or {}


def signed_sections(definition):
    return (definition.get("exit_control") or {}).get("signed_sections") or []


def check_signature(artifact, definition, record, kind, outcome_hint=None):
    problems = []
    if not isinstance(record, dict):
        return ["no signed record: lifecycle/<stage>/<ITEM>.signature.yaml is missing"]
    gate = artifact.get("gate") or {}
    for key in ("person", "role", "statement", "date"):
        if blank(record.get(key)):
            problems.append(f"signed record has empty {key}")
    if record.get("kind") != kind:
        problems.append(f"signed record kind is '{record.get('kind')}', expected '{kind}'")
    if record.get("item") != artifact.get("item") or record.get("stage") != artifact.get("stage"):
        problems.append("signed record is for a different item or stage")
    if kind == "gate":
        if record.get("gate") != gate.get("id"):
            problems.append(f"signed record is for gate '{record.get('gate')}', not {gate.get('id')}")
        if record.get("outcome") not in (gate.get("options") or []):
            problems.append(f"signed outcome '{record.get('outcome')}' is not one of {gate.get('options')}")
    elif record.get("outcome") != "exit":
        problems.append("signed record of an exit must carry outcome 'exit'")
    wanted = required_signer(definition, kind)
    if wanted.get("person") and record.get("person") != wanted["person"]:
        problems.append(f"{kind} must be signed by {wanted['person']} ({wanted.get('role')}), "
                        f"not {record.get('person')}")
    expected = signing.sections_digest(artifact, signed_sections(definition))
    if record.get("sections_sha256") != expected:
        problems.append("signed sections changed after signing (digest mismatch): sign again")
    problems.extend(signing.verify(record))
    return problems


# ---------------------------------------------------------------- core

def validate(artifact, record=None, old=None):
    """Return a list of violations. Empty means the artifact may be written."""
    problems = []
    if not isinstance(artifact, dict):
        return ["artifact is not a YAML mapping"]
    gate = artifact.get("gate") if isinstance(artifact.get("gate"), dict) else None
    stage = artifact.get("stage")

    if gate:
        for consent in gate.get("consents") or []:
            if consent.get("state") == "consented":
                who = consent.get("person", "unknown person")
                if blank(consent.get("response")):
                    problems.append(f"consent of {who} is 'consented' with no written response")
                if not is_date(consent.get("responded_on")):
                    problems.append(f"consent of {who} is 'consented' with no response date")
    problems.extend(check_append_only(old, artifact))

    exiting = (artifact.get("status") == "exited" or artifact.get("exited") is not None
               or artifact.get("exited_to") is not None)
    if not exiting:
        # A signature block filled in without an exit still has to be the real, signed thing.
        if gate and any(not blank(v) for v in (gate.get("signature") or {}).values()):
            problems.extend(check_in_artifact_signature(gate, record))
        return problems

    definition = load_definition(stage)
    if definition is None:
        return problems + [f"no definition for stage '{stage}' in states/"]

    target = artifact.get("exited_to")
    in_gate_stage = bool(definition.get("gate"))
    nongate_targets = [t.get("to") for t in non_gate_transitions(definition)]
    kind = "exit" if (not in_gate_stage or target in nongate_targets) else "gate"

    problems.extend(check_signature(artifact, definition, record, kind))
    if gate:
        problems.extend(check_in_artifact_signature(gate, record))

    if kind == "gate":
        outcome = (record or {}).get("outcome")
        if gate and not blank(gate.get("outcome")) and gate.get("outcome") != outcome:
            problems.append(f"gate.outcome '{gate.get('outcome')}' differs from the signed outcome '{outcome}'")
        transition = find_transition(definition, outcome) if outcome else None
        if transition is None:
            return problems + [f"no allowed transition for outcome '{outcome}' in stage {stage}"]
        wanted_to = transition.get("to")
        if target != wanted_to:
            problems.append(f"exited_to is '{target}' but outcome '{outcome}' allows only '{wanted_to}'")
        if wanted_to == stage:
            problems.append(f"outcome '{outcome}' keeps the item in {stage}; it cannot be exited")
    else:
        allowed = [t.get("to") for t in definition.get("allowed_transitions") or []
                   if not t.get("status") and t.get("to") not in (None, "terminal")]
        if allowed and target not in allowed:
            problems.append(f"exited_to is '{target}' but {stage} allows only {allowed}")

    advancing = target not in (stage, "terminal", None)
    problems.extend(run_exit_checks(artifact, definition, advancing))

    if advancing and gate:
        for consent in gate.get("consents") or []:
            if consent.get("state") != "consented":
                problems.append(f"advancing needs every consent: {consent.get('person', 'unknown person')} "
                                f"is '{consent.get('state')}'")
    return problems


def check_in_artifact_signature(gate, record):
    """The gate.signature block inside the artifact is informational. It may never differ from the
    signed record, and it may never be filled without one."""
    block = gate.get("signature") or {}
    filled = {k: v for k, v in block.items() if not blank(v)}
    if not filled:
        return []
    if not isinstance(record, dict):
        return ["gate.signature is filled in the artifact but no signed record exists: forgery"]
    differing = [k for k, v in filled.items() if str(record.get(k)) != str(v)]
    if differing:
        return [f"gate.signature.{', '.join(differing)} differs from the signed record"]
    return []


# ---------------------------------------------------------------- output

def message(path, problems):
    return "\n".join([
        f"BLOCKED: {path} cannot be written as an exit.",
        *[f"  - {p}" for p in problems],
        "Recovery:",
        "  1. Do not fill a signature, a consent or an exit field yourself. Only the named person signs.",
        "  2. Ask the signer to run: python3 lib/sign_gate.py <ITEM> <stage> --person <name> --statement <words>",
        "     (gates also take --outcome). Ask each missing consent for a dated written response.",
        "  3. Exit with: python3 lib/lifecycle.py advance <ITEM> <stage>",
        "  4. Run the recover skill to log the episode in status_log (waiting_on, asks, escalate_to).",
        "No file was written.",
    ])


# ---------------------------------------------------------------- entry points

def check_file(path, old=None):
    path = Path(path)
    return validate(yaml.safe_load(path.read_text()), signing.load_record(path), old)


def relative_path(file_path):
    try:
        return Path(file_path).resolve().relative_to(signing.root())
    except ValueError:
        return None


def is_artifact(relative):
    return (relative is not None and len(relative.parts) == 3 and relative.parts[0] == "lifecycle"
            and relative.suffix == ".yaml" and not relative.name.endswith(".signature.yaml"))


def is_protected(relative):
    if relative is None:
        return False
    text = relative.as_posix()
    return text.startswith("governance/") or (
        text.startswith("lifecycle/") and text.endswith(".signature.yaml"))


def proposed_text(tool_input, current):
    if "content" in tool_input:
        return tool_input["content"]
    edits = tool_input.get("edits") or [{k: tool_input.get(k) for k in
                                         ("old_string", "new_string", "replace_all")}]
    text = current
    for edit in edits:
        old, new = edit.get("old_string") or "", edit.get("new_string") or ""
        text = text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    return text


def hook():
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not file_path:
        return 0
    relative = relative_path(file_path)
    if is_protected(relative):
        print(f"BLOCKED: {relative} is a trust anchor. Signatures are written only by "
              f"lib/sign_gate.py run by the named person with their own key, and governance/ "
              f"only by a person enrolling a signer. No file was written.", file=sys.stderr)
        return 2
    if not is_artifact(relative):
        return 0
    target = Path(file_path)
    current = target.read_text() if target.exists() else ""
    try:
        new = yaml.safe_load(proposed_text(tool_input, current))
    except yaml.YAMLError as error:
        print(f"BLOCKED: {relative} would not be valid YAML: {error}", file=sys.stderr)
        return 2
    old = yaml.safe_load(current) if current.strip() else None
    old_state = {k: (old or {}).get(k) for k in STATE_FIELDS}
    new_state = {k: (new or {}).get(k) if isinstance(new, dict) else None for k in STATE_FIELDS}
    if isinstance(new, dict) and new_state != old_state and (
            new.get("status") == "exited" or new.get("exited") or new.get("exited_to")):
        print(f"BLOCKED: {relative}: an exit is written only by `python3 lib/lifecycle.py advance`, "
              f"which verifies the signed record first. Direct edits of status, exited or exited_to "
              f"to an exit are refused. No file was written.", file=sys.stderr)
        return 2
    problems = validate(new, signing.load_record(target), old)
    if problems:
        print(message(relative, problems), file=sys.stderr)
        return 2
    return 0


def git(*args, check=True):
    return subprocess.run(["git", "-C", str(signing.root()), *args], capture_output=True,
                          text=True, check=check).stdout


def check_since(base):
    """Validate everything that changed since `base`. The CI and pre-commit entry point."""
    status = 0
    changes = git("diff", "--name-status", "--no-renames", base, "--", "lifecycle", "governance").splitlines()
    if not changes:
        print(f"ok  no lifecycle or governance changes since {base}")
    for line in changes:
        code, name = line.split("\t", 1)
        relative = Path(name)
        problems = []
        if name.endswith(".signature.yaml"):
            if code != "A":
                problems.append("a signed record is immutable once committed: it was modified or deleted")
            else:
                problems.extend(signing.verify(yaml.safe_load((signing.root() / name).read_text())))
        elif name.startswith("governance/"):
            print(f"note  {name} changed: a person enrolled or removed a signer. Review required (CODEOWNERS).")
        elif is_artifact(relative):
            if code == "D":
                problems.append("append-only: an artifact was deleted")
            else:
                old = yaml.safe_load(git("show", f"{base}:{name}", check=False) or "null")
                problems.extend(check_file(signing.root() / name, old))
        if problems:
            print(message(name, problems), file=sys.stderr)
            status = 2
        else:
            print(f"ok  {name}")
    return status


def main(argv):
    if argv[:1] == ["--hook"]:
        return hook()
    if argv[:1] == ["--base"] and len(argv) == 2:
        return check_since(argv[1])
    paths = (sorted(p for p in signing.root().glob("lifecycle/*/*.yaml")
                    if not p.name.endswith(".signature.yaml"))
             if argv[:1] == ["--all"] else [Path(a) for a in argv])
    if not paths:
        print(__doc__)
        return 1
    status = 0
    for path in paths:
        problems = check_file(path)
        if problems:
            print(message(path, problems), file=sys.stderr)
            status = 2
        else:
            print(f"ok  {path}")
    return status


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as error:  # fail closed: a broken control must not let a write through
        print(f"BLOCKED: the gate guard failed internally and refuses by default: "
              f"{type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(2)
