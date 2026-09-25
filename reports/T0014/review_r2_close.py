"""Close R2 review with exact provenance boundaries, no implementation changes."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit, unquote

ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/'reports/T0014'
OUT=TASK/'review-r2'
DOCS=('README.md','docs/implementation_status.md','docs/handoffs/T0014-proof-motif.md')
frozen=json.loads((OUT/'frozen-inputs.json').read_text())
for name,digest in frozen.items():
    if name not in DOCS:
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
links=0
for name in (*DOCS,'reports/T0014/review-r2/review.md'):
    p=ROOT/name
    text=p.read_text()
    assert text.endswith('\n') and not text.endswith('\n\n')
    assert all(s==s.rstrip() for s in text.splitlines()),name
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
        u=urlsplit(target.strip().strip('<>'))
        if not u.scheme and not u.netloc and u.path:
            assert (p.parent/unquote(u.path)).exists(),(p,target)
            links+=1
for p in TASK.glob('*r2*.py'):
    ast.parse(p.read_text())
ast.parse((TASK/'check_rework_r3.py').read_text())
assert '- 状态：`needs_changes`' in (ROOT/DOCS[2]).read_text()
assert 'needs_changes' in next(l for l in (ROOT/DOCS[1]).read_text().splitlines() if l.startswith('- T0014'))
checks={}
for run in ('review-r2-inventory','review-r2-focused','review-r2-guards'):
    r=json.loads((TASK/run/'record.json').read_text())
    assert r['exit_code']==0 and r['before']['source_sha256']==r['after']['source_sha256']
    for stream in ('stdout','stderr'):
        assert hashlib.sha256((TASK/run/(stream+'.txt')).read_bytes()).hexdigest()==r[stream+'_sha256']
    checks[run]=dict(exit_code=r['exit_code'],started_at=r['started_at_utc'],elapsed_s=r['elapsed_s'])
g=json.loads((TASK/'review-r2-guards/guards.json').read_text())
assert len(g['runs'])==5 and sum(not v['guard_valid'] for v in g['runs'])==4
inventory=json.loads((OUT/'inventory.json').read_text())
assert inventory['changed_frozen']==[] and inventory['pi_r2_recorded_runs']==[]
subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
result=dict(task_status='needs_changes',result='NEEDS_CHANGES',
    reviewed_product_sha256=inventory['product_sha256'],reviewed_test_sha256=inventory['test_sha256'],
    independent_focused=31, full_this_round='not_run', prior_independent_full=925,
    pi_claimed_full=916,pi_claimed_full_evidence='no original RUN found in submitted evidence; self-report only',
    prior_six_guards='raw artifacts reviewed; all six rejected, no recorder state/time chain',
    additional_mutants_survived=4, frozen_files_unchanged=2776, out_of_scope_artifacts_preserved=44,
    remaining=['R1 exact-source/submodule isolation self-check', 'R2 existing contract coverage', 'R3 execution/provenance/doc corrections'],
    code_unchanged=True,checks=checks,committed=False,pushed=False)
(OUT/'final-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(f'PASS: original code/tests/history preserved; 4 docs/{links} links; R2 needs_changes recorded; no commit/push')
