"""T0008: verify pi-r1-preflight before-hashes against planning-baseline."""

import json
import pathlib

base = pathlib.Path(__file__).resolve().parents[1]
rec = json.loads((base / "pi-r1-preflight" / "record.json").read_text())
plan = json.loads((base / "planning-baseline.json").read_text())
before = rec["before"]["source_sha256"]
plan_hashes = plan["source_sha256"]
bad = 0
for key, want in plan_hashes.items():
    actual = before.get(key)
    ok = (want is None and actual is None) or want == actual
    if not ok:
        bad += 1
    print(("OK       " if ok else "MISMATCH"), key)
print(f"preflight before sources: {len(before)}")
print(f"planning baseline entries: {len(plan_hashes)}")
if not (set(before) == set(plan_hashes)):
    bad += 1
if bad:
    raise SystemExit(f"preflight diverges from planning baseline: {bad} problem(s)")
print("preflight matches planning baseline")
