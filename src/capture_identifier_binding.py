"""Capture only URLs changed by the documented publisher identifier correction."""

import argparse
import hashlib
import json
import platform
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
    assert len(prior) == 49 and all(
        r["status"] == 200 and r["error"] is None for r in prior
    ), "Finish/preserve the bounded earlier capture before identifier repair"
    requests = json.loads(
        (ROOT / "data/source_requests.json").read_text(encoding="utf-8")
    )
    old_urls = {r["url"]: r for r in prior}
    new = [r for r in requests if r["url"] not in old_urls]
    assert len(new) == 13 and len(requests) == 49
    args.private_dir.mkdir(parents=True, exist_ok=False)
    receipts = []
    total = 0
    for request in requests:
        if request["url"] not in old_urls:
            continue
        original = old_urls[request["url"]]
        data = (args.prior_dir / original["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == original["sha256"]
        envelope = json.loads(data)
        assert (
            isinstance(envelope.get("data"), list)
            and envelope.get("count") == len(envelope["data"]) < 500
        )
        shutil.copyfile(
            args.prior_dir / original["file"], args.private_dir / request["file"]
        )
        receipts.append(
            original
            | {"file": request["file"], "inherited_unchanged_identifier_request": True}
        )
        total += len(envelope["data"])
    (args.private_dir / "previous_acquisition_receipts.json").write_bytes(
        (json.dumps(prior, indent=2) + "\n").encode()
    )
    (args.private_dir / "requests.json").write_bytes(
        (json.dumps(receipts, indent=2) + "\n").encode()
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    for request in new:
        time.sleep(10)
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
            documented_publisher_identifier_binding=True,
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
        ), "Identifier-bound acquisition failure retained; stop without repeated retry"
        envelope = json.loads(data)
        rows = envelope.get("data")
        assert (
            isinstance(rows, list)
            and not envelope.get("error")
            and envelope.get("count") == len(rows) < 500
        ), "Unexpected/error/capped envelope retained; stop"
        total += len(rows)
        assert total < 10000
    assert len(receipts) == 49
    print("CAPTURE_COMPLETE", len(receipts), total, flush=True)


if __name__ == "__main__":
    main()
