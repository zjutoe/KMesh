"""One-time Codex planning inventory, not product validation."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

import kmesh

ROOT = Path(__file__).resolve().parents[2]
HEAD = '0e407ed9b3f270143f8587a301fa34fabf465b6b'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


assert git('rev-parse', 'HEAD') == HEAD
assert git('branch', '--show-current') == 'master'
assert git('diff', '--name-only', 'HEAD') == ''
for path, digest in {
    'src/kmesh/logic/proof_count.py': 'ac710fd17731bde66e90e8d7737a5eac59486b65454f6bd0fbe9d1ca270eec6d',
    'tests/test_proof_count.py': '527808551efb6f3c9a8ae1d72fd31e93dcea20814e23fe7162330a8e15869fff',
    'src/kmesh/logic/proof_key.py': '92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1',
}.items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
for path in ('src/kmesh/logic/motif.py', 'tests/test_motif.py'):
    assert not (ROOT / path).exists(), path
files = git('ls-files', '-z').split('\0')
result = dict(head=HEAD, branch='master', python=sys.version,
              executable=str(Path(sys.executable).absolute()),
              kmesh_path=str(Path(kmesh.__file__).resolve()),
              packages={name: importlib.metadata.version(name) for name in ('kmesh', 'pytest', 'PyYAML')},
              tracked_sha256={path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in files if path})
with (ROOT / 'reports/T0014/planning-baseline.json').open('x') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(f'PASS: clean merged baseline; accepted T0012/T0013 hashes; {len(result["tracked_sha256"])} tracked files; new files absent')
print(json.dumps({k: v for k, v in result.items() if k != 'tracked_sha256'}, indent=2))
