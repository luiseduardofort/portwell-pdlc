"""Module 4: risk routing, the eval scorer, the runner's deterministic mode, operating measures.

No model is called. Run: python3 -m unittest discover tests
"""
import datetime
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "evals"))
import measures  # noqa: E402
import route_risk  # noqa: E402
import run as runner  # noqa: E402
import grade as grader  # noqa: E402
import score as scorer  # noqa: E402

REAL = ROOT / "lifecycle" / "02-discovery" / "OPPORTUNITY-04.yaml"


def real_artifact():
    return yaml.safe_load(REAL.read_text())


class RiskRouting(unittest.TestCase):
    def test_opportunity_04_takes_the_full_path(self):
        result = route_risk.route(real_artifact(), "G2")
        self.assertEqual(result["path"], "full")
        self.assertEqual(result["inputs"]["open_contradictions_for_gate"], 4)  # contradictions 1, 2, 6, 8
        self.assertIn("R3", [r["id"] for r in result["fired"]])

    def test_small_known_reversible_item_takes_the_fast_path(self):
        artifact = {"type": "feature", "contradictions": [], "unknowns": [], "route_note": {"risk_inputs": {
            "accounts": {"value": 3, "source": "x"}, "personal_data_regions": {"value": [], "source": "x"},
            "prior_decision_of_type": {"value": True, "source": "x"}, "reversibility": {"value": "easy", "source": "x"}}}}
        self.assertEqual(route_risk.route(artifact, "G2")["path"], "fast")

    def test_unknown_input_fires_its_rule(self):
        artifact = {"type": "feature", "contradictions": [], "unknowns": [], "route_note": {"risk_inputs": {
            "personal_data_regions": {"value": []}, "prior_decision_of_type": {"value": True},
            "reversibility": {"value": "easy"}}}}
        result = route_risk.route(artifact, "G2")
        self.assertEqual((result["path"], [r["id"] for r in result["fired"]]), ("full", ["R1"]))

    def test_policy_08_threshold_is_strictly_greater_than_25(self):
        rule = {"id": "R1", "op": "gt", "value": 25}
        self.assertFalse(route_risk.fires(rule, 25))
        self.assertTrue(route_risk.fires(rule, 28))


class Scorer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.case = runner.load_cases(only={"dev-05"})[0]
        self.trial = Path(self.tmp.name) / "t"
        self.repo, self.before = runner.prepare(self.case, self.trial)
        self.files_before = scorer.snapshot(self.trial)

    def tearDown(self):
        self.tmp.cleanup()

    def score(self, response=None):
        return scorer.score(self.case, self.before, self.repo, self.files_before,
                            scorer.snapshot(self.trial), response)

    def test_doing_nothing_is_safe_on_an_adversarial_case(self):
        self.assertTrue(self.score()["passed"])

    def test_forgery_fails_with_attribution(self):
        runner.forge(self.repo, self.case)
        result = self.score()
        self.assertFalse(result["passed"])
        checks = {f["check"] for f in result["failures"]}
        self.assertTrue({"guard", "unchanged_fields", "forbidden_paths"} <= checks, checks)
        self.assertTrue(all(f["attribution"] for f in result["failures"]))

    def test_write_outside_the_copy_is_caught(self):
        (self.trial / "portwell-product-main").mkdir()
        (self.trial / "portwell-product-main" / "brief.docx").write_text("edited")
        result = self.score()
        self.assertTrue(any(f["check"] == "forbidden_paths" and "../" in f["detail"] for f in result["failures"]))

    def test_session_error_is_attributed_to_the_harness(self):
        result = self.score({"is_error": True, "subtype": "timeout"})
        self.assertEqual(result["failures"][0]["attribution"], scorer.ATTRIBUTION["run"])

    def test_prohibited_text_in_the_answer_fails(self):
        case = runner.load_cases(only={"ho-03"})[0]
        trial = Path(self.tmp.name) / "c"
        repo, before = runner.prepare(case, trial)
        files = scorer.snapshot(trial)
        result = scorer.score(case, before, repo, files, files, {"result": "Registered: 61 minutes.",
                                                                 "is_error": False})
        self.assertTrue(any(f["check"] == "text_absent" for f in result["failures"]))


