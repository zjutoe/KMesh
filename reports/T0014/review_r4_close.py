"""Record final acceptance after bounded independent R4 verification."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0014'
OUT = TASK / 'review-r4'
DOCS = ('README.md', 'docs/implementation_status.md', 'docs/handoffs/T0014-proof-motif.md')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for name, digest in json.loads((OUT / 'frozen-inputs.json').read_text()).items():
    if name not in DOCS:
        assert sha(ROOT / name) == digest, name
links = 0
for name in (*DOCS, 'reports/T0014/review-r4/review.md'):
    p = ROOT / name
    text = p.read_text()
    assert text.endswith('\n') and not text.endswith('\n\n'), name
    assert all(line == line.rstrip() for line in text.splitlines()), name
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        u = urlsplit(target.strip().strip('<>'))
        if not u.scheme and not u.netloc and u.path:
            assert (p.parent / unquote(u.path)).exists(), (p, target)
            links += 1
handoff = (ROOT / DOCS[2]).read_text()
assert '- 状态：`accepted`' in handoff and handoff.count('- [x] **A') == 7
status = (ROOT / DOCS[1]).read_text().splitlines()
assert '`accepted`' in next(l for l in status if l.startswith('- T0014'))
assert '`accepted`' in next(l for l in status if l.startswith('| 单棵证明跨世界 motif 键 |'))
readme = (ROOT / DOCS[0]).read_text().split('## 证明结构签名（T0014', 1)[1]
assert 'awaiting_review' not in readme and '**`accepted`**' in readme
driver = ast.parse((TASK / 'run_checks.py').read_text())
tests = next(ast.literal_eval(n.value) for n in driver.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'TESTS' for t in n.targets))
shell = re.search(r'```bash\n(.*?)```', readme, re.S).group(1)
assert re.findall(r'tests/test_\w+\.py', shell) == tests
# Example unchanged from the independently reviewed input and successful Pi docs2.
previous = (OUT / 'input-snapshot/README.md').read_text().split('## 证明结构签名（T0014', 1)[1]
assert re.search(r'```python\n(.*?)```', readme, re.S).group(1) == re.search(r'```python\n(.*?)```', previous, re.S).group(1)
checks = {}
for run in ('review-r4-inventory', 'review-r4-focused', 'review-r4-guards'):
    r = json.loads((TASK / run / 'record.json').read_text())
    assert r['exit_code'] == 0 and r['before']['source_sha256'] == r['after']['source_sha256']
    for stream in ('stdout', 'stderr'):
        assert sha(TASK / run / (stream + '.txt')) == r[stream + '_sha256']
    checks[run] = dict(exit_code=r['exit_code'], started_at=r['started_at_utc'], elapsed_s=r['elapsed_s'])
g = json.loads((TASK / 'review-r4-guards/guards.json').read_text())
assert g['all_guards_valid'] and len(g['runs']) == 5
targets = {'format_unvalidated_integer': 'test_all_budget_errors',
           'logic_error_loses_to_invalid_O': 'test_sentinel_identity',
           'underbudget_distinct_twins': 'test_budget_boundaries',
           'header_tuple_subclass': 'test_key_container_types'}
for row in g['runs']:
    assert sha(TASK / 'review-r4-guards' / (row['name'] + '.source.py')) == row['source_sha256']
    output = (TASK / 'review-r4-guards' / (row['name'] + '.stdout.txt')).read_text()
    if row['name'] == 'submitted':
        assert row['exit_code'] == 0 and '32 passed' in output
    else:
        assert row['exit_code'] == 1 and 'FAILED tests/test_motif.py::' + targets[row['name']] in output
inventory = json.loads((OUT / 'inventory.json').read_text())
assert inventory['changed_frozen'] == [] and inventory['outside_scope'] == []
assert len(inventory['runs']) == 6
index = json.loads((TASK / 'pi-r4-docs2/run-index.json').read_text())
assert len(index['runs']) == 20 and index['current_run_excluded']
assert all((TASK / r['run'] / 'record.json').is_file() for r in index['runs'])
for p in TASK.glob('review_r4*.py'):
    ast.parse(p.read_text())
subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
accepted = {p: sha(ROOT / p) for p in ('src/kmesh/logic/motif.py', 'tests/test_motif.py', *DOCS,
                                      'reports/T0014/review-r4/review.md')}
result = dict(task_status='accepted', result='PASS', head=inventory['head'],
    accepted_files_sha256=accepted, independent_focused=32,
    independent_mutants_rejected=4, prior_mutants_rejected_carried_forward=10,
    independent_full_this_round='not_run', verified_prior_pi_full=917, prior_independent_full=925,
    full_version_note='Full results belong to their recorded earlier test versions; current product unchanged, four functions reverified.',
    frozen_files_unchanged=2981, recorded_pi_r4_runs=6,
    criteria={f'A{i}': 'PASS' for i in range(1, 8)}, remaining_substantive_findings=[],
    limitations=['Historical evidence gaps retained; R4 wording and handoff omission corrected by Codex with links to originals.',
                 'Model/provider identity is self-report, not independently verified.',
                 'Bounded exponential single-tree motif reference; no substructure, world audit, split or LLM experiment conclusion.'],
    checks=checks, code_and_tests_unchanged_by_reviewer=True, committed=False, pushed=False)
(OUT / 'final-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(f'PASS: accepted A1-A7; product/tests/history unchanged; 4 docs/{links} links; no commit/push')
