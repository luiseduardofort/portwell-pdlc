#!/usr/bin/env python3
"""Operating measures: from eval results and the lifecycle record to reports/operating-report.md.

  measures.py [--results evals/results/<run>.jsonl] [--as-of YYYY-MM-DD] [--out reports/operating-report.md]

Every number says where it came from. A measure with no data is written "not measured", never 0.
"""
import argparse
import datetime
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signing  # noqa: E402

PEOPLE = ("Ana Fialho", "Rui Bastos", "Tomas Silva", "Kofi Adjei", "Gabriela Rocha", "Sofia Marques")
NOT_MEASURED = "not measured"


def as_date(value):
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def shorten(text, limit=160):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " (truncated)"


def pct(part, whole):
    return NOT_MEASURED if not whole else f"{100 * part / whole:.0f}% ({part}/{whole})"


# ---------------------------------------------------------------- agent measures

def agent_measures(lines, grades):
    runs = len(lines)
    accepted = [l for l in lines if l["passed"]]
    cost = [l["signals"].get("cost_usd") for l in lines if l["signals"].get("cost_usd") is not None]
    tokens = [sum(v for k, v in (l["signals"].get("usage") or {}).items()
                  if k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                           "cache_read_input_tokens") and isinstance(v, (int, float))) for l in lines]
    duration = [l["signals"].get("duration_ms") or 0 for l in lines]
    cycles = [l["signals"].get("permission_denials", 0) + 1 for l in accepted]
    first_green = {}
    for line in sorted(lines, key=lambda l: (l["case"], l["trial"])):
        if line["passed"] and line["case"] not in first_green:
            first_green[line["case"]] = line["trial"]
    adversarial = [l for l in lines if l["kind"] == "adversarial"]
    named = [l for l in lines if any(p in l.get("answer", "") for p in PEOPLE)]
    graded = [g for g in grades if g.get("run_id") and g.get("case")]
    corrections = [g.get("corrections", 0) for g in graded]
    escaped = [g for g in graded if g.get("layer1_passed") and g.get("human_verdict") == "fail"]
    return {
        "runs": runs,
        "accepted": len(accepted),
        "convergence_rate": pct(len(accepted), runs),
        "iterations_to_green": round(sum(cycles) / len(cycles), 2) if cycles else NOT_MEASURED,
        "trials_to_first_pass": first_green,
        "handback_on_adversarial": pct(sum(l["passed"] for l in adversarial), len(adversarial)),
        "answers_naming_a_person": pct(len(named), runs),
        "cost_per_accepted_usd": round(sum(cost) / len(accepted), 4) if accepted and cost else NOT_MEASURED,
        "tokens_per_accepted": round(sum(tokens) / len(accepted)) if accepted and any(tokens) else NOT_MEASURED,
        "minutes_per_accepted": round(sum(duration) / 60000 / len(accepted), 2) if accepted else NOT_MEASURED,
        "total_cost_usd": round(sum(cost), 4) if cost else NOT_MEASURED,
        "boundary_attempts_per_run": round(sum(l["signals"].get("permission_denials", 0) for l in lines) / runs, 2)
        if runs else NOT_MEASURED,
        "correction_ratio": round(sum(corrections) / len(graded), 2) if graded else NOT_MEASURED,
        "escaped_defects": pct(len(escaped), len(graded)) if graded else NOT_MEASURED,
        "attribution": Counter(f["attribution"] for l in lines for f in l["failures"]),
        "by_case": by_case(lines),
    }


def by_case(lines):
    table = defaultdict(lambda: {"trials": 0, "passed": 0, "kind": None, "skill": None})
    for line in lines:
        row = table[line["case"]]
        row["trials"] += 1
        row["passed"] += bool(line["passed"])
        row["kind"], row["skill"] = line["kind"], line["skill"]
    return dict(sorted(table.items()))


# ---------------------------------------------------------------- lifecycle measures

def lifecycle_measures(root, as_of):
    episodes, gates = [], []
    for path in sorted((root / "lifecycle").glob("*/*.yaml")):
        if path.name.endswith(".signature.yaml"):
            continue
        artifact = yaml.safe_load(path.read_text())
        for line in artifact.get("status_log") or []:
            since, until = as_date(line.get("since")), as_date(line.get("until"))
            episodes.append({
                "artifact": path.relative_to(root).as_posix(), "status": line.get("status"),
                "since": line.get("since"), "open": until is None,
                "days": ((until or as_of) - since).days if since else None,
                "waiting_on": line.get("waiting_on"), "escalate_to": line.get("escalate_to")})
        gate = artifact.get("gate") or {}
        if gate:
            entered, deadline = as_date(artifact.get("entered")), as_date(gate.get("deadline"))
            signed = as_date((gate.get("signature") or {}).get("date"))
            gates.append({
                "artifact": path.relative_to(root).as_posix(), "gate": gate.get("id"),
                "signed": signed is not None,
                "days_open": ((signed or as_of) - entered).days if entered else None,
                "days_past_deadline": (as_of - deadline).days if deadline and not signed and as_of > deadline else 0})
    reasons = []
    for path in sorted((root / "lifecycle").glob("*/*.yaml")):
        if path.name.endswith(".signature.yaml"):
            continue
        for line in yaml.safe_load(path.read_text()).get("status_log") or []:
            if line.get("status") in ("blocked", "escalated", "correction-required"):
                reasons.append({"status": line.get("status"), "since": line.get("since"),
                                "reason": shorten(str(line.get("reason", ""))),
                                "waiting_on": line.get("waiting_on")})
    corrections = [e for e in episodes if e["status"] == "correction-required"]
    return {"episodes": episodes, "gates": gates, "handback_reasons": reasons,
            "decisions_signed": sum(g["signed"] for g in gates),
            "correction_episodes": len(corrections),
            "open_corrections_days": [e["days"] for e in corrections if e["open"]]}


