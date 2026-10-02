"""Regression cases for the lifecycle guard. Run: python3 -m unittest discover tests

A throwaway SSH key signs the records, so the cryptographic check runs for real.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import signing  # noqa: E402
import validate_gate as guard  # noqa: E402

REAL = ROOT / "lifecycle" / "02-discovery" / "OPPORTUNITY-04.yaml"
GUARD = ROOT / "lib" / "validate_gate.py"
STATEMENT = "Build, as drafted."

_tmp = None
_keys = {}


def setUpModule():
    global _tmp
    _tmp = tempfile.TemporaryDirectory()
    gov = Path(_tmp.name) / "governance"
    gov.mkdir()
    people = {"Ana Fialho": ("product lead", "ana@portwell.test"),
              "Kofi Adjei": ("engineering manager", "kofi@portwell.test")}
    lines, signers = [], []
    for person, (role, principal) in people.items():
        key = Path(_tmp.name) / principal
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
        _keys[person] = key
        public = Path(str(key) + ".pub").read_text().strip()
        lines.append(f'{principal} namespaces="portwell-gate" {public}')
        signers.append({"person": person, "role": role, "principal": principal})
    (gov / "allowed_signers").write_text("\n".join(lines) + "\n")
    (gov / "signers.yaml").write_text(yaml.safe_dump({"signers": signers}))
    os.environ["PORTWELL_GOVERNANCE"] = str(gov)


def tearDownModule():
    os.environ.pop("PORTWELL_GOVERNANCE", None)
    _tmp.cleanup()


def real_artifact():
    return yaml.safe_load(REAL.read_text())


def make_record(artifact, person="Ana Fialho", outcome="build", kind="gate", statement=STATEMENT):
    definition = guard.load_definition(artifact["stage"])
    record = {
        "kind": kind, "item": artifact["item"], "stage": artifact["stage"],
        "gate": artifact["gate"]["id"] if kind == "gate" else None,
        "outcome": outcome if kind == "gate" else "exit",
        "person": person, "role": "product lead", "statement": statement, "date": "2026-09-30",
        "sections_sha256": signing.sections_digest(artifact, guard.signed_sections(definition)),
    }
    return signing.sign(record, _keys[person])


def exit_attempt(exited_to="03-ready-for-development"):
    artifact = copy.deepcopy(real_artifact())
    artifact.update(status="exited", exited="2026-09-30", exited_to=exited_to)
    return artifact


def ready(artifact):
    """Make every non-signature precondition of a build exit true, to isolate one failure."""
    for consent in artifact["gate"]["consents"]:
        consent.update(state="consented", response="Agreed in writing.", responded_on="2026-09-29")
    artifact["verification"]["outcome"] = "passed"
    return artifact


def has(problems, text):
    return any(text in p for p in problems)


class RefusedBeforeTheControl(unittest.TestCase):
    """Writes the repository used to accept because only prose forbade them."""

    def test_unsigned_exit(self):
        self.assertTrue(has(guard.validate(exit_attempt(), None), "no signed record"))

    def test_forged_signature_block_in_artifact(self):
        artifact = ready(exit_attempt())
        artifact["gate"]["signature"] = {"person": "Ana Fialho", "role": "product lead",
                                         "statement": STATEMENT, "date": "2026-09-30"}
        problems = guard.validate(artifact, None)
        self.assertTrue(has(problems, "forgery"), problems)

    def test_signature_by_the_wrong_person(self):
        artifact = ready(exit_attempt())
        record = make_record(artifact, person="Kofi Adjei")
        self.assertTrue(has(guard.validate(artifact, record), "must be signed by Ana Fialho"))

    def test_tampered_statement_does_not_verify(self):
        artifact = ready(exit_attempt())
        record = make_record(artifact)
        record["statement"] = "A different decision."
        self.assertTrue(has(guard.validate(artifact, record), "does not verify"))

    def test_sections_changed_after_signing(self):
        artifact = ready(exit_attempt())
        record = make_record(artifact)
        artifact["gate"]["pack"]["summary"] = "Edited after the decider signed."
        self.assertTrue(has(guard.validate(artifact, record), "changed after signing"))

    def test_unenrolled_signer(self):
        artifact = ready(exit_attempt())
        record = make_record(artifact)
        record["person"] = "Nobody Enrolled"
        self.assertTrue(has(guard.validate(artifact, record), "is not enrolled"))

    def test_objections_block_advancing_even_when_signed(self):
        artifact = exit_attempt()
        artifact["verification"]["outcome"] = "passed"
        problems = guard.validate(artifact, make_record(artifact))
        self.assertTrue(has(problems, "Rui Bastos is 'objected'"), problems)
        self.assertTrue(has(problems, "Kofi Adjei is 'not-on-record'"), problems)

    def test_failed_verification_blocks_advancing(self):
        artifact = ready(exit_attempt())
        artifact["verification"]["outcome"] = "failed"
        self.assertTrue(has(guard.validate(artifact, make_record(artifact)), "verification.outcome"))

    def test_consented_without_words_or_date(self):
        artifact = real_artifact()
        artifact["gate"]["consents"][0].update(state="consented", response="not on record",
                                               responded_on=None)
        problems = guard.validate(artifact, None)
        self.assertTrue(has(problems, "no written response") and has(problems, "no response date"))

    def test_wrong_target_and_staying_outcome(self):
        artifact = ready(exit_attempt(exited_to="05-review"))
        self.assertTrue(has(guard.validate(artifact, make_record(artifact)), "allows only"))
        artifact = ready(exit_attempt(exited_to="02-discovery"))
        problems = guard.validate(artifact, make_record(artifact, outcome="defer"))
        self.assertTrue(has(problems, "cannot be exited"), problems)

    def test_append_only(self):
        old = real_artifact()
        new = copy.deepcopy(old)
        new["status_log"][0]["reason"] = "rewritten history"
        del new["sources"][0]
        problems = guard.validate(new, None, old)
        self.assertTrue(has(problems, "status_log line 1") and has(problems, "sources"), problems)

    def test_state_change_needs_a_status_log_line(self):
        old = real_artifact()
        new = copy.deepcopy(old)
        new["status"] = "blocked"
        self.assertTrue(has(guard.validate(new, None, old), "without a new status_log line"))


class ExitChecksOfUngatedStages(unittest.TestCase):
    def artifact(self, stage, **sections):
        return {"item": "X-1", "stage": stage, "status": "exited", "exited": "2026-09-30",
                "exited_to": {"03-ready-for-development": "04-in-development",
                              "04-in-development": "05-review"}[stage], **sections}

    def test_verbal_estimate_does_not_satisfy_exit(self):
        accepted = {"person": "Kofi Adjei", "role": "engineering manager", "statement": "Accepted.",
                    "date": "2026-09-30"}
        artifact = self.artifact("03-ready-for-development", engineering_acceptance={
            "estimate": {"written_by": "Kofi Adjei", "dated": "2026-09-29", "verbal": "Kofi, 2026-09-28"},
            "accepted": accepted})
        record = make_record({**artifact, "gate": {"id": None}}, person="Kofi Adjei", kind="exit")
        self.assertTrue(has(guard.validate(artifact, record), "estimate.verbal must be empty"))

    def test_open_deviation_needing_g2_blocks_exit(self):
        artifact = self.artifact("04-in-development", build_record={
            "deviations": [{"what": "x", "needs_g2": True}],
            "declared_ready": {"person": "Kofi Adjei", "date": "2026-09-30"}})
        record = make_record({**artifact, "gate": {"id": None}}, person="Kofi Adjei", kind="exit")
        self.assertTrue(has(guard.validate(artifact, record), "no deviation needing G2"))


class AcceptedAfterTheControl(unittest.TestCase):
    def test_current_records_pass(self):
        for path in sorted(ROOT.glob("lifecycle/*/*.yaml")):
            if not path.name.endswith(".signature.yaml"):
                self.assertEqual(guard.check_file(path), [], path)

    def test_signed_consented_verified_build_passes(self):
        artifact = ready(exit_attempt())
        self.assertEqual(guard.validate(artifact, make_record(artifact)), [])

    def test_signed_reject_needs_no_consents_or_verification(self):
        artifact = exit_attempt(exited_to="terminal")
        self.assertEqual(guard.validate(artifact, make_record(artifact, outcome="reject")), [])


class FailsClosed(unittest.TestCase):
    def run_guard(self, *args, stdin=None, env=None):
        return subprocess.run([sys.executable, str(GUARD), *args], input=stdin, capture_output=True,
                              text=True, env={**os.environ, **(env or {})})

    def test_garbage_on_hook_stdin_blocks(self):
        result = self.run_guard("--hook", stdin="not json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("refuses by default", result.stderr)

    def test_corrupt_artifact_blocks_instead_of_crashing_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.yaml"
            bad.write_text("a: [unclosed")
            self.assertEqual(self.run_guard(str(bad)).returncode, 2)

    def test_broken_definition_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "states", root / "states")
            (root / "states" / "02-discovery" / "definition.yaml").write_text("{ broken")
            target = root / "lifecycle" / "02-discovery"
            target.mkdir(parents=True)
            artifact = ready(exit_attempt())
            (target / "OPPORTUNITY-04.yaml").write_text(yaml.safe_dump(artifact))
            result = self.run_guard(str(target / "OPPORTUNITY-04.yaml"), env={"PORTWELL_ROOT": tmp})
            self.assertEqual(result.returncode, 2)


class HookProtocol(unittest.TestCase):
    def run_hook(self, tool_input):
        return subprocess.run([sys.executable, str(GUARD), "--hook"],
                              input=json.dumps({"tool_input": tool_input}), capture_output=True, text=True)

    def test_direct_exit_edit_is_refused_even_if_fully_signed(self):
        artifact = ready(exit_attempt())
        result = self.run_hook({"file_path": str(REAL), "content": yaml.safe_dump(artifact)})
        self.assertEqual(result.returncode, 2)
        self.assertIn("lifecycle.py advance", result.stderr)

    def test_edit_that_sets_exited_to_is_refused(self):
        result = self.run_hook({"file_path": str(REAL), "old_string": "exited_to: null",
                                "new_string": "exited_to: 03-ready-for-development"})
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_multi_edit_payload_is_applied(self):
        result = self.run_hook({"file_path": str(REAL), "edits": [
            {"old_string": "exited: null", "new_string": 'exited: "2026-09-30"'}]})
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_signature_file_and_governance_are_trust_anchors(self):
        for name in ("lifecycle/02-discovery/OPPORTUNITY-04.signature.yaml", "governance/signers.yaml",
                     "governance/allowed_signers"):
            result = self.run_hook({"file_path": str(ROOT / name), "content": "x"})
            self.assertEqual(result.returncode, 2, name)
            self.assertIn("trust anchor", result.stderr)

    def test_consent_edit_without_words_is_refused(self):
        result = self.run_hook({"file_path": str(REAL), "old_string": "state: objected}",
                                "new_string": 'state: consented, x: ""}'})
        self.assertEqual(result.returncode, 0, "the first consent already carries words")

    def test_other_files_are_ignored(self):
        self.assertEqual(self.run_hook({"file_path": str(ROOT / "board.md"), "content": "x"}).returncode, 0)


class AdvanceCli(unittest.TestCase):
    """End to end in a scratch copy: sign with a key, advance, and check what was written."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "states", self.root / "states")
        self.dir = self.root / "lifecycle" / "02-discovery"
        self.dir.mkdir(parents=True)
        self.path = self.dir / "OPPORTUNITY-04.yaml"
        self.path.write_text(REAL.read_text())
        self.original = self.path.read_text()
        self.env = {**os.environ, "PORTWELL_ROOT": self.tmp.name}

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "lib" / "lifecycle.py"), *args],
                              capture_output=True, text=True, env=self.env)

    def test_advance_without_signed_record_writes_nothing(self):
        result = self.run_cli("advance", "OPPORTUNITY-04", "02-discovery")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.path.read_text(), self.original)

    def test_advance_with_unmet_consents_writes_nothing_even_when_signed(self):
        record = make_record(yaml.safe_load(self.path.read_text()))
        (self.dir / "OPPORTUNITY-04.signature.yaml").write_text(yaml.safe_dump(record))
        result = self.run_cli("advance", "OPPORTUNITY-04", "02-discovery")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("advancing needs every consent", result.stderr)
        self.assertEqual(self.path.read_text(), self.original)

    def test_signed_reject_advances_and_keeps_comments(self):
        artifact = yaml.safe_load(self.path.read_text())
        record = make_record(artifact, outcome="reject")
        (self.dir / "OPPORTUNITY-04.signature.yaml").write_text(yaml.safe_dump(record))
        result = self.run_cli("advance", "OPPORTUNITY-04", "02-discovery", "--date", "2026-09-30")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.path.read_text()
        after = yaml.safe_load(text)
        self.assertEqual((after["status"], after["exited_to"], after["gate"]["outcome"]),
                         ("exited", "terminal", "reject"))
        self.assertEqual(len(after["status_log"]), len(artifact["status_log"]) + 1)
        self.assertIn("# most severe open episode", text)
        self.assertEqual(guard.validate(after, record, artifact), [])


