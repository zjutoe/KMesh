"""Freeze the T0015 R1 submission and inspect immutable execution evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
OUT = TASK / 'review-r1'
OUT.mkdir(exist_ok=False)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


baseline = json.loads((TASK / 'planning-files.json').read_text())
changed = [p for p, h in baseline.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
paths = set(subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,text=True).split('\0')) - {''}
mutable = {'README.md','docs/implementation_status.md','docs/handoffs/T0015-proof-subtree.md',
           'src/kmesh/logic/proof_subtree.py','tests/test_proof_subtree.py','reports/T0015/planning-files.json'}
outside = [p for p in sorted(paths) if p not in baseline and p not in mutable and not p.startswith(('reports/T0015/pi-', 'reports/T0015/review-r1', 'reports/T0015/review_r1'))]
inputs = {p: sha(ROOT/p) for p in sorted(paths) if not p.startswith(('reports/T0015/review-r1','reports/T0015/review_r1'))}
(OUT/'frozen-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
for name in sorted(mutable - {'reports/T0015/planning-files.json'}):
    dest = OUT/'input-snapshot'/name
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/name,dest)
runs = []
for p in sorted(TASK.glob('pi-*/record.json')):
    r = json.loads(p.read_text())
    assert r['status'] == 'finished', p
    for stream in ('stdout','stderr'):
        assert sha(p.parent/(stream+'.txt')) == r[stream+'_sha256'], p
    assert r['before']['source_sha256'] == r['after']['source_sha256'], p
    runs.append(dict(run=p.parent.name, exit_code=r['exit_code'], started_at=r['started_at_utc'],
        elapsed_s=r['elapsed_s'], argv=r['argv'], source_sha256=r['before']['source_sha256'],
        stdout_tail=(p.parent/'stdout.txt').read_text().splitlines()[-8:], stderr=(p.parent/'stderr.txt').read_text()))
runs.sort(key=lambda r: r['started_at'])
orphan = [dict(path=str(p.relative_to(ROOT)), files=sorted(x.name for x in p.iterdir()))
          for p in sorted(TASK.glob('pi-*')) if p.is_dir() and not (p/'record.json').exists()]
result = dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
    frozen_files=len(baseline), changed_frozen=changed, outside_scope=outside,
    product_sha256=sha(ROOT/'src/kmesh/logic/proof_subtree.py'), test_sha256=sha(ROOT/'tests/test_proof_subtree.py'),
    runs=runs, directories_without_record=orphan)
(OUT/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
assert not changed and not outside
print(f'Frozen {len(baseline)} files unchanged; scope clean; {len(runs)} recorded Pi RUNs')
print('Product:',result['product_sha256'])
print('Tests:',result['test_sha256'])
for r in runs:
    print(r['run'],r['exit_code'],r['started_at'],str(r['source_sha256']['src/kmesh/logic/proof_subtree.py'])[:12],r['stdout_tail'][-2:])
print('Directories without record:',orphan)
