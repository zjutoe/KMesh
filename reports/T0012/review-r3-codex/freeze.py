"""Freeze R3 submission; Pi-created review-r3 files are retained as submitted inputs."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / 'reports/T0012'
OUT = TASK / 'review-r3-freeze'
MUTABLE = ('tests/test_proof_key.py', 'README.md', 'docs/implementation_status.md', 'docs/handoffs/T0012-proof-key.md')
PRODUCT = 'src/kmesh/logic/proof_key.py'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    names = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    manifest = {n:sha(ROOT/n) for n in sorted(set(names)) if n and not n.startswith('reports/T0012/review-r3-')}
    (OUT/'input-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    previous = json.loads((TASK/'review-r2-freeze/input-manifest.json').read_text())
    audit = json.loads((TASK/'review-r2/final-audit.json').read_text())
    protected = {n:d for n,d in previous.items() if n not in MUTABLE} | audit['review_material_sha256']
    changed = [n for n,d in protected.items() if manifest.get(n) != d]
    for n in (PRODUCT,*MUTABLE):
        dest=OUT/'input-snapshot'/n
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((ROOT/n).read_bytes())
    rows=[]
    dirs=[]
    for directory in sorted(TASK.glob('pi-r3*')):
        if not directory.is_dir():
            continue
        dirs.append(dict(name=directory.name, recorded=(directory/'record.json').exists()))
        if not (directory/'record.json').exists():
            continue
        record=json.loads((directory/'record.json').read_text())
        for stream in ('stdout','stderr'):
            assert sha(directory/(stream+'.txt'))==record[stream+'_sha256']
        rows.append({k:record[k] for k in ('argv','exit_code','started_at_utc','finished_at_utc','elapsed_s')} | dict(run=directory.name,
            source_before=record['before']['source_sha256'],source_after=record['after']['source_sha256'],
            stdout=(directory/'stdout.txt').read_text(),stderr=(directory/'stderr.txt').read_text()))
    rows.sort(key=lambda x:x['started_at_utc'])
    old=ast.parse((TASK/'review-r2-freeze/input-snapshot/tests/test_proof_key.py').read_text())
    new=ast.parse((ROOT/MUTABLE[0]).read_text())
    classes=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.ClassDef)}
    oc,nc=classes(old),classes(new)
    unchanged={n:oc[n]==nc[n] for n in ('TestAHandComputed','TestBTransformations','TestCOracleAndEnumeration')}
    result=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protected_count=len(protected),protected_differences=changed,
        input_sha256={n:manifest[n] for n in (PRODUCT,*MUTABLE)},
        abc_ast_unchanged=unchanged,pi_r3_directories=dirs,pi_r3_records=rows)
    (OUT/'input-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    assert not changed, changed
    print('PASS: protected files',len(protected),'unchanged; input files',len(manifest))
    print('A/B/C unchanged:',unchanged)
    for r in rows:
        print(r['run'],r['exit_code'],r['started_at_utc'],r['elapsed_s'])
    print('Without record.json:',[d['name'] for d in dirs if not d['recorded']])

if __name__=='__main__':
    main()
