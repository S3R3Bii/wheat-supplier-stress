"""Capture each fixed keyless preview request once, with bounded rate and record gates."""

import argparse
import hashlib
import json
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    args.private_dir.mkdir(parents=True, exist_ok=False)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    receipts = []
    previous_start = None
    total = 0
    for request in json.loads(
        (ROOT / "data/source_requests.json").read_text(encoding="utf-8")
    ):
        if previous_start is not None:
            time.sleep(max(0, 1.25 - (time.monotonic() - previous_start)))
        previous_start = time.monotonic()
        started = datetime.now(timezone.utc).isoformat()
        body = b""
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
                body = response.read()
        except HTTPError as exc:
            status = exc.code
            headers = dict(exc.headers.items())
            body = exc.read()
            error = str(exc)
        except Exception as exc:
            error = type(exc).__name__ + ":" + str(exc)
        (args.private_dir / request["file"]).write_bytes(body)
        item = dict(
            request,
            started_utc=started,
            completed_utc=datetime.now(timezone.utc).isoformat(),
            status=status,
            headers={
                k: v
                for k, v in headers.items()
                if k.lower()
                in {"content-type", "content-length", "etag", "last-modified", "date"}
            },
            bytes=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            protocol_commit=commit,
            python=platform.python_version(),
            error=error,
        )
        receipts.append(item)
        (args.private_dir / "requests.json").write_bytes(
            (json.dumps(receipts, indent=2) + "\n").encode()
        )
        print(
            json.dumps(
                {
                    k: item[k]
                    for k in ["kind", "year", "reporter", "status", "bytes", "error"]
                }
            ),
            flush=True,
        )
        assert (
            status == 200 and error is None
        ), "Source denial/error retained; stop without bypass, credential change or silent retry"
        envelope = json.loads(body)
        rows = envelope.get("data")
        assert isinstance(
            rows, list
        ), "Unexpected source envelope retained; bind schema before continuing"
        assert not envelope.get("error"), "Source error envelope retained; stop"
        assert (
            envelope.get("count") == len(rows) and len(rows) < 500
        ), "Potentially incomplete/capped response retained; stop"
        total += len(rows)
        assert total < 10000, "Total original record bound exceeded; stop"
        print("ENVELOPE_OK", len(rows), "cumulative_records", total, flush=True)
    print("CAPTURE_COMPLETE", len(receipts), total, flush=True)


if __name__ == "__main__":
    main()
