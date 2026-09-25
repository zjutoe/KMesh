"""Codex T0014 R3 scope/evidence checker; preflight before tests, docs after review submission."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0014'
PRODUCT = 'src/kmesh/logic/motif.py'
TEST = 'tests/test_motif.py'
DOCS = ('README.md', 'docs/implementation_status.md', 'docs/handoffs/T0014-proof-motif.md')


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


mode, out_arg = sys.argv[1:]
assert mode in ('preflight', 'docs')
out = ROOT / out_arg
assert out.is_dir() and out.parent == TASK and out.name.startswith('pi-r3-')
baseline = json.loads((TASK / 'review-r2/rework-baseline.json').read_text())
assert git('rev-parse', 'HEAD') == baseline['head']
assert git('branch', '--show-current') == 'T0014-proof-motif'
for name, value in baseline['files'].items():
    assert digest(name) == value, f'frozen file changed: {name}'
current = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')) - {''}
for name in current:
    assert name in baseline['files'] or name in (TEST, *DOCS, 'reports/T0014/review-r2/rework-baseline.json') or name.startswith('reports/T0014/pi-r3'), name
    assert (ROOT / name).is_file(), name
    assert 'pytest-tmp' not in Path(name).parts and '__pycache__' not in Path(name).parts, name
handoff = (ROOT / DOCS[2]).read_text()
status = (ROOT / DOCS[1]).read_text()
if mode == 'preflight':
    assert digest(TEST) == baseline['test_sha256'], 'preflight must precede test edits'
    assert '- 状态：`in_progress`' in handoff
    assert 'in_progress' in next(s for s in status.splitlines() if s.startswith('- T0014'))
    print('PASS: R2 test baseline, frozen product/planning/history/review, HEAD/branch/scope, in_progress')
    raise SystemExit(0)
assert '- 状态：`awaiting_review`' in handoff
assert 'awaiting_review' in next(s for s in status.splitlines() if s.startswith('- T0014'))
assert 'awaiting_review' in next(s for s in status.splitlines() if s.startswith('| 单棵证明跨世界 motif 键 |'))
provenance = list(TASK.glob('pi-r3*/provenance.md'))
assert len(provenance) == 1, 'one new R3 provenance; old history frozen'
rows = []
for path in TASK.glob('pi-*/record.json'):
    if path.parent == out:
        continue
    r = json.loads(path.read_text())
    assert r['status'] == 'finished', path
    for stream in ('stdout', 'stderr'):
        assert digest(str((path.parent / (stream + '.txt')).relative_to(ROOT))) == r[stream + '_sha256'], path
    rows.append(dict(run=path.parent.name, argv=r['argv'], exit_code=r['exit_code'],
                     started_at=r['started_at_utc'], finished_at=r['finished_at_utc'], elapsed_s=r['elapsed_s']))
rows.sort(key=lambda row: row['started_at'])
(out / 'run-index.json').write_text(json.dumps(dict(runs=rows, current_run_excluded=True,
    source_sha256={p: digest(p) for p in (PRODUCT, TEST)}), indent=2) + '\n')
links = 0
for path in [*(ROOT / p for p in DOCS), *provenance, ROOT / TEST]:
    text = path.read_text()
    assert text.endswith('\n') and not text.endswith('\n\n') and all(s == s.rstrip() for s in text.splitlines()), path
    if path.suffix == '.md':
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            u = urlsplit(target.strip().strip('<>'))
            if not u.scheme and not u.netloc and u.path:
                assert (path.parent / unquote(u.path)).exists(), (path, target)
                links += 1
ast.parse((ROOT / TEST).read_text())
readme = (ROOT / DOCS[0]).read_text().split('证明结构签名（T0014', 1)[1]
assert 'awaiting_review' in readme
example = re.search(r'```python\n(.*?)```', readme, re.S).group(1)
r = subprocess.run([sys.executable, '-c', example], cwd=ROOT, capture_output=True, text=True, timeout=10)
print(r.stdout, end='')
print(r.stderr, end='', file=sys.stderr)
assert r.returncode == 0
driver = ast.parse((TASK / 'run_checks.py').read_text())
tests = next(ast.literal_eval(n.value) for n in driver.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TESTS' for t in n.targets))
shell = re.search(r'```bash\n(.*?)```', readme, re.S).group(1)
assert re.findall(r'tests/test_\w+\.py', shell) == tests, 'README must match fourteen-file driver order'
subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
print(f'PASS: frozen product/history/scope; 4 docs/{links} links; hygiene, awaiting_review; README COPY and fourteen-file list; {len(rows)} prior RUNs indexed')
