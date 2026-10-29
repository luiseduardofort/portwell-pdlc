"""Signed gate records. A decision is an SSH signature made with the decider's own key.

The agent has no access to that key, so it can write the shape of a signature but never a valid
one. Verification uses `ssh-keygen -Y verify` and the allowlist in governance/allowed_signers.
"""
import datetime
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import yaml

NAMESPACE = "portwell-gate"
FIELDS = ("kind", "item", "stage", "gate", "outcome", "person", "role", "statement", "date",
          "sections_sha256")


def root():
    return Path(os.environ.get("PORTWELL_ROOT") or Path(__file__).resolve().parent.parent)


def governance_dir():
    return Path(os.environ.get("PORTWELL_GOVERNANCE") or root() / "governance")


def get_path(data, dotted):
    for part in dotted.split("."):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def sections_digest(artifact, paths):
    """Hash of the sections the signer attests to. Any later edit to them voids the signature."""
    payload = {p: get_path(artifact, p) for p in paths}
    blob = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def payload_bytes(record):
    body = {k: (str(record[k]) if record.get(k) is not None else None) for k in FIELDS}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def load_signers():
    path = governance_dir() / "signers.yaml"
    if not path.exists():
        return []
    return (yaml.safe_load(path.read_text()) or {}).get("signers") or []


def signer_for(person):
    for entry in load_signers():
        if entry.get("person") == person:
            return entry
    return None


def verify(record):
    """Return a list of problems with the cryptographic signature. Empty means valid."""
    signature = record.get("ssh_signature")
    if not signature:
        return ["signature record has no ssh_signature"]
    entry = signer_for(record.get("person"))
    if entry is None or not entry.get("principal"):
        return [f"{record.get('person')} is not enrolled in governance/signers.yaml"]
    allowed = governance_dir() / "allowed_signers"
    if not allowed.exists() or not allowed.read_text().strip():
        return ["governance/allowed_signers is empty: no key can sign"]
    with tempfile.TemporaryDirectory() as tmp:
        sig_file = Path(tmp) / "record.sig"
        sig_file.write_text(signature)
        try:
            result = subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", entry["principal"],
                 "-n", NAMESPACE, "-s", str(sig_file)],
                input=payload_bytes(record), capture_output=True, timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return [f"cannot run ssh-keygen to verify the signature: {error}"]
    if result.returncode != 0:
        return [f"SSH signature of {record.get('person')} does not verify against the allowed key"]
    return []


def sign(record, key_path):
    """Sign a record with the key at key_path. Run by the person, never by a skill."""
    result = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key_path), "-n", NAMESPACE],
        input=payload_bytes(record), capture_output=True, check=True,
    )
    return {**{k: record.get(k) for k in FIELDS}, "ssh_signature": result.stdout.decode()}


def signature_path(artifact_path):
    artifact_path = Path(artifact_path)
    return artifact_path.with_name(artifact_path.stem + ".signature.yaml")


def load_record(artifact_path):
    path = signature_path(artifact_path)
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text())


def today():
    return datetime.date.today().isoformat()
