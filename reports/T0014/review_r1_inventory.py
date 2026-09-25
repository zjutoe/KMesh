"""Codex review: freeze submitted inputs and audit raw evidence, without edits."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0014'
OUT = TASK / 'review-r1'
OUT.mkdir(exist_ok=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


frozen = json.loads((TASK / 'planning-files.json').read_text())
changed = [p for p, digest in frozen.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
assert not changed, changed
paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT, text=True).split('\0')
mutable = {'README.md', 'docs/implementation_status.md', 'docs/handoffs/T0014-proof-motif.md',
           'src/kmesh/logic/motif.py', 'tests/test_motif.py', 'reports/T0014/planning-files.json'}
outside = [p for p in paths if p and p not in frozen and p not in mutable
           and not p.startswith(('reports/T0014/pi-', 'reports/T0014/review'))]
assert not outside, outside
inputs = {p: sha(ROOT / p) for p in paths if p and not p.startswith('reports/T0014/review')}
(OUT / 'frozen-inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
for name in ('src/kmesh/logic/motif.py', 'tests/test_motif.py', 'README.md',
             'docs/implementation_status.md', 'docs/handoffs/T0014-proof-motif.md',
             'docs/motif_identity_v1.md', 'reports/T0014/pi-r1/provenance.md'):
    dest = OUT / 'input-snapshot' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, dest)
runs = []
for p in sorted(TASK.glob('pi-*/record.json')):
    r = json.loads(p.read_text())
    assert r['status'] == 'finished', p
    for stream in ('stdout', 'stderr'):
        assert sha(p.parent / (stream + '.txt')) == r[stream + '_sha256'], p
    sources = r['before']['source_sha256']
    assert sources == r['after']['source_sha256'], p
    runs.append(dict(run=p.parent.name, argv=r['argv'], exit_code=r['exit_code'],
                     started_at=r['started_at_utc'], finished_at=r['finished_at_utc'], elapsed_s=r['elapsed_s'],
                     product_sha256=sources['src/kmesh/logic/motif.py'],
                     test_sha256=sources['tests/test_motif.py'],
                     stdout=(p.parent / 'stdout.txt').read_text(), stderr=(p.parent / 'stderr.txt').read_text()))
result = dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              frozen_planning_files_unchanged=len(frozen), scope='PASS', runs=runs,
              source_sha256={p:inputs[p] for p in ('src/kmesh/logic/motif.py','tests/test_motif.py')})
(OUT / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