class ChangesSinceBase(unittest.TestCase):
    """The CI and pre-commit path, in a scratch git repository."""

    def git(self, *args):
        subprocess.run(["git", "-C", self.tmp.name, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        shutil.copytree(ROOT / "states", root / "states")
        (root / "lifecycle" / "02-discovery").mkdir(parents=True)
        self.path = root / "lifecycle" / "02-discovery" / "OPPORTUNITY-04.yaml"
        shutil.copy(REAL, self.path)
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.env = {**os.environ, "PORTWELL_ROOT": self.tmp.name}

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        return subprocess.run([sys.executable, str(GUARD), "--base", "HEAD"], capture_output=True,
                              text=True, env=self.env)

    def test_unchanged_passes(self):
        self.assertEqual(self.check().returncode, 0)

    def test_rewriting_history_is_caught_even_when_written_by_the_shell(self):
        self.path.write_text(self.path.read_text().replace("legacy entry", "nothing happened", 1)
                             .replace("reason: ", "reason: REWRITTEN ", 1))
        result = self.check()
        self.assertEqual(result.returncode, 2)
        self.assertIn("append-only", result.stderr)

    def test_deleting_an_artifact_is_caught(self):
        self.path.unlink()
        self.assertEqual(self.check().returncode, 2)

    def test_forged_exit_by_shell_is_caught(self):
        text = self.path.read_text().replace("exited: null", 'exited: "2026-09-30"', 1)
        text = text.replace("exited_to: null", "exited_to: 03-ready-for-development", 1)
        self.path.write_text(text)
        result = self.check()
        self.assertEqual(result.returncode, 2)
        self.assertIn("no signed record", result.stderr)


if __name__ == "__main__":
    unittest.main()
