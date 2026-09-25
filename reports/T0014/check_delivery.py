"""T0014 frozen scope, environment and document checks, not a correctness oracle."""
import hashlib
import importlib.metadata
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
HANDOFF = 'docs/handoffs/T0014-proof-motif.md'
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
    assert out.is_dir() and out.parent == TASK
    baseline = json.loads((TASK / 'planning-baseline.json').read_text())
    frozen = json.loads((TASK / 'planning-files.json').read_text())
    for path, digest in frozen.items():
        assert sha(path) == digest, f'frozen file changed: {path}'
    assert git('branch', '--show-current').strip() == 'T0014-proof-motif'
    subprocess.run(['git', 'merge-base', '--is-ancestor', baseline['head'], 'HEAD'], cwd=ROOT, check=True)
    current = {p for p in git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0') if p}
    for path in current:
        assert path in frozen or path in MUTABLE or path == 'reports/T0014/planning-files.json' or path.startswith('reports/T0014/pi-'), f'outside scope: {path}'
        assert (ROOT / path).is_file(), path
        assert not {'pytest-tmp', '__pycache__'}.intersection(Path(path).parts), path
    if mode == 'preflight':
        import kmesh
        assert sys.version == baseline['python']
        assert str(Path(sys.executable).absolute()) == baseline['executable']
        assert str(Path(kmesh.__file__).resolve()) == baseline['kmesh_path']
        for name, version in baseline['packages'].items():
            assert importlib.metadata.version(name) == version, name
        assert not (ROOT / PRODUCT).exists() and not (ROOT / TEST).exists(), 'preflight must precede coding'
        print('PASS: frozen accepted base and planning files, environment, branch, scope; new files absent')
        return
    provenance = sorted(TASK.glob('pi-*/provenance.md'))
    assert len(provenance) == 1, 'write one round-1 provenance before docs'
    # Generate the index before checking links to it; the current RUN is excluded.
    rows = []
    for path in TASK.glob('pi-*/record.json'):
        if path.parent == out:
            continue  # This docs run is still running; do not report its future outcome.
        record = json.loads(path.read_text())
        assert record['status'] == 'finished', path
        for stream in ('stdout', 'stderr'):
            assert sha((path.parent / (stream + '.txt')).relative_to(ROOT)) == record[stream + '_sha256'], path
        rows.append(dict(run=path.parent.name, argv=record['argv'], exit_code=record['exit_code'],
                         started_at_utc=record['started_at_utc'], finished_at_utc=record['finished_at_utc'], elapsed_s=record['elapsed_s']))
    rows.sort(key=lambda r: r['started_at_utc'])
    (out / 'run-index.json').write_text(json.dumps(dict(scope='finished Pi RUNs before this docs run', runs=rows,
        current_source_sha256={p: sha(p) for p in (PRODUCT, TEST)}), indent=2) + '\n')
    docs = [ROOT / path for path in DOCS] + provenance
    links = 0
    for path in [*docs, ROOT / PRODUCT, ROOT / TEST]:
        text = path.read_text()
        assert text.endswith('\n') and not text.endswith('\n\n') and all(s == s.rstrip() for s in text.splitlines()), path
        if path.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                u = urlsplit(target.strip().strip('<>'))
                if not u.scheme and not u.netloc and u.path:
                    assert (path.parent / unquote(u.path)).exists(), (path, target)
                    links += 1
    assert '- 状态：`awaiting_review`' in (ROOT / HANDOFF).read_text()
    assert 'awaiting_review' in next(s for s in (ROOT / DOCS[1]).read_text().splitlines() if s.startswith('- T0014'))
    assert 'awaiting_review' in next(s for s in (ROOT / DOCS[1]).read_text().splitlines() if s.startswith('| 单棵证明跨世界 motif 键 |'))
    assert all((ROOT / p).exists() for p in (PRODUCT, TEST))
    readme = (ROOT / 'README.md').read_text().split('证明结构签名（T0014', 1)[1].split('\n## ', 1)[0]
    assert 'awaiting_review' in readme
    example = re.search(r'```python\n(.*?)```', readme, re.S).group(1)
    run = subprocess.run([sys.executable, '-c', example], cwd=ROOT, capture_output=True, text=True, timeout=10)
    print(run.stdout, end='')
    print(run.stderr, end='', file=sys.stderr)
    assert run.returncode == 0, 'README COPY example failed'
    print(f'PASS: frozen base, scope, {len(docs)} docs/{links} links, hygiene, awaiting_review; run-index.json records {len(rows)} earlier finished RUNs')


if __name__ == '__main__':
    main()
