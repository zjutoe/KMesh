"""Close review documentation and verify that submission/history stayed frozen."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
MUTABLE_DOCS = {'README.md', 'docs/implementation_status.md', 'docs/handoffs/T0015-proof-subtree.md'}


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


inputs = json.loads((TASK / 'review-r1/frozen-inputs.json').read_text())
for path, digest in inputs.items():
    if path not in MUTABLE_DOCS:
        assert sha(path) == digest, path
for path in TASK.glob('review_r1*.py'):
    ast.parse(path.read_text())
ast.parse((TASK / 'check_rework_r2.py').read_text())
probe = json.loads((TASK / 'review-r1-probe/result.json').read_text())
assert probe['extraction_subclass_error']['type'] == 'TypeError'
guards = json.loads((TASK / 'review-r1-guards/guards.json').read_text())
for name in ('submitted', 'corrupt_chain_refs', 'retry_logic_error', 'consume_generator'):
    assert guards['cases'][name]['exit_code'] == 0
assert guards['cases']['lazy_forbidden_import']['guard_valid'] is True
links = 0
docs = [*(ROOT / p for p in sorted(MUTABLE_DOCS)), TASK / 'review-r1/review.md']
for path in docs:
    content = path.read_text()
    assert content.endswith('\n') and all(s == s.rstrip() for s in content.splitlines()), path
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
        u = urlsplit(target.strip().strip('<>'))
        if not u.scheme and not u.netloc and u.path:
            assert (path.parent / unquote(u.path)).exists(), (path, target)
            links += 1
handoff = (ROOT / 'docs/handoffs/T0015-proof-subtree.md').read_text()
status = (ROOT / 'docs/implementation_status.md').read_text()
readme = (ROOT / 'README.md').read_text().split('完整证明子树（T0015', 1)[1]
assert '- 状态：`needs_changes`' in handoff
assert 'needs_changes' in next(x for x in status.splitlines() if x.startswith('- T0015'))
assert 'needs_changes' in next(x for x in status.splitlines() if x.startswith('| 完整有根证明子树抽取 |'))
assert '**`needs_changes`**' in readme
subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
for path in TASK.glob('review-r1*/record.json'):
    r = json.loads(path.read_text())
    if r['status'] == 'running':
        assert path.parent.name == 'review-r1-close'
        continue
    assert r['status'] == 'finished' and r['exit_code'] == 0, path
    for stream in ('stdout', 'stderr'):
        assert sha(path.parent.relative_to(ROOT) / (stream + '.txt')) == r[stream + '_sha256']
audit = dict(result='needs_changes', task_status='needs_changes',
             independent_focused='16 passed', independent_full='not_run; checked Pi 933 raw evidence',
             product_defects=['accepted ProofStep subclass reconstruction TypeError'],
             surviving_faults=['corrupt_chain_refs', 'retry_logic_error', 'consume_generator'],
             source_sha256={p: sha(p) for p in ('src/kmesh/logic/proof_subtree.py', 'tests/test_proof_subtree.py')},
             frozen_planning_files=3088, historical_inputs_unchanged=True, docs_links=links)
(TASK / 'review-r1/final-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print(f'PASS: review closed as needs_changes; submitted code/tests and historical evidence unchanged; {links} local links; hygiene/states')
