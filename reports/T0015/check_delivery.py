"""T0015 frozen scope/record/docs checks; not a subtree correctness oracle."""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
PRODUCT = 'src/kmesh/logic/proof_subtree.py'
TEST = 'tests/test_proof_subtree.py'
HANDOFF = 'docs/handoffs/T0015-proof-subtree.md'
DOCS = ('README.md', 'docs/implementation_status.md', HANDOFF)
MUTABLE = (PRODUCT, TEST, *DOCS)


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def main():
    mode, out_arg = sys.argv[1:]
    assert mode in ('preflight', 'docs')
    out = (ROOT / out_arg).resolve()
    assert out.is_dir() and out.parent == TASK and out.name.startswith('pi-')
    baseline = json.loads((TASK / 'planning-baseline.json').read_text())
    frozen = json.loads((TASK / 'planning-files.json').read_text())
    for path, digest in frozen.items():
        assert sha(path) == digest, f'frozen file changed: {path}'
    assert git('branch', '--show-current').strip() == 'T0015-proof-subtree'
    subprocess.run(['git', 'merge-base', '--is-ancestor', baseline['head'], 'HEAD'], cwd=ROOT, check=True)
    current = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')) - {''}
    for path in current:
        assert path in frozen or path in MUTABLE or path == 'reports/T0015/planning-files.json' or path.startswith('reports/T0015/pi-'), f'outside scope: {path}'
        assert (ROOT / path).is_file(), path
        assert not {'pytest-tmp', '__pycache__'}.intersection(Path(path).parts), path
    handoff = (ROOT / HANDOFF).read_text()
    status = (ROOT / DOCS[1]).read_text()
    if mode == 'preflight':
        import kmesh
        assert sys.version == baseline['python']
        assert str(Path(sys.executable).absolute()) == baseline['executable']
        assert str(Path(kmesh.__file__).resolve()) == baseline['kmesh_path']
        for name, version in baseline['packages'].items():
            assert importlib.metadata.version(name) == version, name
        assert not (ROOT / PRODUCT).exists() and not (ROOT / TEST).exists(), 'preflight must precede coding'
        assert '- 状态：`in_progress`' in handoff
        assert 'in_progress' in next(s for s in status.splitlines() if s.startswith('- T0015'))
        print('PASS: frozen baseline/planning, environment, branch, scope, in_progress; new product/tests absent')
        return
    provenance = list(TASK.glob('pi-*/provenance.md'))
    assert len(provenance) == 1, 'one round-1 provenance; no duplicated command/time tables'
    rows = []
    for path in TASK.glob('pi-*/record.json'):
        if path.parent == out:
            continue
        r = json.loads(path.read_text())
        assert r['status'] == 'finished', path
        for stream in ('stdout', 'stderr'):
            assert sha((path.parent / (stream + '.txt')).relative_to(ROOT)) == r[stream + '_sha256'], path
        rows.append(dict(run=path.parent.name, argv=r['argv'], exit_code=r['exit_code'],
                         started_at_utc=r['started_at_utc'], finished_at_utc=r['finished_at_utc'], elapsed_s=r['elapsed_s']))
    rows.sort(key=lambda r: r['started_at_utc'])
    (out / 'run-index.json').write_text(json.dumps(dict(scope='T0015 finished Pi RUNs only; current docs excluded',
        runs=rows, current_source_sha256={p: sha(p) for p in (PRODUCT, TEST)}), indent=2) + '\n')
    links = 0
    for path in [*(ROOT / p for p in DOCS), *provenance, ROOT / PRODUCT, ROOT / TEST]:
        text = path.read_text()
        assert text.endswith('\n') and all(s == s.rstrip() for s in text.splitlines()), path
        if path.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                u = urlsplit(target.strip().strip('<>'))
                if not u.scheme and not u.netloc and u.path:
                    assert (path.parent / unquote(u.path)).exists(), (path, target)
                    links += 1
    assert '- 状态：`awaiting_review`' in handoff
    assert 'awaiting_review' in next(s for s in status.splitlines() if s.startswith('- T0015'))
    assert 'awaiting_review' in next(s for s in status.splitlines() if s.startswith('| 完整有根证明子树抽取 |'))
    pi_record = handoff.split('## Pi 执行记录', 1)[1].split('## Codex 验收记录', 1)[0]
    provenance_path = provenance[0].resolve()
    assert any((ROOT / HANDOFF).parent.joinpath(target).resolve() == provenance_path
               for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', pi_record)), 'handoff Pi record must link actual provenance'
    readme = (ROOT / 'README.md').read_text().split('完整证明子树（T0015', 1)[1].split('\n## ', 1)[0]
    assert 'awaiting_review' in readme
    example = re.search(r'```python\n(.*?)```', readme, re.S).group(1)
    r = subprocess.run([sys.executable, '-c', example], cwd=ROOT, capture_output=True, text=True, timeout=10)
    print(r.stdout, end='')
    print(r.stderr, end='', file=sys.stderr)
    assert r.returncode == 0, 'README subtree example failed'
    driver = ast.parse((TASK / 'run_checks.py').read_text())
    tests = next(ast.literal_eval(n.value) for n in driver.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'TESTS' for t in n.targets))
    shell = re.search(r'```bash\n(.*?)```', readme, re.S).group(1)
    assert re.findall(r'tests/test_\w+\.py', shell) == tests, 'README must match fifteen-file driver order'
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    print(f'PASS: scope/frozen, 4 docs/{links} links, provenance link, states, hygiene, README example/test list; {len(rows)} previous T0015 RUNs')


if __name__ == '__main__':
    main()
