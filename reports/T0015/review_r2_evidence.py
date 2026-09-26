"""Read-only evidence/scope audit for T0015 R2; run using the frozen recorder."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
OUT = TASK / 'review-r2-evidence'
PRODUCT = 'src/kmesh/logic/proof_subtree.py'
TEST = 'tests/test_proof_subtree.py'
MUTABLE = {PRODUCT, TEST, 'README.md', 'docs/implementation_status.md',
           'docs/handoffs/T0015-proof-subtree.md'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    p = subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True)
    return dict(argv=['git', *args], exit_code=p.returncode,
                stdout=p.stdout, stderr=p.stderr)


def frozen_check(manifest):
    return dict(count=len(manifest), mismatches=[p for p, digest in manifest.items()
        if not (ROOT / p).is_file() or sha(ROOT / p) != digest])


baseline = json.loads((TASK / 'rework-r2-baseline.json').read_text())
planning = json.loads((TASK / 'planning-files.json').read_text())
result = dict(kind='independent read-only evidence audit; not a product verdict',
              planning_frozen=frozen_check(planning),
              r2_frozen=frozen_check(baseline['files']),
              current_source_sha256={p: sha(ROOT / p) for p in (PRODUCT, TEST)},
              head=git('rev-parse', 'HEAD'), branch=git('branch', '--show-current'))
records = []
for path in TASK.glob('pi-*/record.json'):
    record = json.loads(path.read_text())
    stream_matches = {s: sha(path.parent / (s + '.txt')) == record[s + '_sha256']
                      for s in ('stdout', 'stderr')}
    before = record['before']['source_sha256']
    after = record['after']['source_sha256']
    records.append(dict(run=path.parent.name, record_sha256=sha(path),
        started_at_utc=record['started_at_utc'], finished_at_utc=record['finished_at_utc'],
        status=record['status'], exit_code=record['exit_code'], argv=record['argv'],
        source_sha256={p: before[p] for p in (PRODUCT, TEST)},
        all_sources_stable=before == after, stream_hash_matches=stream_matches,
        older_sources_current=all(digest == sha(ROOT / p)
            for p, digest in before.items() if p not in (PRODUCT, TEST)),
        stdout_last_lines=(path.parent / 'stdout.txt').read_text().splitlines()[-3:],
        stderr_bytes=(path.parent / 'stderr.txt').stat().st_size))
records.sort(key=lambda item: item['started_at_utc'])
result['completed_pi_runs'] = records
result['r2_preflight_records'] = [item['run'] for item in records
    if 'reports/T0015/check_rework_r2.py' in item['argv'] and 'preflight' in item['argv']]
result['r2_preflight_directory_exists'] = (TASK / 'pi-r2-preflight').exists()
result['pi_directories_without_record'] = sorted(p.name for p in TASK.glob('pi-*')
    if p.is_dir() and not (p / 'record.json').exists())
result['r2_or_omitted_full_runs'] = [r for r in records
    if r['run'].startswith('pi-r2') or r['run'] == 'pi-r1-r2full']

guards = json.loads((TASK / 'pi-r2-guards/guards.json').read_text())
result['guards'] = dict(all_guards_valid=guards['all_guards_valid'], cases={})
for name, case in guards['cases'].items():
    folder = TASK / 'pi-r2-guards' / name
    result['guards']['cases'][name] = dict(exit_code=case['exit_code'],
        target=case['target'], guard_valid=case['guard_valid'],
        stream_hash_matches={s: sha(folder / (s + '.txt')) == case[s + '_sha256']
                             for s in ('stdout', 'stderr')},
        stdout_last_lines=(folder / 'stdout.txt').read_text().splitlines()[-3:])

ls = git('ls-files', '--cached', '--others', '--exclude-standard', '-z')
assert ls['exit_code'] == 0, ls
visible = set(ls['stdout'].split('\0')) - {''}
def authorized(path):
    return (path in baseline['files'] or path in MUTABLE
            or path == 'reports/T0015/rework-r2-baseline.json'
            or path.startswith('reports/T0015/pi-r2')
            or path.startswith('reports/T0015/review-r2')
            or path.startswith('reports/T0015/review_r2'))

result['visible_scope_exceptions'] = sorted(p for p in visible if not authorized(p))
actual = {str(p.relative_to(ROOT)) for p in TASK.rglob('*')
          if p.is_file() and not {'pytest-tmp', '__pycache__', '.pytest_cache'}.intersection(p.parts)}
result['actual_task_scope_exceptions'] = sorted(p for p in actual if not authorized(p))
omitted = TASK / 'pi-r1-r2full'
result['omitted_full_evidence'] = {
    p.name: dict(sha256=sha(p), git_visible=str(p.relative_to(ROOT)) in visible)
    for p in omitted.iterdir() if p.is_file()}
result['omitted_full_ignore_rules'] = (omitted / '.gitignore').read_text().splitlines()
result['omitted_full_check_ignore'] = git('check-ignore', '-v',
    'reports/T0015/pi-r1-r2full/.gitignore', 'reports/T0015/pi-r1-r2full/record.json',
    'reports/T0015/pi-r1-r2full/stdout.txt', 'reports/T0015/pi-r1-r2full/stderr.txt')
index = json.loads((TASK / 'pi-r2-docs/run-index.json').read_text())
result['docs_index_runs'] = [r['run'] for r in index['runs']]
result['docs_index_current_source_sha256'] = index['current_source_sha256']
result['doc_sha256'] = {p: sha(ROOT / p) for p in
    ('README.md', 'docs/implementation_status.md', 'docs/handoffs/T0015-proof-subtree.md',
     'reports/T0015/pi-r2/provenance.md', 'reports/T0015/check_rework_r2.py')}

result['findings'] = [
    'No R2 preflight record/directory; pre-coding R2 check is not established.',
    'Final R2 sources already pass 934 in pi-r1-r2full before regression on restored R1 product; test-first history is not established.',
    'Two complete 934-test R2-source runs exist; provenance and README claim only one and omit pi-r1-r2full.',
    'pi-r1-r2full/.gitignore excludes itself and all three evidence files, bypassing git-visible scope checks and normal evidence staging.',
    'Pi 17-test results are called independent in README/status/provenance before Codex R2 review; source attribution needs correction.',
    'Actual model remains unknown: provenance reports Qwen while handoff requires authorized bonsai2; no independent configuration source or advance mismatch feedback.',
    '3167 is the R2 frozen inventory size, while the original planning frozen inventory is 3088; provenance conflates the labels.',
]
result['interpretation_limits'] = [
    'Stable matching source/stream hashes validate the retained test outcomes; chronology defects do not imply an API defect.',
    'Absence of a recorded preflight does not prove no unrecorded command ran; that history is unknown.',
    'Regression is a real reproduced failure under R1 product bytes, but was recorded after a final-source passing full run.',
    'Ignored evidence is currently readable and hash-consistent; this audit does not infer why the ignore file was added.',
    'The recorder does not independently capture the running model or all filesystem changes.',
]

assert not result['planning_frozen']['mismatches'], result['planning_frozen']
assert not result['r2_frozen']['mismatches'], result['r2_frozen']
assert all(r['status'] == 'finished' and r['all_sources_stable']
           and r['older_sources_current'] and all(r['stream_hash_matches'].values())
           for r in records), 'retained record/source integrity mismatch'
assert all(all(c['stream_hash_matches'].values())
           for c in result['guards']['cases'].values()), 'guard stream mismatch'
(OUT / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('PASS retained integrity: planning=%d, R2=%d frozen files; %d Pi records; all streams/source snapshots consistent'
      % (len(planning), len(baseline['files']), len(records)))
for r in result['r2_or_omitted_full_runs']:
    print(r['started_at_utc'], r['run'], 'exit=' + str(r['exit_code']),
          'product=' + r['source_sha256'][PRODUCT][:12],
          'test=' + r['source_sha256'][TEST][:12])
print('R2 preflight records:', result['r2_preflight_records'])
print('Actual task scope exceptions:', result['actual_task_scope_exceptions'])
print('Reporting/process findings: %d; see result.json. Audit exit=0 does not mean task acceptance.' % len(result['findings']))
