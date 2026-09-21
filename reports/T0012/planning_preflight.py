"""Capture the accepted, uncommitted T0011 base before T0012 planning edits."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
TASK = ROOT / 'reports/T0012'


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    previous = json.loads((ROOT / 'reports/T0011/review-r2/final-audit.json').read_text())
    assert previous['task_status'] == 'accepted'
    for path, digest in previous['accepted_files'].items():
        assert sha(path) == digest, path
    for path, digest in previous['history_sha256'].items():
        assert sha(path) == digest, path
    old = json.loads((ROOT / 'reports/T0011/planning-baseline.json').read_text())
    sources = {p: sha(p) for p in old['source_sha256'] if p.startswith(('src/', 'tests/')) or p == 'pyproject.toml'}
    for p, h in old['source_sha256'].items():
        if h is not None and p in sources:
            assert sources[p] == h, p
    for p in ('src/kmesh/logic/proof_key.py', 'tests/test_proof_key.py'):
        assert not (ROOT / p).exists()
        sources[p] = None
    files = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], text=True).split('\0')
    repo = {p: sha(p) for p in files if p and not p.startswith('reports/T0012/')}
    import kmesh
    result = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  branch=subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip(),
                  status=subprocess.check_output(['git', 'status', '--short'], text=True),
                  source_sha256=sources, initial_repository_sha256=repo,
                  python=sys.version, executable=str(Path(sys.executable).absolute()),
                  kmesh_path=str(Path(kmesh.__file__).resolve()),
                  packages={p: importlib.metadata.version(p) for p in ('kmesh', 'pytest')},
                  prior_test_inventory=795, prior_full_executed=771,
                  inventory_note='732 unchanged old tests plus accepted T0011 63 focused; 795 is inventory, not a full run result',
                  product_implemented=False)
    assert result['head'] == previous['head']
    assert sys.version_info[:3] == (3, 13, 9)
    assert result['kmesh_path'] == str(ROOT / 'src/kmesh/__init__.py')
    target = TASK / 'planning-baseline.json'
    assert not target.exists()
    target.write_text(json.dumps(result, indent=2) + '\n')
    print('PASS: accepted T0011 hashes/history, environment, new files absent; baseline captured')
    print(json.dumps({k: result[k] for k in ('head', 'branch', 'packages', 'prior_test_inventory', 'prior_full_executed')}, indent=2))


if __name__ == '__main__':
    main()
