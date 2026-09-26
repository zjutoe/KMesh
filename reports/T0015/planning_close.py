"""Check T0015's ready handoff, helpers and evidence, without implementation."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
DOCS = ('docs/handoffs/T0015-proof-subtree.md', 'docs/implementation_status.md',
        'docs/decisions.md', 'docs/proof_identity_v1.md', 'docs/motif_identity_v1.md',
        'reports/T0015/planning-review.md')
links = 0
for name in DOCS:
    p = ROOT / name
    text = p.read_text()
    assert text.endswith('\n') and all(line == line.rstrip() for line in text.splitlines()), name
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        u = urlsplit(target.strip().strip('<>'))
        if not u.scheme and not u.netloc and u.path:
            assert (p.parent / unquote(u.path)).exists(), (p, target)
            links += 1
for p in TASK.glob('*.py'):
    ast.parse(p.read_text())
assert not (ROOT / 'src/kmesh/logic/proof_subtree.py').exists()
assert not (ROOT / 'tests/test_proof_subtree.py').exists()
handoff = (ROOT / DOCS[0]).read_text()
assert '- 状态：`ready`' in handoff
assert all(section in handoff for section in ('## 任务信息', '## 目标、范围与交付物', '## 前提与假设',
    '## 具体实施步骤', '## 验证方法', '## 验收标准', '## Pi 执行记录', '## Codex 验收记录'))
assert 'T0015（完整有根证明子树抽取）：`ready`' in (ROOT / DOCS[1]).read_text()
assert (ROOT / 'KMesh_Research_Plan_v0.1.md').read_bytes() == subprocess.check_output(
    ['git','show','f5ef96f:KMesh_Research_Plan_v0.1.md'], cwd=ROOT)
source_changes = subprocess.check_output(['git','diff','--name-only','HEAD','--','src','tests'],cwd=ROOT,text=True)
assert source_changes == ''
checks = {}
for name in ('planning-baseline', 'planning-examples', 'planning-edge-examples', 'planning-collect'):
    record = json.loads((TASK / name / 'record.json').read_text())
    assert record['status'] == 'finished' and record['exit_code'] == 0
    assert record['before']['source_sha256'] == record['after']['source_sha256']
    for stream in ('stdout','stderr'):
        assert hashlib.sha256((TASK/name/(stream+'.txt')).read_bytes()).hexdigest() == record[stream+'_sha256']
    checks[name] = {'exit_code': record['exit_code'], 'elapsed_s': record['elapsed_s']}
assert '917 tests collected' in (TASK/'planning-collect/stdout.txt').read_text()
driver = ast.parse((TASK/'run_checks.py').read_text())
tests = next(ast.literal_eval(n.value) for n in driver.body if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id == 'TESTS' for t in n.targets))
assert len(tests) == 15 and tests[0] == 'tests/test_proof_subtree.py'
subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
result = dict(task_status='ready', baseline='f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41',
    checks=checks, independent_design_review='read-only /root/design_t0012; no unresolved design findings',
    current_baseline_tests_collected=917, new_product='not_created', new_tests='not_created',
    research_protocol_changed=False, committed=False, pushed=False)
(TASK/'planning-close/result.json').write_text(json.dumps(result,indent=2)+'\n')
print(f'PASS: ready handoff, 6 documents/{links} links, helper syntax, fixture evidence, baseline collection; product/tests not created')
