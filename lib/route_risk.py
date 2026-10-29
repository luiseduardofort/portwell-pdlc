#!/usr/bin/env python3
"""Two-speed routing, by rule. The route skill reports this result instead of judging it.

  route_risk.py ARTIFACT [--gate G2]

Inputs come from the artifact. Counts of open contradictions and unknowns are computed. Account
count, regions, prior decision and reversibility are read from `route_note.risk_inputs`, which the
route skill writes with a source for each value. A missing input is `unknown`, and an unknown input
fires its rule. Prints the path and every rule that fired, with its input. Exit 0 always: routing
reports, it does not block.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing  # noqa: E402

UNKNOWN = "unknown"


def load_rules():
    return yaml.safe_load((signing.root() / "states" / "routing.yaml").read_text())


def gather(artifact, gate):
    route = artifact.get("route_note") or {}
    declared = route.get("risk_inputs") or {}
    contradictions = [c for c in artifact.get("contradictions") or []
                      if str(c.get("depends")) == gate and not c.get("resolved_by")]
    unknowns = [u for u in artifact.get("unknowns") or [] if gate in str(u.get("needed_for", ""))]

    def declared_value(key):
        entry = declared.get(key)
        if isinstance(entry, dict):
            return entry.get("value", UNKNOWN)
        return UNKNOWN if entry is None else entry

    return {
        "accounts": declared_value("accounts"),
        "personal_data_regions": declared_value("personal_data_regions"),
        "open_contradictions_for_gate": len(contradictions),
        "unknowns_for_gate": len(unknowns),
        "type": artifact.get("type") or UNKNOWN,
        "prior_decision_of_type": declared_value("prior_decision_of_type"),
        "reversibility": declared_value("reversibility"),
    }


def fires(rule, value):
    if value in (UNKNOWN, None, ""):
        return True
    op, target = rule["op"], rule.get("value")
    if op == "gt":
        return isinstance(value, (int, float)) and value > target
    if op == "eq":
        return value == target
    if op == "in":
        return value in target
    if op == "nonempty":
        return bool(value)
    raise ValueError(f"unknown operator {op} in rule {rule['id']}")


def route(artifact, gate):
    inputs = gather(artifact, gate)
    fired = [{"id": r["id"], "input": r["input"], "value": inputs[r["input"]], "because": r["because"]}
             for r in load_rules()["rules"] if fires(r, inputs[r["input"]])]
    return {"path": "full" if fired else "fast", "inputs": inputs, "fired": fired}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("artifact")
    parser.add_argument("--gate", default="G2")
    args = parser.parse_args(argv)
    result = route(yaml.safe_load(Path(args.artifact).read_text()), args.gate)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
