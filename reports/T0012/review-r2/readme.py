"""Run the submitted README example without altering it."""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/sys.argv[1]
text=(ROOT/'README.md').read_text().split('单棵证明的规范键（T0012',1)[1]
code=re.search(r'```python\n(.*?)```',text,re.S).group(1)
(OUT/'example.py').write_text(code)
p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,timeout=10)
(OUT/'example.stdout').write_bytes(p.stdout)
(OUT/'example.stderr').write_bytes(p.stderr)
(OUT/'result.json').write_text(json.dumps(dict(exit_code=p.returncode),indent=2)+'\n')
assert p.returncode==0, p.stderr.decode()
print('PASS: submitted K1 README block executed unchanged')
