"""Replay all conditional finite-network accounts in a separate directory."""

from pathlib import Path
import sys, subprocess, argparse, json, hashlib

ROOT = Path(__file__).resolve().parents[1]
NAMES = [
    n + "_" + str(y) + e
    for y in [2019, 2020]
    for n, e in [
        ("endpoints", ".csv"),
        ("flows", ".csv"),
        ("cuts", ".csv"),
        ("importers", ".csv"),
        ("suppliers", ".csv"),
        ("summary", ".json"),
    ]
] + ["summary.json", "exercise.json"]


def main(out, analysis_only):
    assert not out.exists() and out.resolve() != (ROOT / "results/bounds").resolve()

    def call(n, *a):
        subprocess.run(
            [sys.executable, str(ROOT / "src" / n), *map(str, a)], cwd=ROOT, check=True
        )

    call("bounds_freeze.py")
    before = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "data").rglob("*")
        if p.is_file()
    }
    for y in [2019, 2020]:
        call("bounds_analyze.py", "--year", y, "--replay", "--out", out)
        call("bounds_check.py", "--year", y, "--out", out)
    call("bounds_summarize.py", "--out", out)
    call("bounds_exercise.py", "--out", out)
    for n in NAMES:
        assert (out / n).read_bytes() == (ROOT / "results/bounds" / n).read_bytes(), n
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=True,
    )
    if not analysis_only:
        call("bounds_check_figures.py")
        call("bounds_check_paper.py")
        call("bounds_check_exercise.py")
    after = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "data").rglob("*")
        if p.is_file()
    }
    assert before == after
    receipt = dict(
        status="PASS",
        python=sys.version.split()[0],
        reproduced_files=NAMES,
        unchanged_source_files=len(before),
        native_redownload=False,
        qualification="Saved source-informed scenario replay; no actual spare-supply, original-vintage or predictive certification.",
    )
    (out / "REPLAY_RECEIPT.json").write_bytes(
        (json.dumps(receipt, indent=2) + "\n").encode()
    )
    print("PASS_BOUNDS_REPLAY", sys.version.split()[0], len(NAMES), len(before))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--analysis-only", action="store_true")
    a = p.parse_args()
    main(a.out, a.analysis_only)
