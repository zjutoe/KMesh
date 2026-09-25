"""Close Codex review evidence, preserving product/tests and all Pi history."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0014'
REVIEW = TASK / 'review-r1'
DOCS = ('README.md', 'docs/implementation_status.md', 'docs/handoffs/T0014-proof-motif.md')
frozen = json.loads((REVIEW / 'frozen-inputs.json').read_text())
for name, digest in frozen.items():
    if name not in DOCS:
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
links = 0
for name in (*DOCS, 'reports/T0014/review-r1/review.md'):
    p = ROOT / name
    text = p.read_text()
    assert text.endswith('\n') and not text.endswith('\n\n')
    assert all(line == line.rstrip() for line in text.splitlines()), name
    for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        u = urlsplit(link.strip().strip('<>'))
        if not u.scheme and not u.netloc and u.path:
            assert (p.parent / unquote(u.path)).exists(), (p, link)
            links += 1
for p in TASK.glob('*r1*.py'):
    ast.parse(p.read_text(), filename=str(p))
ast.parse((TASK / 'check_rework_r2.py').read_text())
assert '- 状态：`needs_changes`' in (ROOT / DOCS[2]).read_text()
assert 'needs_changes' in next(s for s in (ROOT / DOCS[1]).read_text().splitlines() if s.startswith('- T0014'))
assert 'needs_changes' in (ROOT / 'README.md').read_text().split('## 证明结构签名（T0014', 1)[1]
checks = ('review-r1-inventory', 'review-r1-full', 'review-r1-guards', 'review-r1-probe', 'review-r1-isolation')
records = {}
for run in checks:
    r = json.loads((TASK / run / 'record.json').read_text())
    assert r['exit_code'] == 0 and r['before']['source_sha256'] == r['after']['source_sha256'], run
    for stream in ('stdout', 'stderr'):
        assert hashlib.sha256((TASK / run / (stream + '.txt')).read_bytes()).hexdigest() == r[stream + '_sha256']
    records[run] = dict(exit_code=r['exit_code'], started_at=r['started_at_utc'], elapsed_s=r['elapsed_s'])
guards = json.loads((TASK / 'review-r1-guards/guards.json').read_text())
assert len(guards['runs']) == 7
assert sum(not r['guard_valid'] for r in guards['runs']) == 5
subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
result = dict(task_status='needs_changes', result='NEEDS_CHANGES',
    reviewed_source_sha256={name: frozen[name] for name in ('src/kmesh/logic/motif.py','tests/test_motif.py')},
    independent_full=925, submitted_focused=40, mutants_rejected=1, mutants_survived=5,
    product_findings='No functional defect observed in bounded independent probes; not exhaustive correctness',
    rework=['R1 hard isolation', 'R2 identity and purity', 'R3 delegation diagnostics and complete long chain', 'R4 record/README corrections'],
    historical_inputs_unchanged=len(frozen)-len(DOCS), checks=records,
    unchanged_product_and_tests=True, committed=False, pushed=False)
(REVIEW / 'final-audit.json').write_text(json.dumps(result, indent=2)+'\n')
print(f'PASS: review evidence closed; original source/tests/history unchanged; 4 docs/{links} links; needs_changes; no commit/push')
