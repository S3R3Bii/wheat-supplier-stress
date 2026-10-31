"""Stable exact finite-scenario files and historical byte guards."""

from pathlib import Path
import json, csv, hashlib
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(n):
    return json.loads((ROOT / n).read_bytes())


def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((json.dumps(x, indent=2, sort_keys=True) + "\n").encode())


def read(p):
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def table(p, rows, fields=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def history():
    x = load("HISTORY_SOURCE_HOLD.json")
    for n, h in x["files"].items():
        assert sha(ROOT / n) == h, ("original held-source/code bytes changed", n)
    gate = load("data/fao/input_gate.json")
    assert (
        gate["status"] == "FAIL_SOURCE_QUALIFICATION"
        and gate["failed_gates"]
        == ["common_support:143:2020:coverage_80_to_105_percent"]
        and gate["scenario_outputs_computed"] is False
    )
    assert load("data/input_receipt.json")["status"] != "PASS_SOURCE_QUALIFICATION"
    return len(x["files"])
