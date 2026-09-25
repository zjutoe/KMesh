"""Freeze and audit the T0014 R3 submission; do not modify Pi evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0014'
OUT = TASK / 'review-r3'
OUT.mkdir(exist_ok=False)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


baseline = json.loads((TASK / 'review-r2/rework-baseline.json').read_text())
changed = [p for p, h in baseline['files'].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
paths = set(subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT, text=True).split('\0')) - {''}
inputs = {p: sha(ROOT / p) for p in sorted(paths) if not p.startswith(('reports/T0014/review-r3', 'reports/T0014/review_r3'))}
(OUT / 'frozen-inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
for p in ('tests/test_motif.py', 'src/kmesh/logic/motif.py', 'README.md', 'docs/implementation_status.md', 'docs/handoffs/T0014-proof-motif.md'):
    dest = OUT / 'input-snapshot' / p
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / p, dest)
mutable = {'README.md', 'docs/implementation_status.md', 'docs/handoffs/T0014-proof-motif.md', 'tests/test_motif.py', 'reports/T0014/review-r2/rework-baseline.json'}
outside = [p for p in sorted(paths) if p not in baseline['files'] and p not in mutable and not p.startswith(('reports/T0014/pi-r3', 'reports/T0014/review-r3', 'reports/T0014/review_r3'))]
runs = []
for p in sorted(TASK.glob('pi-r3*/record.json')):
    r = json.loads(p.read_text())
    assert r['status'] == 'finished', p
    for stream in ('stdout', 'stderr'):
        assert sha(p.parent / (stream + '.txt')) == r[stream + '_sha256'], p
    assert r['before']['source_sha256'] == r['after']['source_sha256'], p
    runs.append(dict(run=p.parent.name, exit_code=r['exit_code'], started_at=r['started_at_utc'],
        finished_at=r['finished_at_utc'], elapsed_s=r['elapsed_s'], argv=r['argv'],
        product_sha256=r['before']['source_sha256']['src/kmesh/logic/motif.py'],
        test_sha256=r['before']['source_sha256']['tests/test_motif.py'],
        stdout_tail=(p.parent / 'stdout.txt').read_text().splitlines()[-5:],
        stderr=(p.parent / 'stderr.txt').read_text()))
runs.sort(key=lambda r: r['started_at'])
result = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    frozen_files=len(baseline['files']), changed_frozen=changed, outside_scope=outside,
    product_sha256=sha(ROOT / 'src/kmesh/logic/motif.py'), test_sha256=sha(ROOT / 'tests/test_motif.py'), runs=runs)
(OUT / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n')
assert not changed and not outside, result
print(f"Frozen files unchanged: {len(baseline['files'])}; scope clean; {len(runs)} recorded R3 RUNs")
print('Product:', result['product_sha256'])
print('Tests:', result['test_sha256'])
for r in runs:
    print(r['run'], r['exit_code'], r['started_at'], r['test_sha256'][:12], r['stdout_tail'][-1:] if r['stdout_tail'] else [], r['stderr'][-250:])
