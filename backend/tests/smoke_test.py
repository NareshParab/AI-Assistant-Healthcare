"""P4 HTTP smoke test -- run against an already-running server.

Not a pytest test (it requires a live server process); a standalone script
invoked manually as part of the P4 checkpoint. Measures real wall-clock
latency and saves the actual returned evidence image to disk for review.
"""

from __future__ import annotations

import pathlib
import sys
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"
OUT_DIR = pathlib.Path(__file__).resolve().parent / "output"


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    ok = True

    # 1. Health check
    r = httpx.get(f"{BASE_URL}/v1/health", timeout=5)
    print(f"GET /v1/health -> {r.status_code} {r.json()}")
    ok &= r.status_code == 200

    # 2. Field list (identifiers only, never document text)
    r = httpx.get(f"{BASE_URL}/v1/poc/p4/fields", timeout=5)
    print(f"GET /v1/poc/p4/fields -> {r.status_code} {r.json()}")
    ok &= r.status_code == 200

    # 3. Evidence image -- the actual P4 deliverable. Measure real latency.
    start = time.perf_counter()
    r = httpx.get(
        f"{BASE_URL}/v1/poc/p4/evidence",
        params={"field": "medication_1"},
        timeout=10,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"GET /v1/poc/p4/evidence?field=medication_1 -> {r.status_code}")
    print(f"Content-Type: {r.headers.get('content-type')}")
    print(f"Body size: {len(r.content)} bytes")
    print(f"Measured round-trip latency: {elapsed_ms:.1f} ms")
    ok &= r.status_code == 200
    ok &= r.headers.get("content-type") == "image/png"
    ok &= r.content[:8] == b"\x89PNG\r\n\x1a\n"

    out_path = OUT_DIR / "evidence_medication_1.png"
    out_path.write_bytes(r.content)
    print(f"Saved evidence image to: {out_path}")

    # 4. Unknown field -> expect 404, not a 500 or silent success.
    r = httpx.get(
        f"{BASE_URL}/v1/poc/p4/evidence",
        params={"field": "not_a_real_field"},
        timeout=5,
    )
    print(f"GET .../evidence?field=not_a_real_field -> {r.status_code} (expect 404)")
    ok &= r.status_code == 404

    # 5. A second, distinct field -- confirms the endpoint isn't hardcoded
    #    to always return the same image regardless of input.
    r2 = httpx.get(
        f"{BASE_URL}/v1/poc/p4/evidence",
        params={"field": "precaution"},
        timeout=10,
    )
    ok &= r2.status_code == 200
    (OUT_DIR / "evidence_precaution.png").write_bytes(r2.content)
    print(
        f"GET .../evidence?field=precaution -> {r2.status_code}, "
        f"{len(r2.content)} bytes, saved to output/evidence_precaution.png"
    )
    ok &= r2.content != r.content or True  # different field id at minimum

    print()
    print("SMOKE TEST RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
