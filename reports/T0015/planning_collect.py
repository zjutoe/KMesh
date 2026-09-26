"""Collect accepted prerequisite tests once; do not rerun their full suite."""
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
files = runpy.run_path(str(ROOT/'reports/T0015/run_checks.py'))['TESTS'][1:]
assert len(files) == 14
r = subprocess.run([sys.executable,'-m','pytest','--collect-only','-q',*files,
    '--basetemp','reports/T0015/planning-collect/pytest-tmp'],cwd=ROOT,capture_output=True,text=True)
print(r.stdout,end='')
print(r.stderr,end='',file=sys.stderr)
assert r.returncode == 0
assert '917 tests collected' in r.stdout
