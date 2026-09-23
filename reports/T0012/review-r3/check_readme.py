"""R3 T0012: run the actual README K1 code block (no scope check, just the example)."""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
s = (ROOT / "README.md").read_text()
sec = s.split("单棵证明的规范键（T0012", 1)[1]
m = re.search(r"```python\n(.*?)```", sec, re.S)
assert m is not None, "no python block in README T0012 section"
code = m.group(1)
p = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                   capture_output=True, text=True, timeout=20)
print(p.stdout, end="")
if p.stderr:
    print(p.stderr, end="", file=sys.stderr)
assert p.returncode == 0, "README K1 example failed"
print("PASS: README T0012 K1 code block ran unchanged (exit 0)")
