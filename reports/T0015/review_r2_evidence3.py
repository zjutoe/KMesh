"""Audit and preserve ignored T0015 evidence; no original files are changed."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
OUT = TASK / 'review-r2-evidence3'
PRODUCT = 'src/kmesh/logic/proof_subtree.py'
TEST = 'tests/test_proof_subtree.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


baseline = json.loads((TASK / 'rework-r2-baseline.json').read_text())['files']
visible = set(subprocess.check_output(
    ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
    cwd=ROOT, text=True).split('\0')) - {''}
result = dict(kind='supplementary read-only audit of omitted original artifacts',
              current_source_sha256={p: sha(ROOT / p) for p in (PRODUCT, TEST)},
              artifact_inventory={}, guards={}, full={})
artifacts = []
for name in ('pi-r1-r2full', 'pi-r1-r2guards'):
    folder = TASK / name
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or {'pytest-tmp', '__pycache__', '.pytest_cache'}.intersection(path.parts):
            continue
        relative = str(path.relative_to(ROOT))
        destination = OUT / 'input-snapshot' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        assert not destination.exists(), destination
        shutil.copyfile(path, destination)
        assert sha(destination) == sha(path), path
        result['artifact_inventory'][relative] = dict(sha256=sha(path),
            bytes=path.stat().st_size, present_in_r2_baseline=relative in baseline,
            git_visible=relative in visible,
            preserved_copy=str(destination.relative_to(ROOT)))
        artifacts.append(relative)

ignored = subprocess.run(['git', 'check-ignore', '-v', *artifacts],
                         cwd=ROOT, text=True, capture_output=True)
result['git_check_ignore'] = dict(exit_code=ignored.returncode,
                                stdout=ignored.stdout, stderr=ignored.stderr)
for name in ('pi-r1-r2full', 'pi-r1-r2guards'):
    result[name + '_ignore_rules'] = (TASK / name / '.gitignore').read_text().splitlines()

outer = TASK / 'pi-r1-r2guards'
report = json.loads((outer / 'guards.json').read_text())
result['guards']['outer_record_exists'] = (outer / 'record.json').exists()
result['guards']['outer_stdout_exists'] = (outer / 'stdout.txt').exists()
result['guards']['outer_stderr_exists'] = (outer / 'stderr.txt').exists()
result['guards']['all_guards_valid'] = report['all_guards_valid']
result['guards']['cases'] = {}
for name, row in report['cases'].items():
    folder = outer / name
    inner = json.loads((folder / 'result.json').read_text())
    workspace = Path(row['cwd'])
    result['guards']['cases'][name] = dict(
        result_json_matches_summary=inner == row, exit_code=row['exit_code'],
        target=row['target'], guard_valid=row['guard_valid'],
        product_snapshot_sha256=sha(folder / 'product.py.txt'),
        product_snapshot_matches=sha(folder / 'product.py.txt') == row['product_sha256'],
        product_copy_exists=(workspace / PRODUCT).is_file(),
        product_copy_matches=(workspace / PRODUCT).is_file() and sha(workspace / PRODUCT) == row['product_sha256'],
        test_copy_exists=(workspace / TEST).is_file(),
        test_copy_matches=(workspace / TEST).is_file() and sha(workspace / TEST) == row['test_sha256'],
        test_matches_current=row['test_sha256'] == sha(ROOT / TEST),
        streams_match={s: sha(folder / (s + '.txt')) == row[s + '_sha256']
                       for s in ('stdout', 'stderr')},
        stdout_last_lines=(folder / 'stdout.txt').read_text().splitlines()[-3:])

full_dir = TASK / 'pi-r1-r2full'
full = json.loads((full_dir / 'record.json').read_text())
regression = json.loads((TASK / 'pi-r2-regression/record.json').read_text())
later_full = json.loads((TASK / 'pi-r2-full/record.json').read_text())
result['full'] = dict(started_at_utc=full['started_at_utc'],
    finished_at_utc=full['finished_at_utc'], exit_code=full['exit_code'],
    streams_match={s: sha(full_dir / (s + '.txt')) == full[s + '_sha256']
                   for s in ('stdout', 'stderr')},
    all_before_after_sources_same=full['before']['source_sha256'] == full['after']['source_sha256'],
    all_sources_match_later_full=full['before']['source_sha256'] == later_full['before']['source_sha256'],
    all_sources_match_current=all(sha(ROOT / p) == d for p,d in full['before']['source_sha256'].items()),
    finished_before_regression=full['finished_at_utc'] < regression['started_at_utc'],
    regression_started_at_utc=regression['started_at_utc'],
    regression_product_sha256=regression['before']['source_sha256'][PRODUCT],
    later_full_started_at_utc=later_full['started_at_utc'],
    stdout_last_lines=(full_dir / 'stdout.txt').read_text().splitlines()[-3:])
result['conclusions'] = [
    '26 non-scratch original artifacts across two omitted directories are absent from R2 frozen baseline and excluded by their local .gitignore files.',
    'Original bytes are preserved in input-snapshot; this audit did not change visibility or any original artifact.',
    'The omitted full RUN is complete, has consistent stream/source hashes, and ran final R2 source/test bytes before the restored-R1 regression.',
    'The omitted guards directory has valid matching inner summaries/product/test copies/streams and all four targets rejected, but no outer recorder record/stdout/stderr.',
    'Omitted-guards precise start time, recorder launch, environment, and operator/model cannot be established from these artifacts; no chronology is inferred from mtime.',
    'Ignored artifacts bypass the git-visible scope checker and would be absent from ordinary staging; this is an evidence/scope closure defect, not evidence of an API failure.',
]
assert len(artifacts) == 26, artifacts
assert all(not row['present_in_r2_baseline'] and not row['git_visible']
           for row in result['artifact_inventory'].values())
assert ignored.returncode == 0 and len(ignored.stdout.splitlines()) == len(artifacts)
for case in result['guards']['cases'].values():
    assert case['result_json_matches_summary'] and case['product_snapshot_matches']
    assert case['product_copy_matches'] and case['test_copy_matches'] and case['test_matches_current']
    assert all(case['streams_match'].values()) and case['guard_valid']
assert all(result['full']['streams_match'].values())
assert result['full']['all_before_after_sources_same'] and result['full']['all_sources_match_later_full']
assert result['full']['all_sources_match_current'] and result['full']['finished_before_regression']
(OUT / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('PASS: 26 ignored non-scratch artifacts inventoried and preserved; all absent from baseline/git-visible scope.')
print('PASS: omitted full record and all 5 inner guard cases have consistent source/test/stream hashes.')
print('LIMIT: omitted guards has no outer record/stdout/stderr; exact chronology and actor/model remain unknown.')
print('Recorded versions: final R2 full 14:21:52 -> restored R1 regression 14:31:24 -> final R2 full 14:32:18 UTC.')
print('Evidence visibility/reporting is incomplete; audit exit=0 does not mean task acceptance.')
