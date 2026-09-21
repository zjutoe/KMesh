"""Validate planning docs and command construction without creating product code."""
import ast
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "reports/T0010"
HANDOFF = "docs/handoffs/T0010-minimum-depth.md"


def main():
    baseline = json.loads((TASK / "planning-baseline.json").read_text())
    for name, digest in baseline["source_sha256"].items():
        path = ROOT / name
        if digest is None:
            assert not path.exists(), name
        else:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
    changed = set()
    for args in (("diff", "HEAD", "--name-only", "-z"),
                 ("ls-files", "--others", "--exclude-standard", "-z")):
        changed.update(p for p in subprocess.check_output(["git", *args], cwd=ROOT, text=True).split("\0") if p)
    allowed = {HANDOFF, "docs/decisions.md", "docs/implementation_status.md",
               "docs/handoffs/T0009-proof-enumeration.md"}
    assert all(p in allowed or p.startswith("reports/T0010/") for p in changed), changed
    links = 0
    docs = [ROOT / p for p in allowed] + [TASK / "planning-review.md"]
    for path in docs:
        content = path.read_text()
        assert content.endswith("\n") and all(s == s.rstrip() for s in content.splitlines()), path
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            parsed = urlsplit(link.strip().strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            assert (path.parent / unquote(parsed.path)).exists(), (path, link)
            links += 1
    assert "- 状态：`ready`" in (ROOT / HANDOFF).read_text()
    assert "`ready`" in next(s for s in (ROOT / "docs/implementation_status.md").read_text().splitlines()
                             if s.startswith("- T0010"))
    for path in TASK.glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    # Exercise command assembly only; no test process/product implementation.
    driver = runpy.run_path(str(TASK / "run_checks.py"))
    for phase in ("preflight", "focused", "full", "docs"):
        run = f"pi-check-{phase}"
        with patch.object(sys, "argv", ["run_checks.py", run, phase]), \
             patch("subprocess.call", return_value=0) as invoke:
            assert driver["main"]() == 0
        argv = invoke.call_args.args[0]
        assert argv[:4] == [".venv/bin/python", "reports/T0010/record_check.py", run, "--"]
        if phase in ("focused", "full"):
            assert argv[-2:] == ["--basetemp", f"reports/T0010/{run}/pytest-tmp"]
            expected = driver["TESTS"][:1] if phase == "focused" else driver["TESTS"]
            assert argv[8:-2] == expected
        else:
            assert argv[4:] == [".venv/bin/python", "reports/T0010/check_delivery.py", phase]
    ignored = subprocess.check_output(
        ["git", "check-ignore", "reports/T0010/pi-check-full/pytest-tmp/example"], cwd=ROOT, text=True)
    assert ignored.strip() == "reports/T0010/pi-check-full/pytest-tmp/example"
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    print(f"PASS: ready, planning scope, frozen baseline, {len(docs)} docs/{links} local links, helper syntax/argv, scratch ignore")
    print("Product implementation and new tests: not_run; old full regression not repeated")


if __name__ == "__main__":
    main()
