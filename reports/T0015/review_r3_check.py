"""Codex R3 evidence-only acceptance checks. No product imports or test execution."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
DOCS = ('README.md', 'docs/implementation_status.md', 'docs/handoffs/T0015-proof-subtree.md')
SCRATCH = {'pytest-tmp', '__pycache__'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(rel):
    return json.loads((TASK / rel).read_text())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode()


def check_docs(state, paths):
    handoff = (ROOT / DOCS[2]).read_text()
    status = (ROOT / DOCS[1]).read_text()
    assert f'- 状态：`{state}`' in handoff
    assert state in next(s for s in status.splitlines() if s.startswith('- T0015'))
    assert state in next(s for s in status.splitlines() if s.startswith('| 完整有根证明子树抽取 |'))
    assert state in (ROOT / DOCS[0]).read_text().split('## 完整证明子树（T0015', 1)[1]
    links = 0
    for path in paths:
        text = path.read_text()
        assert text.endswith('\n') and all(line == line.rstrip() for line in text.splitlines()), path
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            u = urlsplit(target.strip().strip('<>'))
            if not u.scheme and not u.netloc and u.path:
                assert (path.parent / unquote(u.path)).exists(), (path, target)
                links += 1
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    return links


def audit():
    baseline = read('rework-r3-baseline.json')
    assert git('rev-parse', 'HEAD').strip() == baseline['head']
    assert git('branch', '--show-current').strip() == baseline['branch']
    ignore = baseline['ignore_original']
    allowed_changes = set(DOCS) | set(ignore)
    for rel, h in baseline['files'].items():
        if rel not in allowed_changes:
            assert sha(ROOT / rel) == h, rel
    visible = set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')) - {''}
    actual = {p.relative_to(ROOT).as_posix() for p in TASK.rglob('*')
              if p.is_file() and not SCRATCH.intersection(p.relative_to(TASK).parts)}
    extras = visible | actual
    extras -= set(baseline['files']) | {'reports/T0015/rework-r3-baseline.json', 'reports/T0015/review_r3_check.py'}
    assert all(p.startswith(('reports/T0015/pi-r3', 'reports/T0015/review-r3')) for p in extras), sorted(extras)
    for rel, original in ignore.items():
        expected = original + ''.join('!' + line + '\n' for line in original.splitlines())
        assert (ROOT / rel).read_text() == expected, rel
    hidden = baseline['previously_hidden_artifacts']
    assert len(hidden) == 26 and all(p in visible for p in hidden)
    for rel in hidden:
        if rel not in ignore:
            assert sha(ROOT / rel) == baseline['files'][rel], rel
    # Parent exclusions still apply without creating any temporary test directories.
    scratch = ['reports/T0015/pi-r1-r2guards/submitted/pytest-tmp/probe',
               'reports/T0015/pi-r1-r2full/__pycache__/probe']
    ignored = subprocess.check_output(['git', 'check-ignore', '--', *scratch], cwd=ROOT, text=True).splitlines()
    assert ignored == scratch
    runs = []
    for phase, run in (('preflight', 'pi-r3-preflight'), ('docs', 'pi-r3-docs')):
        r = read(run + '/record.json')
        assert r['status'] == 'finished' and r['exit_code'] == 0
        assert r['argv'] == ['.venv/bin/python', 'reports/T0015/check_rework_r3.py', phase, run]
        assert r['before']['source_sha256'] == r['after']['source_sha256']
        for rel, h in r['before']['source_sha256'].items():
            assert sha(ROOT / rel) == h, rel
        for stream in ('stdout', 'stderr'):
            assert sha(TASK / run / (stream + '.txt')) == r[stream + '_sha256']
        assert not (TASK / run / 'stderr.txt').read_bytes()
        runs.append({'run': run, 'started_at_utc': r['started_at_utc'], 'exit_code': r['exit_code']})
    assert runs[0]['started_at_utc'] < runs[1]['started_at_utc']
    pi_records = list(TASK.glob('pi-*/record.json'))
    index = read('pi-r3-docs/run-index.json')
    expected_runs = {p.parent.name for p in pi_records} - {'pi-r3-docs'}
    assert {r['run'] for r in index['completed_recorded_runs']} == expected_runs
    for row in index['completed_recorded_runs']:
        record = read(row['run'] + '/record.json')
        assert all(row[k] == record[k] for k in ('started_at_utc', 'exit_code', 'argv'))
    assert index['current_excluded'] == 'pi-r3-docs'
    assert index['visibility_restored'] == hidden
    assert not (TASK / 'pi-r2-preflight').exists()
    assert not (TASK / 'pi-r1-r2guards/record.json').exists()
    provenance = TASK / 'pi-r3/provenance.md'
    assert list(TASK.glob('pi-r3*/provenance.md')) == [provenance]
    links = check_docs('awaiting_review', [*(ROOT / p for p in DOCS), provenance])
    out = TASK / 'review-r3-evidence'
    frozen = {}
    for path in [*(ROOT / p for p in DOCS), provenance]:
        rel = path.relative_to(ROOT)
        copy = out / 'input-snapshot' / rel
        copy.parent.mkdir(parents=True, exist_ok=True)
        with copy.open('xb') as handle:
            handle.write(path.read_bytes())
        frozen[rel.as_posix()] = sha(path)
    pi_files = {p.relative_to(ROOT).as_posix(): sha(p) for p in TASK.glob('pi-r3*/*') if p.is_file()}
    result = {
        'result': 'PASS', 'baseline_files': len(baseline['files']),
        'unchanged_frozen_files': len(baseline['files']) - len(allowed_changes),
        'restored_visible_files': 26, 'raw_artifacts_unchanged': 24,
        'ignore_files_append_only': 2, 'pi_r3_runs': runs,
        'indexed_prior_pi_runs': len(expected_runs), 'total_completed_pi_runs': len(pi_records),
        'source_sha256': {p: baseline['files'][p] for p in ('src/kmesh/logic/proof_subtree.py', 'tests/test_proof_subtree.py')},
        'submitted_document_sha256': frozen, 'pi_r3_files_sha256': pi_files,
        'links_checked': links, 'product_tests_executed_this_round': False,
        'editorial_clarifications': ['14 prior records indexed, 15 including current docs; 13 was the R2 cutoff',
            '26 visible = 24 unchanged artifacts + 2 append-only ignore files',
            '17 independent tests belong to Codex R2, not the Pi R3 provenance; prefill means preflight'],
        'historical_limits': ['R2 preflight unrecorded', 'omitted guards outer record absent',
            'R2 regression followed a passing fixed-source full', 'historical model attribution unknown'],
    }
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'PASS: {result["unchanged_frozen_files"]} frozen files; 26 visible, 24 raw unchanged, 2 append-only; two R3 RUNs valid; index {len(expected_runs)}, total {len(pi_records)}; no product execution')


def close():
    audit_result = read('review-r3-evidence/result.json')
    assert audit_result['result'] == 'PASS'
    for rel, h in audit_result['source_sha256'].items():
        assert sha(ROOT / rel) == h
    for rel, h in audit_result['pi_r3_files_sha256'].items():
        assert sha(ROOT / rel) == h
    report = TASK / 'review-r3/review.md'
    links = check_docs('accepted', [*(ROOT / p for p in DOCS), report])
    handoff = (ROOT / DOCS[2]).read_text()
    assert all(f'- [x] **A{i} ' in handoff for i in range(1, 8))
    result = {
        'result': 'PASS', 'task_status': 'accepted', 'review_date': '2026-09-26',
        'head': git('rev-parse', 'HEAD').strip(), 'source_sha256': audit_result['source_sha256'],
        'E1': 'closed', 'E2': 'closed with explicit historical limits and Codex editorial clarification',
        'evidence_audit': '../review-r3-evidence/result.json',
        'reused_verification': {'codex_r2_tests': 17, 'codex_r2_mutants': 4, 'codex_r2_outputs': 15, 'pi_full_verified': 934},
        'tests_run_this_round': False, 'codinator_run_this_round': False,
        'historical_limits': audit_result['historical_limits'],
        'document_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in [*(ROOT / r for r in DOCS), report]},
        'links_checked': links,
    }
    (TASK / 'review-r3/final-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'PASS: T0015 accepted, E1/E2 closed, code/Pi evidence unchanged, {links} links, no tests/models/commit/push')


if __name__ == '__main__':
    {'audit': audit, 'close': close}[sys.argv[1]]()
