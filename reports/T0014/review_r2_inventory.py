"""Freeze T0014 R2 submission; record evidence gaps without repairing history."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0014'
OUT = TASK / 'review-r2'
OUT.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = json.loads((TASK / 'review-r1/rework-baseline.json').read_text())
changed = [p for p, h in baseline['files'].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
paths = set(subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,text=True).split('\0'))-{''}
input_files = {p: sha(ROOT/p) for p in sorted(paths) if not p.startswith(('reports/T0014/review-r2', 'reports/T0014/review_r2'))}
(OUT/'frozen-inputs.json').write_text(json.dumps(input_files,indent=2)+'\n')
for p in ('tests/test_motif.py','src/kmesh/logic/motif.py','README.md','docs/implementation_status.md','docs/handoffs/T0014-proof-motif.md'):
    d=OUT/'input-snapshot'/p
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/p,d)
mutable={'README.md','docs/implementation_status.md','docs/handoffs/T0014-proof-motif.md','tests/test_motif.py','reports/T0014/review-r1/rework-baseline.json'}
outside=[p for p in sorted(paths) if p not in baseline['files'] and p not in mutable and not p.startswith(('reports/T0014/pi-r2','reports/T0014/review-r2','reports/T0014/review_r2'))]
new_runs=[]
for p in sorted(TASK.glob('pi-r2*/record.json')):
    r=json.loads(p.read_text())
    new_runs.append({'path':str(p.relative_to(ROOT)), 'record':r})
guards=[]
for folder in ('guard-r2','guard-r3'):
    p=TASK/folder/'guards.json'
    if not p.exists():
        continue
    r=json.loads(p.read_text())
    for row in r['runs']:
        assert sha(p.parent/(row['name']+'.source.py'))==row['source_sha256']
    guards.append(dict(folder=folder, recorder_present=(p.parent/'record.json').exists(),
        test_sha256=r['test_sha256'], all_guards_valid=r['all_guards_valid'],
        outcomes=[dict(name=v['name'],exit_code=v['exit_code'], stdout_tail=(p.parent/(v['name']+'.stdout.txt')).read_text().splitlines()[-6:]) for v in r['runs']]))
result=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    frozen_file_count=len(baseline['files']), changed_frozen=changed, out_of_R2_scope=outside,
    product_sha256=sha(ROOT/'src/kmesh/logic/motif.py'), test_sha256=sha(ROOT/'tests/test_motif.py'),
    pi_r2_recorded_runs=new_runs, pi_r2_provenance=[str(p.relative_to(ROOT)) for p in TASK.glob('pi-r2*/provenance.md')],
    pi_r2_dirs=[dict(name=p.name, files=[x.name for x in p.iterdir()]) for p in TASK.glob('pi-r2*')], guard_artifacts=guards)
(OUT/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
