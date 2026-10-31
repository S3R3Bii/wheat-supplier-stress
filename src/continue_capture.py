"""One explicit slower continuation after the recorded provider wait; preserve prior bytes."""

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior-dir", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    prior = json.loads((args.prior_dir / "requests.json").read_text(encoding="utf-8"))
    failures = [r for r in prior if r["status"] != 200]
    assert (
        len(failures) == 1 and failures[0]["status"] == 429
    ), "This continuation only handles the single recorded transient rate limit"
    failed = failures[0]
    body = (args.prior_dir / failed["file"]).read_bytes()
    assert hashlib.sha256(body).hexdigest() == failed["sha256"]
    message = json.loads(body)["message"]
    wait = re.search(r"Try again in (\d+) seconds", message)
    assert wait, "No explicit provider wait; stop"
    seconds = int(wait[1])
    assert seconds <= 60, "Provider wait outside this bounded continuation"
    elapsed = (
        datetime.now(timezone.utc) - datetime.fromisoformat(failed["completed_utc"])
    ).total_seconds()
    time.sleep(max(0, seconds + 1 - elapsed))
    args.private_dir.mkdir(parents=True, exist_ok=False)
    receipts = []
    total = 0
    completed = {}
    for item in prior:
        if item["status"] != 200:
            continue
        data = (args.prior_dir / item["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
        envelope = json.loads(data)
        assert (
            isinstance(envelope.get("data"), list)
            and envelope.get("count") == len(envelope["data"]) < 500
        )
        shutil.copyfile(args.prior_dir / item["file"], args.private_dir / item["file"])
        record = item | {"inherited_successful_original_no_refetch": True}
        receipts.append(record)
        completed[item["file"]] = record
        total += len(envelope["data"])
    (args.private_dir / "prior_failed_requests.json").write_bytes(
        (json.dumps(failures, indent=2) + "\n").encode()
    )
    (args.private_dir / "requests.json").write_bytes(
        (json.dumps(receipts, indent=2) + "\n").encode()
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    previous_completed = None
    for request in json.loads(
        (ROOT / "data/source_requests.json").read_text(encoding="utf-8")
    ):
        if request["file"] in completed:
            assert request["url"] == completed[request["file"]]["url"]
            continue
        if previous_completed is not None:
            time.sleep(max(0, 10 - (time.monotonic() - previous_completed)))
        started = datetime.now(timezone.utc).isoformat()
        data = b""
        status = None
        headers = {}
        error = None
        try:
            with urlopen(
                Request(
                    request["url"],
                    headers={"User-Agent": "IndependentFoodTradeResearch/1.0"},
                ),
                timeout=90,
            ) as response:
                status = response.status
                headers = dict(response.headers.items())
                data = response.read()
        except HTTPError as exc:
            status = exc.code
            headers = dict(exc.headers.items())
            data = exc.read()
            error = str(exc)
        except Exception as exc:
            error = type(exc).__name__ + ":" + str(exc)
        previous_completed = time.monotonic()
        (args.private_dir / request["file"]).write_bytes(data)
        record = dict(
            request,
            started_utc=started,
            completed_utc=datetime.now(timezone.utc).isoformat(),
            status=status,
            headers={
                k: v
                for k, v in headers.items()
                if k.lower()
                in {
                    "content-type",
                    "content-length",
                    "etag",
                    "last-modified",
                    "date",
                    "retry-after",
                }
            },
            bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            protocol_commit=commit,
            python=platform.python_version(),
            error=error,
            explicit_slower_continuation=True,
            minimum_seconds_between_responses=10,
        )
        receipts.append(record)
        (args.private_dir / "requests.json").write_bytes(
            (json.dumps(receipts, indent=2) + "\n").encode()
        )
        print(
            json.dumps(
                {
                    k: record[k]
                    for k in ["kind", "year", "reporter", "status", "bytes", "error"]
                }
            ),
            flush=True,
        )
        assert (
            status == 200 and error is None
        ), "Second acquisition error/rate limit retained; stop without further continuation"
        envelope = json.loads(data)
        rows = envelope.get("data")
        assert (
            isinstance(rows, list)
            and not envelope.get("error")
            and envelope.get("count") == len(rows) < 500
        ), "Unexpected/error/capped envelope retained; stop"
        total += len(rows)
        assert total < 10000, "Total original-record bound exceeded; stop"
        print("ENVELOPE_OK", len(rows), "cumulative_records", total, flush=True)
    print("CAPTURE_COMPLETE", len(receipts), total, flush=True)


if __name__ == "__main__":
    main()