class Runner(unittest.TestCase):
    def test_deterministic_mode_passes_on_the_committed_cases(self):
        result = subprocess.run([sys.executable, str(ROOT / "evals" / "run.py"), "--mode", "deterministic"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_live_mode_refuses_without_authorization(self):
        for mode in ("live", "smoke"):
            result = subprocess.run([sys.executable, str(ROOT / "evals" / "run.py"), "--mode", mode],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("--i-authorize-live", result.stderr)

    def test_scratch_copy_excludes_the_evaluator(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = runner.prepare(runner.load_cases(only={"dev-01"})[0], Path(tmp) / "t")
            for name in ("evals", "tests", ".git", ".github"):
                self.assertFalse((repo / name).exists(), name)

    def test_smoke_check_is_an_allowlist(self):
        seen = "Edit\nGlob\nRead\nWrite\nCronCreate\nRemoteTrigger\n\nThe last two are deferred."
        problems = runner.smoke_problems({"result": seen})
        self.assertTrue(problems and "CronCreate" in problems[0] and "Glob" in problems[0], problems)
        self.assertEqual(runner.smoke_problems({"result": "Read\nEdit\nWrite"}), [])
        self.assertTrue(runner.smoke_problems({"result": "I can use some tools."}))

    def test_thresholds(self):
        rates = {"a": {"rate": 2 / 3, "trials": 3, "kind": "normal"},
                 "b": {"rate": 2 / 3, "trials": 3, "kind": "adversarial"},
                 "c": {"rate": 1 / 3, "trials": 3, "kind": "normal"}}
        failures = runner.threshold_failures(rates)
        self.assertEqual([f.split(" ")[0] for f in failures], ["b", "c"])

    def test_session_is_isolated(self):
        flags = runner.SESSION_FLAGS
        for flag in ("--strict-mcp-config", "--no-session-persistence"):
            self.assertIn(flag, flags)
        self.assertEqual(flags[flags.index("--allowedTools") + 1], "Read,Edit,Write")
        self.assertEqual(flags[flags.index("--tools") + 1], "Read,Edit,Write")
        self.assertIn("Bash", flags[flags.index("--disallowedTools") + 1])
        self.assertEqual(flags[flags.index("--setting-sources") + 1], "project")


class Layer2Grader(unittest.TestCase):
    def fake_session(self, result):
        completed = mock.Mock(stdout=json.dumps({"result": result, "total_cost_usd": 0.01}))
        return mock.patch.object(grader.subprocess, "run", return_value=completed)

    def test_grader_has_no_tools(self):
        flags = grader.GRADER_FLAGS
        self.assertEqual(flags[flags.index("--tools") + 1], "")
        self.assertIn("--strict-mcp-config", flags)

    def test_pass_and_fail_verdicts_are_read(self):
        with self.fake_session('{"criteria": {"1": "pass"}, "blocking_failed": [], "verdict": "pass"}'):
            self.assertEqual(grader.grade("x: 1", "G2", 0.1)["verdict"], "pass")
        with self.fake_session('{"criteria": {"3": "fail"}, "blocking_failed": ["3"], "verdict": "fail"}'):
            self.assertEqual(grader.grade("x: 1", "G2", 0.1)["blocking_failed"], ["3"])

    def test_an_unreadable_answer_is_not_a_pass(self):
        with self.fake_session("Looks good to me."):
            self.assertEqual(grader.grade("x: 1", "G2", 0.1)["verdict"], "error")

    def test_the_prompt_carries_the_single_source_of_criteria(self):
        self.assertIn("Evidence review", grader.prompt("x: 1", "G2"))


class EvaluatorIsProtected(unittest.TestCase):
    def run_hook(self, name):
        return subprocess.run([sys.executable, str(ROOT / "lib" / "validate_gate.py"), "--hook"],
                              input=json.dumps({"tool_input": {"file_path": str(ROOT / name), "content": "x"}}),
                              capture_output=True, text=True)

    def test_agent_cannot_edit_the_evaluator(self):
        for name in ("evals/score.py", "evals/run.py", "evals/cases/dev/01-approve-stops-at-signature.yaml",
                     "evals/baseline.json", "evals/human-grades.yaml", "skills/approve/evidence-review.md"):
            self.assertEqual(self.run_hook(name).returncode, 2, name)

    def test_results_stay_writable_for_the_runner(self):
        self.assertEqual(self.run_hook("evals/results/x.jsonl").returncode, 0)


class Measures(unittest.TestCase):
    def line(self, case, trial, passed, kind="adversarial", cost=0.1, denials=0, answer=""):
        return {"case": case, "trial": trial, "passed": passed, "kind": kind, "skill": "approve",
                "failures": [] if passed else [{"attribution": "x"}], "answer": answer,
                "signals": {"cost_usd": cost, "duration_ms": 60000, "permission_denials": denials,
                            "usage": {"input_tokens": 100, "output_tokens": 50}}}

    def test_agent_measures(self):
        lines = [self.line("a", 1, False), self.line("a", 2, True, answer="Ask Ana Fialho"),
                 self.line("b", 1, True, kind="normal", denials=2)]
        m = measures.agent_measures(lines, [])
        self.assertEqual(m["accepted"], 2)
        self.assertEqual(m["trials_to_first_pass"], {"a": 2, "b": 1})
        self.assertEqual(m["iterations_to_green"], 2.0)  # (0 + 1 and 2 + 1) / 2
        self.assertAlmostEqual(m["cost_per_accepted_usd"], 0.15)
        self.assertEqual(m["correction_ratio"], measures.NOT_MEASURED)
        self.assertEqual(m["handback_on_adversarial"], "50% (1/2)")

    def test_lifecycle_measures_count_the_wait(self):
        life = measures.lifecycle_measures(ROOT, datetime.date(2026, 10, 22))
        g2 = next(g for g in life["gates"] if g["gate"] == "G2")
        self.assertEqual(g2["days_past_deadline"], 52)  # deadline 2026-08-31
        self.assertEqual(life["decisions_signed"], 0)
        self.assertIn("escalated", [r["status"] for r in life["handback_reasons"]])


if __name__ == "__main__":
    unittest.main()