# ---------------------------------------------------------------- report

def render(agent, life, results_name, as_of):
    out = [
        "# Operating report", "",
        f"As of {as_of}. Eval results: `{results_name or 'none'}`. Lifecycle: `lifecycle/`.",
        "Generated by `lib/measures.py`. Do not edit by hand.", "",
        "No measure here should be read alone, and none is a productivity claim. A high pass rate on",
        "eight cases says nothing about the harness on items it has not seen.", "",
        "## Accepted change per unit of human attention", "",
    ]
    if agent:
        out += [
            "| Measure | Value | Source |", "| :- | :- | :- |",
            f"| Runs | {agent['runs']} | eval results |",
            f"| Accepted outputs | {agent['accepted']} | runs that passed layer 1 |",
            f"| Convergence rate | {agent['convergence_rate']} | accepted with no human intervention |",
            f"| Handback on adversarial cases | {agent['handback_on_adversarial']} | refused and returned to a person |",
            f"| Answers naming a person | {agent['answers_naming_a_person']} | heuristic: a named owner appears in the answer |",
            f"| Cost per accepted output (USD) | {agent['cost_per_accepted_usd']} | session `total_cost_usd` |",
            f"| Tokens per accepted output | {agent['tokens_per_accepted']} | session `usage` |",
            f"| Minutes per accepted output | {agent['minutes_per_accepted']} | session `duration_ms` |",
            f"| Total cost of the run (USD) | {agent['total_cost_usd']} | sum over all runs, failed included |",
            f"| Boundary attempts per run | {agent['boundary_attempts_per_run']} | tool calls denied by permissions or the hook |",
            f"| Iterations to green | {agent['iterations_to_green']} | per accepted run: blocks by the hook or permissions before the result, plus one |",
            f"| Correction ratio | {agent['correction_ratio']} | `evals/human-grades.yaml` |",
            f"| Escaped defects | {agent['escaped_defects']} | passed layer 1, failed the human grade |",
            "", "### By case", "", "| Case | Kind | Skill | Passed | Trials to first pass |",
            "| :- | :- | :- | :- | :- |",
        ]
        for case, row in agent["by_case"].items():
            out.append(f"| {case} | {row['kind']} | {row['skill']} | {row['passed']}/{row['trials']} | "
                       f"{agent['trials_to_first_pass'].get(case, 'not reached')} |")
        out += ["", "### Failure attribution", "", "| Component | Failures |", "| :- | -: |"]
        out += [f"| {k} | {v} |" for k, v in agent["attribution"].most_common()] or ["| none | 0 |"]
    else:
        out += ["No live eval results recorded. Every agent measure is not measured."]
    out += [
        "", "## Delivery baseline, PDLC reading", "",
        "| DORA measure | PDLC reading | Value |", "| :- | :- | :- |",
        f"| Deployment frequency | Decisions signed | {life['decisions_signed']} |",
        "| Lead time for change | Days from stage entry to signed gate | "
        + "; ".join(f"{g['gate']}: {g['days_open']} days, {'signed' if g['signed'] else 'unsigned'}" for g in life["gates"]) + " |",
        f"| Change failure rate | Correction-required episodes | {life['correction_episodes']} |",
        "| Mean time to restore | Days in correction-required, open episodes | "
        + (", ".join(str(d) for d in life["open_corrections_days"]) or "none open") + " |",
        "", "## Escalation: why work hands back to a person", "",
        "From `status_log` lines with status blocked, escalated or correction-required.", "",
        "| Status | Since | Waiting on | Reason |", "| :- | :- | :- | :- |",
        *[f"| {r['status']} | {r['since']} | {r['waiting_on']} | {r['reason']} |" for r in life["handback_reasons"]],
        "", "Human attention is not measured directly. Its proxies here are the open waits below, the",
        "correction ratio and the escaped defects, which need `evals/human-grades.yaml` to be filled.",
        "", "## Track outcome: time waiting on a named person", "",
        "| Artifact | Status | Since | Days | Waiting on | Escalate to |", "| :- | :- | :- | -: | :- | :- |",
    ]
    for e in life["episodes"]:
        if e["open"]:
            out.append(f"| {e['artifact']} | {e['status']} | {e['since']} | {e['days']} | {e['waiting_on']} | {e['escalate_to']} |")
    for g in life["gates"]:
        if g["days_past_deadline"]:
            out.append(f"\n{g['gate']} in `{g['artifact']}` is {g['days_past_deadline']} days past its deadline, unsigned.")
    return "\n".join(out) + "\n"


def main(argv):
    root = signing.root()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results")
    parser.add_argument("--as-of", default=datetime.date.today().isoformat())
    parser.add_argument("--out", default=str(root / "reports" / "operating-report.md"))
    args = parser.parse_args(argv)
    results = args.results
    baseline = root / "evals" / "baseline.json"
    if not results and baseline.exists():
        results = str(root / json.loads(baseline.read_text())["results"])
    lines = [json.loads(l) for l in Path(results).read_text().splitlines() if l.strip()] if results else []
    grades_path = root / "evals" / "human-grades.yaml"
    grades = (yaml.safe_load(grades_path.read_text()) or {}).get("grades") or [] if grades_path.exists() else []
    as_of = datetime.date.fromisoformat(args.as_of)
    report = render(agent_measures(lines, grades) if lines else None, lifecycle_measures(root, as_of),
                    Path(results).name if results else None, as_of)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(report)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
