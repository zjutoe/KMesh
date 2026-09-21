"""Freeze and close the bounded T0011 R2 review; never edit submitted code."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / 'reports/T0011'
PRODUCT = 'src/kmesh/logic/clause_key.py'
TEST = 'tests/test_clause_key.py'
DOCS = ('README.md', 'docs/implementation_status.md', 'docs/handoffs/T0011-clause-key.md')


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def read(name):
    return json.loads((TASK / name).read_text())


def main():
    mode = sys.argv[1]
    assert mode in ('freeze', 'close')
    previous = read('review-r1/final-audit.json')
    baseline = read('planning-baseline.json')
    planning = read('planning-files.json')
    protected = previous['history_sha256'] | previous['review_material_sha256'] | planning
    protected.update({p: h for p, h in baseline['source_sha256'].items() if h is not None})
    for name, digest in protected.items():
        assert sha(name) == digest, name
    assert sha(PRODUCT) == previous['reviewed_files'][PRODUCT]
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    assert head == previous['head'] and branch == 'T0011-clause-key'
    changed = set()
    for command in (['git', 'diff', 'HEAD', '--name-only', '-z'], ['git', 'ls-files', '--others', '--exclude-standard', '-z']):
        changed.update(p for p in subprocess.check_output(command, cwd=ROOT, text=True).split('\0') if p)
    for name in changed:
        assert name in protected or name in (PRODUCT, TEST, *DOCS) or name.startswith('reports/T0011/'), name
        assert (ROOT / name).is_file(), name
        assert not {'pytest-tmp', '__pycache__'}.intersection(Path(name).parts), name
    if mode == 'freeze':
        out = TASK / 'review-r2-freeze'
        inputs = {p: sha(p) for p in (PRODUCT, TEST, *DOCS)}
        for name in inputs:
            target = out / 'input-snapshot' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        history = {}
        for path in TASK.rglob('*'):
            if path.is_file() and not {'pytest-tmp', '__pycache__'}.intersection(path.parts):
                if not path.relative_to(TASK).parts[0].startswith('review-r2'):
                    history[str(path.relative_to(ROOT))] = sha(path.relative_to(ROOT))
        runs = []
        for path in TASK.glob('pi-r2*/record.json'):
            r = json.loads(path.read_text())
            assert r['status'] == 'finished', path
            for stream in ('stdout', 'stderr'):
                assert sha((path.parent / (stream + '.txt')).relative_to(ROOT)) == r[stream + '_sha256'], path
            for stage in ('before', 'after'):
                assert r[stage]['source_sha256'][PRODUCT] == inputs[PRODUCT], path
                for name, digest in baseline['source_sha256'].items():
                    if digest is not None:
                        assert r[stage]['source_sha256'][name] == digest, (path, stage, name)
            runs.append(dict(run=path.parent.name, started=r['started_at_utc'], elapsed_s=r['elapsed_s'],
                             exit_code=r['exit_code'], argv=r['argv'],
                             test_before=r['before']['source_sha256'][TEST], test_after=r['after']['source_sha256'][TEST],
                             stdout=(path.parent / 'stdout.txt').read_text(), stderr=(path.parent / 'stderr.txt').read_text()))
        runs.sort(key=lambda r: r['started'])
        assert runs[0]['run'] == 'pi-r2-preflight' and runs[0]['exit_code'] == 0
        assert runs[0]['test_before'] == runs[0]['test_after'] == previous['reviewed_files'][TEST]
        assert next(r for r in runs if r['run'] == 'pi-r2-focused2')['test_after'] == inputs[TEST]
        result = dict(head=head, branch=branch, input_sha256=inputs, history_sha256=history, pi_runs=runs)
        (out / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(dict(input_sha256=inputs, history_files=len(history), runs=[{k: r[k] for k in ('run', 'exit_code', 'elapsed_s', 'started')} for r in runs]), indent=2))
        return
    freeze = read('review-r2-freeze/audit.json')
    for name, digest in freeze['history_sha256'].items():
        assert sha(name) == digest, name
    assert all(sha(p) == freeze['input_sha256'][p] for p in (PRODUCT, TEST))
    guards = read('review-r2-guards/guards.json')
    assert guards['mode'] == 'enforce' and guards['test_sha256'] == sha(TEST)
    assert guards['cases'][0]['exit_code'] == 0 and all(r['detected'] for r in guards['cases'][1:])
    assert '63 passed' in (TASK / 'review-r2-guards/submitted.stdout').read_text()
    assert read('review-r2-guards/record.json')['exit_code'] == 0
    assert read('review-r1-full/record.json')['exit_code'] == 0
    assert '771 passed' in (TASK / 'review-r1-full/stdout.txt').read_text()
    docs = [ROOT / p for p in DOCS] + [TASK / 'review-r2/review.md']
    links = 0
    for path in [*docs, ROOT / PRODUCT, ROOT / TEST]:
        text = path.read_text()
        assert text.endswith('\n') and all(s == s.rstrip() for s in text.splitlines()), path
        if path.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                u = urlsplit(target.strip().strip('<>'))
                if not u.scheme and not u.netloc and u.path:
                    assert (path.parent / unquote(u.path)).exists(), (path, target)
                    links += 1
    assert '- 状态：`accepted`' in (ROOT / DOCS[2]).read_text()
    assert '`accepted`' in next(s for s in (ROOT / DOCS[1]).read_text().splitlines() if s.startswith('- T0011'))
    assert '**状态：`accepted`（2026-09-21，Codex 第 2 轮复验）**' in (ROOT / DOCS[0]).read_text()
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    result = dict(result='PASS', task_status='accepted', head=head, branch=branch,
                  accepted_files={p: sha(p) for p in (PRODUCT, TEST)},
                  focused_passed=63, rejected_mutants=5, full_carried_forward=771, full_rerun=False,
                  history_files_checked=len(freeze['history_sha256']), history_sha256=freeze['history_sha256'],
                  closure_document_sha256={p: sha(p) for p in DOCS},
                  limitations=['Finite synthetic verification only; not proof uniqueness, motif, world audit or LLM training results.', 'R1 missing historical helper text and environment provenance limits retained.'])
    target = TASK / 'review-r2/final-audit.json'
    assert not target.exists()
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(f'PASS: accepted files/history unchanged, guards 5/5, 63 focused; {len(docs)} docs/{links} links; accepted')


if __name__ == '__main__':
    main()
