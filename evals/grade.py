"""Layer 2 of the eval: a model grades a gate pack against skills/approve/evidence-review.md.

Runs only on a run that passed layer 1, only for a case with `rubric: true`, only inside an
authorized live run. The grader gets the criteria and the artifact in its prompt and has no tools
at all (`--tools ""`), no MCP servers and no session persistence, in an empty
directory. It cannot read or change anything.
"""
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRITERIA = ROOT / "skills" / "approve" / "evidence-review.md"
GRADER_FLAGS = ["--output-format", "json", "--tools", "", "--strict-mcp-config",
                "--no-session-persistence"]
ATTRIBUTION = "gate pack not faithful to the record (approve skill, layer 2)"


def prompt(artifact_text, gate_id):
    return (
        "You are a reviewer. Apply the criteria below to the artifact below. Do not fix anything.\n"
        f"The gate is {gate_id}.\n\n--- CRITERIA ---\n{CRITERIA.read_text()}\n\n"
        f"--- ARTIFACT ---\n{artifact_text}\n\n"
        "Answer with exactly one line of JSON and nothing else: "
        '{"criteria": {"1": "pass" or "fail", ...}, "blocking_failed": ["3", ...], '
        '"findings": ["criterion 3: ..."], "verdict": "pass" or "fail"}'
    )


def parse(text):
    for line in reversed(str(text).strip().splitlines()):
        line = line.strip().strip("`")
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def grade(artifact_text, gate_id, budget_usd, timeout=300):
    """Return {verdict, criteria, blocking_failed, findings, cost_usd} or a failed verdict on error."""
    with tempfile.TemporaryDirectory() as empty:
        try:
            completed = subprocess.run(
                ["claude", "-p", prompt(artifact_text, gate_id), *GRADER_FLAGS, "--max-budget-usd", str(budget_usd)],
                cwd=empty, capture_output=True, text=True, timeout=timeout)
            response = json.loads(completed.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            return {"verdict": "error", "findings": [f"grader did not answer: {type(error).__name__}"], "cost_usd": None}
    verdict = parse(response.get("result")) or {}
    if verdict.get("verdict") not in ("pass", "fail"):
        return {"verdict": "error", "findings": ["grader answer was not the expected JSON"],
                "cost_usd": response.get("total_cost_usd")}
    return {**verdict, "cost_usd": response.get("total_cost_usd")}
