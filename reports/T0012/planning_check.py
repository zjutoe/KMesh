"""Check the handoff artifacts before freezing the final planning manifest."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path.cwd()
TASK = ROOT / 'reports/T0012'
baseline = json.loads((TASK / 'planning-baseline.json').read_text())
mutable_planning = {'docs/proof_identity_v1.md', 'docs/decisions.md', 'docs/implementation_status.md'}
for path, digest in baseline['initial_repository_sha256'].items():
    if path not in mutable_planning:
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
for path, digest in baseline['source_sha256'].items():
    if digest is None:
        assert not (ROOT / path).exists(), path
    else:
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
current = {p for p in subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], text=True).split('\0') if p}
for path in current - baseline['initial_repository_sha256'].keys():
    assert path == 'docs/handoffs/T0012-proof-key.md' or path.startswith('reports/T0012/'), path
docs = [ROOT / p for p in ('docs/handoffs/T0012-proof-key.md', 'docs/proof_identity_v1.md', 'docs/decisions.md', 'docs/implementation_status.md', 'reports/T0012/planning-review.md')]
links = 0
for path in docs:
    text = path.read_text()
    assert text.endswith('\n') and all(s == s.rstrip() for s in text.splitlines()), path
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
        u = urlsplit(target.strip().strip('<>'))
        if not u.scheme and not u.netloc and u.path:
            assert (path.parent / unquote(u.path)).exists(), (path, target)
            links += 1
for path in TASK.glob('*.py'):
    text = path.read_text()
    ast.parse(text, filename=str(path))
    assert text.endswith('\n') and all(s == s.rstrip() for s in text.splitlines()), path
assert '- 状态：`ready`' in docs[0].read_text()
assert '`ready`' in next(s for s in docs[3].read_text().splitlines() if s.startswith('- T0012'))
for run in ('planning-preflight', 'planning-examples', 'planning-deep-example'):
    r = json.loads((TASK / run / 'record.json').read_text())
    assert r['status'] == 'finished' and r['exit_code'] == 0, run
subprocess.run(['git', 'diff', '--check'], check=True)
result = dict(result='PASS', task_status='ready', product_implemented=False, documents=len(docs), local_links=links,
              preserved_initial_files=len(baseline['initial_repository_sha256'])-len(mutable_planning),
              baseline='accepted uncommitted T0011 worktree at 4c457e2', scope='planning only')
(TASK / 'planning-check/result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
