"""Record planning baseline and accepted prerequisite hashes (no new product)."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import kmesh


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


accepted = json.loads((ROOT / 'reports/T0014/review-r4/final-audit.json').read_text())
for name in ('src/kmesh/logic/motif.py', 'tests/test_motif.py'):
    assert sha(ROOT / name) == accepted['accepted_files_sha256'][name], name
for task, name in (('T0012', 'proof_key'), ('T0006', 'proof'), ('T0003', 'types')):
    assert (ROOT / f'src/kmesh/logic/{name}.py').is_file(), task
assert not (ROOT / 'src/kmesh/logic/proof_subtree.py').exists()
assert not (ROOT / 'tests/test_proof_subtree.py').exists()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head == 'f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41'
tracked = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT, text=True).splitlines()
result = dict(head=head, python=sys.version, executable=str(Path(sys.executable).absolute()),
    kmesh_path=str(Path(kmesh.__file__).resolve()), packages={p: importlib.metadata.version(p) for p in ('kmesh','pytest')},
    tracked_changes_at_capture=tracked, new_product_and_test_absent=True,
    accepted_T0014_sha256={n: sha(ROOT / n) for n in ('src/kmesh/logic/motif.py','tests/test_motif.py')})
out = ROOT / 'reports/T0015/planning-baseline.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
