"""T0011 review/rework scope and documentation checks; not a product oracle."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / 'reports/T0011'
PRODUCT = 'src/kmesh/logic/clause_key.py'
TEST = 'tests/test_clause_key.py'
HANDOFF = 'docs/handoffs/T0011-clause-key.md'
DOCS = ['README.md', 'docs/implementation_status.md', HANDOFF]


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    mode = sys.argv[1]
    assert mode in ('preflight', 'docs', 'close')
    freeze = json.loads((TASK / 'review-r1-freeze/audit.json').read_text())
    baseline = json.loads((TASK / 'planning-baseline.json').read_text())
    planning = json.loads((TASK / 'planning-files.json').read_text())
    protected = dict(freeze['history_sha256']) | planning
    protected.update({p: h for p, h in baseline['source_sha256'].items() if h is not None})
    audit_path = TASK / 'review-r1/final-audit.json'
    if mode != 'close':
        audit = json.loads(audit_path.read_text())
        protected.update(audit['review_material_sha256'])
    for name, digest in protected.items():
        assert sha(name) == digest, f'frozen file changed: {name}'
    assert sha(PRODUCT) == freeze['input_sha256'][PRODUCT]
    assert git('rev-parse', 'HEAD') == freeze['head']
    assert git('branch', '--show-current') == 'T0011-clause-key'
    changed = set(git('diff', 'HEAD', '--name-only', '-z').split('\0'))
    changed.update(git('ls-files', '--others', '--exclude-standard', '-z').split('\0'))
    allowed = set(protected) | set(DOCS) | {PRODUCT, TEST, 'reports/T0011/planning-files.json', 'reports/T0011/review-r1/final-audit.json'}
    for name in changed - {''}:
        permitted = name in allowed or name.startswith('reports/T0011/pi-r2') or name.startswith('reports/T0011/review-r1-close/')
        if mode == 'close':
            permitted = permitted or name.startswith('reports/T0011/review-r1')
        assert permitted, f'outside rework scope: {name}'
        assert (ROOT / name).is_file(), f'deleted: {name}'
        assert not {'pytest-tmp', '__pycache__'}.intersection(Path(name).parts), name
    if mode in ('preflight', 'close'):
        assert sha(TEST) == freeze['input_sha256'][TEST], 'submitted tests changed before rework'
    if mode == 'preflight':
        import kmesh
        assert sys.version_info[:3] == (3, 13, 9)
        assert str(Path(sys.executable).absolute()) == str(ROOT / '.venv/bin/python')
        assert Path(kmesh.__file__).resolve() == ROOT / 'src/kmesh/__init__.py'
        for name, version in baseline['packages'].items():
            assert importlib.metadata.version(name) == version, name
        print('PASS: rework baseline, product/test hashes, old history, branch, environment, scope')
        return
    paths = [ROOT / p for p in DOCS]
    paths.extend(sorted((TASK / 'review-r1').glob('*.md')))
    provenance = sorted(TASK.glob('pi-r2*/provenance.md'))
    if mode == 'docs':
        assert provenance, 'write a new R2 provenance before docs check'
    paths.extend(provenance)
    links = 0
    for path in [*paths, ROOT / PRODUCT, ROOT / TEST]:
        text = path.read_text()
        assert text.endswith('\n'), path
        assert all(line == line.rstrip() for line in text.splitlines()), path
        if path.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                parsed = urlsplit(target.strip().strip('<>'))
                if not parsed.scheme and not parsed.netloc and parsed.path:
                    assert (path.parent / unquote(parsed.path)).exists(), (path, target)
                    links += 1
    status = 'needs_changes' if mode == 'close' else 'awaiting_review'
    assert '- 状态：`' + status + '`' in (ROOT / HANDOFF).read_text()
    line = next(s for s in (ROOT / DOCS[1]).read_text().splitlines() if s.startswith('- T0011'))
    assert status in line
    readme = (ROOT / DOCS[0]).read_text()
    assert '**状态：`' + status + '`' in readme
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    if mode == 'close':
        review_hashes = {}
        for path in TASK.glob('review-r1*'):
            if path.name == 'review-r1-close':
                continue  # Current recorder writes its final metadata after this check returns.
            for item in path.rglob('*'):
                if item.is_file() and item != audit_path and not {'pytest-tmp', '__pycache__'}.intersection(item.parts):
                    review_hashes[str(item.relative_to(ROOT))] = sha(item.relative_to(ROOT))
        result = dict(result='NEEDS_CHANGES', task_status='needs_changes', head=freeze['head'],
                      reviewed_files=freeze['input_sha256'], product_defect_found=False,
                      full_tests_passed=771, finite_oracle_checks=3571,
                      surviving_mutants=['diagnostic_suffix', 'float_variable_number', 'conditional_reverse'],
                      history_sha256=freeze['history_sha256'], review_material_sha256=review_hashes,
                      closure_document_sha256={p: sha(p) for p in DOCS},
                      limitations=['Finite probes do not prove correctness for all inputs.', 'No proof uniqueness, motif, world audit or training experiment.'])
        assert not audit_path.exists(), 'do not overwrite a final audit'
        audit_path.write_text(json.dumps(result, indent=2) + '\n')
    print(f'PASS: frozen product/history, scope, {len(paths)} documents/{links} local links, text hygiene, {status}')


if __name__ == '__main__':
    main()
