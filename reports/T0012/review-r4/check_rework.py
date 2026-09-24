"""Codex T0012 R5 scope/docs helper; product correctness checked separately."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / 'reports/T0012'
PRODUCT = 'src/kmesh/logic/proof_key.py'
TEST = 'tests/test_proof_key.py'
HANDOFF = 'docs/handoffs/T0012-proof-key.md'
DOCS = ('README.md', 'docs/implementation_status.md', HANDOFF)
MUTABLE = (TEST, *DOCS)

def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

def main():
    mode = sys.argv[1]
    assert mode in ('preflight', 'readme', 'docs', 'close')
    freeze = json.loads((TASK / 'review-r4-freeze/input-audit.json').read_text())
    inputs = json.loads((TASK / 'review-r4-freeze/input-manifest.json').read_text())
    protected = {p: h for p, h in inputs.items() if p not in MUTABLE}
    audit_path = TASK / 'review-r4/final-audit.json'
    if mode != 'close':
        protected.update(json.loads(audit_path.read_text())['review_material_sha256'])
    for name, digest in protected.items():
        assert sha(name) == digest, f'frozen file changed: {name}'
    assert git('rev-parse', 'HEAD') == freeze['head']
    assert git('branch', '--show-current') == 'T0012-proof-key'
    current = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')) - {''}
    for name in current:
        allowed = name in protected or name in MUTABLE or name == 'reports/T0012/review-r4/final-audit.json' or name.startswith('reports/T0012/pi-r5') or name.startswith('reports/T0012/review-r4-close/')
        if mode == 'close':
            allowed |= name.startswith('reports/T0012/review-r4')
        assert allowed, f'outside rework scope: {name}'
        assert (ROOT / name).is_file(), name
        assert not {'pytest-tmp', '__pycache__'}.intersection(Path(name).parts), name
    if mode in ('preflight', 'close'):
        assert sha(TEST) == freeze['input_sha256'][TEST]
    if mode == 'preflight':
        import kmesh
        baseline = json.loads((TASK / 'planning-baseline.json').read_text())
        assert sys.version == baseline['python']
        assert str(Path(sys.executable).absolute()) == baseline['executable']
        assert str(Path(kmesh.__file__).resolve()) == baseline['kmesh_path']
        for name, version in baseline['packages'].items():
            assert importlib.metadata.version(name) == version
        print('PASS: frozen product/tests/history/review, HEAD, environment and rework scope')
        return
    if mode == 'readme':
        section = (ROOT / 'README.md').read_text().split('单棵证明的规范键（T0012', 1)[1]
        code = re.search(r'```python\n(.*?)```', section, re.S).group(1)
        # Uses the current submitted example unchanged; no private data or I/O permitted by contract.
        p = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=10)
        print(p.stdout, end='')
        print(p.stderr, end='', file=sys.stderr)
        assert p.returncode == 0, 'README example failed'
        print('PASS: actual README T0012 code block')
        return
    provenance = sorted(TASK.glob('pi-r5*/provenance.md'))
    if mode == 'docs':
        assert len(provenance) == 1, 'write one R5 provenance before docs'
    paths = [ROOT / p for p in DOCS] + [TASK / 'review-r4/review.md'] + provenance
    links = 0
    for path in [*paths, ROOT / PRODUCT, ROOT / TEST]:
        text = path.read_text()
        assert text.endswith('\n') and all(s == s.rstrip() for s in text.splitlines()), path
        if path.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                u = urlsplit(target.strip().strip('<>'))
                if not u.scheme and not u.netloc and u.path:
                    assert (path.parent / unquote(u.path)).exists(), (path, target)
                    links += 1
    status = 'needs_changes' if mode == 'close' else 'awaiting_review'
    assert '- 状态：`' + status + '`' in (ROOT / HANDOFF).read_text()
    assert status in next(s for s in (ROOT / DOCS[1]).read_text().splitlines() if s.startswith('- T0012'))
    assert '**状态：`' + status + '`' in (ROOT / DOCS[0]).read_text()
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    if mode == 'close':
        review_hashes = {}
        for directory in TASK.glob('review-r4*'):
            if directory.name == 'review-r4-close':
                continue  # Recorder will finish its own metadata after this command.
            for path in directory.rglob('*'):
                if path.is_file() and path != audit_path and not {'pytest-tmp', '__pycache__'}.intersection(path.parts):
                    review_hashes[str(path.relative_to(ROOT))] = sha(path.relative_to(ROOT))
        guards = json.loads((TASK / 'review-r4-guards/guards.json').read_text())
        survived = [r['name'] for r in guards['results'][1:] if r['exit_code'] == 0]
        result = dict(result='NEEDS_CHANGES', task_status='needs_changes', head=freeze['head'],
                      reviewed_files=freeze['input_sha256'], product_defect_found=False,
                      closed_findings=['entry_boundaries', 'output_types', 'import_isolation'],
                      pending_findings=['joint_K3_K4_K5BA', 'duplicate_COPY_rule', 'constant_case', 'before_after_purity', 'records'],
                      full_tests_passed=None, carried_full_tests_passed=840, submitted_focused_tests=69,
                      surviving_mutants=survived, rejected_mutants=[r['name'] for r in guards['results'][1:] if r['exit_code'] == 1],
                      review_material_sha256=review_hashes,
                      closure_document_sha256={p: sha(p) for p in DOCS},
                      limitations=['Finite product probes do not prove general identity correctness.',
                                   'Pi claimed 847 full tests have no submitted raw run; not independently rerun.',
                                   'R4 boundary precedes preflight; test snapshots show R4 -> R3 -> R4. Switching operation unknown.',
                                   'No uniqueness, motif, world audit or training experiment.'])
        assert not audit_path.exists(), 'refuse to overwrite final audit'
        audit_path.write_text(json.dumps(result, indent=2) + '\n')
    print(f'PASS: frozen product/history/review, scope, {len(paths)} docs/{links} local links, hygiene, {status}')

if __name__ == '__main__':
    main()
