"""Bind actual source/history/method and complete development results before 2020."""

from bounds_common import ROOT, load, save, sha, history
import subprocess, argparse


def main(create):
    history()
    path = ROOT / "BOUNDS_FREEZE.json"
    if create:
        assert not path.exists()
        names = set(load("HISTORY_SOURCE_HOLD.json")["files"])
        names.update(
            "src/" + n
            for n in [
                "bounds_common.py",
                "bounds_inputs.py",
                "bounds_model.py",
                "bounds_analyze.py",
                "bounds_check.py",
                "bounds_exercise.py",
                "bounds_summarize.py",
                "bounds_freeze.py",
                "bounds_replay.py",
            ]
        )
        names.update(
            [
                "BOUNDS_PROTOCOL.md",
                "HISTORY_SOURCE_HOLD.json",
                ".gitattributes",
                "requirements.txt",
                "tests/test_bounds.py",
                "data/bounds_inputs.json",
                "data/bounds_support.csv",
                "data/bounds_pair_support.csv",
                "data/bounds_requests.json",
            ]
        )
        names.update(
            str(p.relative_to(ROOT)).replace("\\", "/")
            for p in (ROOT / "results/bounds").glob("*2019.*")
        )
        save(
            path,
            dict(
                source_checkpoint=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                hashes={n: sha(ROOT / n) for n in sorted(names)},
                qualification="Actual source,history,method,requests,tests and all development outputs fixed before later 2020 scenario summaries. Both years source informed; not a predictive holdout. Original source gate remains failed.",
            ),
        )
    x = load("BOUNDS_FREEZE.json")
    for n, h in x["hashes"].items():
        assert sha(ROOT / n) == h, n
    print("PASS_BOUNDS_DEVELOPMENT_FREEZE", len(x["hashes"]), sha(path))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--create", action="store_true")
    main(p.parse_args().create)
