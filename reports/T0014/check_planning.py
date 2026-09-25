"""Static planning checks; never claims the future motif product is validated."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0014'
DOCS = ('docs/motif_identity_v1.md', 'docs/handoffs/T0014-proof-motif.md',
        'docs/proof_identity_v1.md', 'docs/decisions.md', 'docs/implementation_status.md',
        'reports/T0014/planning-review.md')
ALLOWED_OLD = {'docs/proof_identity_v1.md', 'docs/decisions.md', 'docs/implementation_status.md'}
baseline = json.loads((TASK / 'planning-baseline.json').read_text())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head == baseline['head']
for path, digest in baseline['tracked_sha256'].items():
    if path not in ALLOWED_OLD:
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
for path in ('src/kmesh/logic/motif.py', 'tests/test_motif.py'):
    assert not (ROOT / path).exists(), path
links = 0
for name in DOCS:
    path = ROOT / name
    text = path.read_text()
    assert text.endswith('\n') and not text.endswith('\n\n')
    assert all(line == line.rstrip() for line in text.splitlines()), name
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        url = urlsplit(target.strip().strip('<>'))
        if not url.scheme and not url.netloc and url.path:
            assert (path.parent / unquote(url.path)).exists(), (name, target)
            links += 1
for path in TASK.glob('*.py'):
    text = path.read_text()
    ast.parse(text, filename=str(path))
    assert text.endswith('\n') and all(line == line.rstrip() for line in text.splitlines()), path
handoff = (ROOT / DOCS[1]).read_text()
assert '- 状态：`ready`' in handoff
assert all(name in handoff for name in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7'))
status = (ROOT / 'docs/implementation_status.md').read_text()
assert '`ready`' in next(line for line in status.splitlines() if line.startswith('- T0014'))
assert '`ready`' in next(line for line in status.splitlines() if line.startswith('| 单棵证明跨世界 motif 键 |'))
subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
print(f'PASS: {len(baseline["tracked_sha256"])} base files audited, accepted code/history unchanged; {len(DOCS)} docs/{links} links; helper AST/hygiene; ready; motif not implemented')
