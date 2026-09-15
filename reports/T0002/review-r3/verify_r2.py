"""Verify the four original round-2 YAML counterexamples without modifying them."""
import json
from pathlib import Path
import subprocess
import sys
import time

from kmesh.config import ConfigError, load_model_config

root = Path.cwd()
run = root / "reports/T0002/review-r3/r2-counterexamples"
run.mkdir(exist_ok=False)
paths = [
    "reports/T0002/review-r2/regressions/empty-int-tag.yaml",
    "reports/T0002/review-r2/regressions/empty-float-tag.yaml",
    "reports/T0002/review-r2/regressions/invalid-timestamp-tag.yaml",
    "reports/T0002/review-r2/yaml-float/sexagesimal.yaml",
]
results = []
for relative in paths:
    path = root / relative
    try:
        load_model_config(path)
    except Exception as exc:
        api = dict(exception=type(exc).__name__, message=str(exc),
                   controlled=isinstance(exc, ConfigError))
    else:
        api = dict(exception=None, message="unexpected success", controlled=False)
    argv = [sys.executable, "-m", "kmesh.cli", "config", "validate-model", "--config", str(path)]
    start = time.monotonic()
    p = subprocess.run(argv, cwd=root, capture_output=True, timeout=60)
    (run / f"{path.stem}.stdout").write_bytes(p.stdout)
    (run / f"{path.stem}.stderr").write_bytes(p.stderr)
    passed = (api["controlled"] and str(path) in api["message"]
              and "invalid YAML" in api["message"] and p.returncode == 1
              and not p.stdout and str(path).encode() in p.stderr
              and b"invalid YAML" in p.stderr and b"Traceback" not in p.stderr)
    results.append(dict(path=relative, api=api, argv=argv, exit_code=p.returncode,
                        elapsed_s=round(time.monotonic()-start, 3), passed=passed))
    (run / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(path.stem, "PASS" if passed else "FAIL")
summary = dict(result="PASS" if all(r["passed"] for r in results) else "FAIL", cases=len(results))
(run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
raise SystemExit(0 if summary["result"] == "PASS" else 1)
