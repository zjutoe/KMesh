"""Codex R2 preflight/docs checker; run through the unchanged recorder.

The round-1 checker stays frozen. This checker admits Codex review evidence
and one new R2 provenance without relaxing the old-file or path boundary.
"""
import argparse
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
BASELINE = 'reports/T0015/rework-r2-baseline.json'


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('preflight', 'docs'))
    parser.add_argument('run')
    args = parser.parse_args()
    assert re.fullmatch(r'pi-r2[a-z0-9_-]*', args.run)
    out = TASK / args.run
    assert out.is_dir()
    baseline = json.loads((ROOT / BASELINE).read_text())
    assert git('rev-parse', 'HEAD') == baseline['head']
    assert git('branch', '--show-current') == 'T0015-proof-subtree'
    for path, digest in baseline['files'].items():
        assert (ROOT / path).is_file() and sha(path) == digest, f'frozen changed/missing: {path}'
    current = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')) - {''}
    for path in current:
        assert path in baseline['files'] or path in MUTABLE or path == BASELINE or path.startswith('reports/T0015/pi-r2'), f'outside scope: {path}'
        assert (ROOT / path).is_file(), path
        assert not {'pytest-tmp', '__pycache__'}.intersection(Path(path).parts), path
    handoff = (ROOT / HANDOFF).read_text()
    status = (ROOT / DOCS[1]).read_text()
    expected = 'in_progress' if args.phase == 'preflight' else 'awaiting_review'
    assert f'- 状态：`{expected}`' in handoff
    assert expected in next(s for s in status.splitlines() if s.startswith('- T0015'))
    if args.phase == 'preflight':
        for path, digest in baseline['source_sha256'].items():
            assert sha(path) == digest, f'preflight must precede rework: {path}'
        planning = json.loads((TASK / 'planning-baseline.json').read_text())
        import kmesh
        assert sys.version == planning['python']
        assert str(Path(sys.executable).absolute()) == planning['executable']
        assert str(Path(kmesh.__file__).resolve()) == planning['kmesh_path']
        for name, version in planning['packages'].items():
            assert importlib.metadata.version(name) == version
        print('PASS: R1 source hashes, frozen history/planning/review, HEAD/branch/scope, environment, in_progress')
        return
    provenance = TASK / 'pi-r2/provenance.md'
    assert sorted(TASK.glob('pi-r2*/provenance.md')) == [provenance], 'one new R2 provenance'
    assert expected in next(s for s in status.splitlines() if s.startswith('| 完整有根证明子树抽取 |'))
    assert '../../reports/T0015/pi-r2/provenance.md' in handoff
    tests = next(ast.literal_eval(n.value) for n in ast.parse((TASK / 'run_checks.py').read_text()).body
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TESTS' for t in n.targets))
    rows = []
    verified = set()
    for path in sorted(TASK.glob('pi-*/record.json')):
        if path.parent == out:
            continue
        r = json.loads(path.read_text())
        assert r['status'] == 'finished', path
        for stream in ('stdout', 'stderr'):
            assert sha(path.parent.relative_to(ROOT) / (stream + '.txt')) == r[stream + '_sha256'], path
        rows.append(dict(run=path.parent.name, argv=r['argv'], exit_code=r['exit_code'],
                         started_at_utc=r['started_at_utc'], finished_at_utc=r['finished_at_utc'], elapsed_s=r['elapsed_s']))
        if path.parent.name.startswith('pi-r2') and r['exit_code'] == 0:
            same = all(r[side]['source_sha256'][p] == sha(p) for side in ('before', 'after') for p in (PRODUCT, TEST))
            files = [a for a in r['argv'] if a.startswith('tests/test_') and a.endswith('.py')]
            if same and files in ([TEST], tests):
                assert '--basetemp' in r['argv'], path
                assert not re.search(r'\b\d+ (skipped|xfailed|xpassed)\b', (path.parent / 'stdout.txt').read_text())
                verified.add('focused' if files == [TEST] else 'full')
            guards = path.parent / 'guards.json'
            if same and guards.exists():
                assert json.loads(guards.read_text())['all_guards_valid'] is True
                verified.add('guards')
    assert verified == {'focused', 'full', 'guards'}, verified
    rows.sort(key=lambda r: r['started_at_utc'])
    (out / 'run-index.json').write_text(json.dumps(dict(scope='T0015 completed Pi RUNs only; current excluded', runs=rows,
        current_source_sha256={p: sha(p) for p in (PRODUCT, TEST)}), indent=2) + '\n')
    links = 0
    for path in [*(ROOT / p for p in DOCS), provenance, ROOT / PRODUCT, ROOT / TEST]:
        content = path.read_text()
        assert content.endswith('\n') and all(s == s.rstrip() for s in content.splitlines()), path
        if path.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
                u = urlsplit(target.strip().strip('<>'))
                if not u.scheme and not u.netloc and u.path:
                    assert (path.parent / unquote(u.path)).exists(), (path, target)
                    links += 1
    section = (ROOT / 'README.md').read_text().split('完整证明子树（T0015', 1)[1].split('\n## ', 1)[0]
    assert expected in section
    assert re.findall(r'tests/test_\w+\.py', re.search(r'```bash\n(.*?)```', section, re.S).group(1)) == tests
    example = re.search(r'```python\n(.*?)```', section, re.S).group(1)
    subprocess.run([sys.executable, '-c', example], cwd=ROOT, check=True, timeout=10)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    print(f'PASS: frozen/scope, current focused/full/guards, 4 docs/{links} links, states, hygiene, README; index excludes current RUN')


if __name__ == '__main__':
    main()
