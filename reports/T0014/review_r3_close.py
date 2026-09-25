"""Close the T0014 R3 review and freeze its evidence without changing tests."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0014'
OUT = TASK / 'review-r3'
DOCS = ('README.md', 'docs/implementation_status.md', 'docs/handoffs/T0014-proof-motif.md')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


frozen = json.loads((OUT / 'frozen-inputs.json').read_text())
for name, digest in frozen.items():
    if name not in DOCS:
        assert sha(ROOT / name) == digest, name
links = 0
for name in (*DOCS, 'reports/T0014/review-r3/review.md'):
    p = ROOT / name
    text = p.read_text()
    assert text.endswith('\n') and not text.endswith('\n\n'), name
    assert all(s == s.rstrip() for s in text.splitlines()), name
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        u = urlsplit(target.strip().strip('<>'))
        if not u.scheme and not u.netloc and u.path:
            assert (p.parent / unquote(u.path)).exists(), (p, target)
            links += 1
for p in TASK.glob('review_r3*.py'):
    ast.parse(p.read_text())
ast.parse((TASK / 'check_rework_r4.py').read_text())
assert '- 状态：`needs_changes`' in (ROOT / DOCS[2]).read_text()
assert 'needs_changes' in next(l for l in (ROOT / DOCS[1]).read_text().splitlines() if l.startswith('- T0014'))
checks = {}
for run in ('review-r3-inventory', 'review-r3-focused', 'review-r3-guards', 'review-r3-probe'):
    r = json.loads((TASK / run / 'record.json').read_text())
    assert r['exit_code'] == 0 and r['before']['source_sha256'] == r['after']['source_sha256']
    for stream in ('stdout', 'stderr'):
        assert sha(TASK / run / (stream + '.txt')) == r[stream + '_sha256']
    checks[run] = dict(exit_code=r['exit_code'], started_at=r['started_at_utc'], elapsed_s=r['elapsed_s'])
g = json.loads((TASK / 'review-r3-guards/guards.json').read_text())
escaped = [r['name'] for r in g['runs'] if not r['guard_valid']]
assert escaped == ['format_unvalidated_integer', 'logic_error_loses_to_invalid_O', 'header_tuple_subclass']
inventory = json.loads((OUT / 'inventory.json').read_text())
assert inventory['changed_frozen'] == [] and inventory['outside_scope'] == []
assert len(inventory['runs']) == 9
for folder in ('pi-r3-guards', 'pi-r3-extra-guards'):
    guard = json.loads((TASK / folder / 'guards.json').read_text())
    assert guard['all_guards_valid'] and guard['test_sha256'] == inventory['test_sha256']
    for row in guard['runs']:
        p = TASK / folder / (row['name'] + '.source.py')
        if 'source_sha256' in row:
            assert sha(p) == row['source_sha256']
        output = (TASK / folder / (row['name'] + '.stdout.txt')).read_text()
        assert ('32 passed' in output if row['name'] == 'submitted' else 'FAILED ' in output)
full = json.loads((TASK / 'pi-r3-full/record.json').read_text())
assert full['exit_code'] == 0 and full['before']['source_sha256']['tests/test_motif.py'] == inventory['test_sha256']
assert (TASK / 'pi-r3-full/stdout.txt').read_text().strip().endswith('917 passed in 16.13s')
assert (TASK / 'pi-r3-full/stderr.txt').read_bytes() == b''
probe = json.loads((TASK / 'review-r3-probe/result.json').read_text())
assert all(v == 'PASS' for v in probe['checks'].values())
subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
result = dict(task_status='needs_changes', result='NEEDS_CHANGES',
    reviewed_product_sha256=inventory['product_sha256'], reviewed_test_sha256=inventory['test_sha256'],
    independent_focused=32, independent_full_this_round='not_run', prior_independent_full=925,
    verified_pi_full=917, pi_full_evidence='argv, output hashes and before/after source hashes verified',
    original_mutants_rejected=10, additional_mutants_survived=escaped,
    additional_mutant_already_rejected='underbudget_distinct_twins',
    product_probe=probe['checks'], frozen_files_unchanged=inventory['frozen_files'],
    recorded_pi_r3_runs=9, code_and_tests_unchanged_by_reviewer=True,
    remaining=['R1 integer conversion limit test', 'R2 exception priority, native tuple types and M6 AB budget test',
               'R3 execution/provenance corrections'],
    checks=checks, committed=False, pushed=False)
(OUT / 'final-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(f'PASS: product/tests/history unchanged; 4 docs/{links} links; R3 needs_changes recorded; no commit/push')
