"""Close Codex R2 evidence review and export the next handoff's frozen baseline."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
DOCS = ('README.md', 'docs/implementation_status.md', 'docs/handoffs/T0015-proof-subtree.md')
SCRATCH = {'pytest-tmp', '__pycache__'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(rel):
    return json.loads((TASK / rel).read_text())


def visible():
    raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    return set(raw.decode().split('\0')) - {''}


def export_baseline():
    """Metadata export; refresh once after the enclosing recorder has finished."""
    inventory = read('review-r2-evidence3/result.json')['artifact_inventory']
    paths = visible() | {
        p.relative_to(ROOT).as_posix() for p in TASK.rglob('*')
        if p.is_file() and not SCRATCH.intersection(p.relative_to(TASK).parts)
    }
    target = TASK / 'rework-r3-baseline.json'
    paths.discard(target.relative_to(ROOT).as_posix())
    data = {
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
        'files': {rel: sha(ROOT / rel) for rel in sorted(paths)},
        'ignore_original': {rel: (ROOT / rel).read_text() for rel in inventory if rel.endswith('/.gitignore')},
        'previously_hidden_artifacts': sorted(inventory),
        'note': 'Current R3 handoff baseline, including actual ignored evidence; not a historical Pi preflight. Mutable docs and the two append-only ignore exceptions are defined by check_rework_r3.py.',
    }
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    probe = read('review-r2-probe/result.json')
    assert probe['result'] == 'PASS'
    source_hashes = {p: h for p, h in probe['frozen_sha256'].items() if p.startswith(('src/', 'tests/'))}
    for rel, h in source_hashes.items():
        assert sha(ROOT / rel) == h, rel
    frozen = read('rework-r2-baseline.json')['files']
    for rel, h in frozen.items():
        assert sha(ROOT / rel) == h, rel
    audit = read('review-r2-evidence/result.json')
    for run in audit['completed_pi_runs']:
        directory = TASK / run['run']
        assert sha(directory / 'record.json') == run['record_sha256']
        record = json.loads((directory / 'record.json').read_text())
        for stream in ('stdout', 'stderr'):
            assert sha(directory / (stream + '.txt')) == record[stream + '_sha256']
    guards = read('review-r2-guards/guards.json')
    assert guards['all_guards_valid'] and len(guards['cases']) == 5
    assert read('review-r2-focused/record.json')['exit_code'] == 0
    assert '17 passed' in (TASK / 'review-r2-focused/stdout.txt').read_text()
    assert read('review-r2-evidence2/record.json')['exit_code'] == 1
    assert read('review-r2-evidence3/record.json')['exit_code'] == 0
    inventory = read('review-r2-evidence3/result.json')['artifact_inventory']
    archive = {}
    for rel, item in inventory.items():
        source = ROOT / rel
        assert sha(source) == item['sha256'], rel
        suffix = source.relative_to(TASK)
        destination = TASK / 'review-r2/hidden-evidence-snapshot' / suffix
        if destination.name == '.gitignore':
            destination = destination.with_name('.gitignore.txt')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as handle:
            handle.write(source.read_bytes())
        archive[rel] = {'copy': destination.relative_to(ROOT).as_posix(), 'sha256': sha(destination)}
    assert len(archive) == 26
    git_visible = visible()
    assert all(item['copy'] in git_visible for item in archive.values())
    (TASK / 'review-r2/hidden-evidence-manifest.json').write_text(json.dumps(archive, indent=2) + '\n')
    ast.parse((TASK / 'check_rework_r3.py').read_text())
    export_baseline()
    docs = [*(ROOT / rel for rel in DOCS), TASK / 'review-r2/review.md']
    links = 0
    for path in docs:
        text = path.read_text()
        assert text.endswith('\n') and all(line == line.rstrip() for line in text.splitlines()), path
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            url = urlsplit(target.strip().strip('<>'))
            if not url.scheme and not url.netloc and url.path:
                assert (path.parent / unquote(url.path)).exists(), (path, target)
                links += 1
    handoff = (ROOT / DOCS[2]).read_text()
    assert '- 状态：`needs_changes`' in handoff and 'T0015 / r3' in handoff
    status = (ROOT / DOCS[1]).read_text()
    assert 'needs_changes' in next(s for s in status.splitlines() if s.startswith('- T0015'))
    assert 'needs_changes' in next(s for s in status.splitlines() if s.startswith('| 完整有根证明子树抽取 |'))
    assert 'needs_changes' in (ROOT / DOCS[0]).read_text().split('## 完整证明子树（T0015', 1)[1]
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    final = {
        'result': 'needs_changes', 'task_status': 'needs_changes',
        'product_and_tests': 'PASS; frozen', 'source_sha256': source_hashes,
        'independent_focused': 17, 'independent_mutants_rejected': 4,
        'independent_output_probes': 15, 'independent_full': 'not_run',
        'pi_full_verified': {'runs': ['pi-r1-r2full', 'pi-r2-full'], 'passed_each': 934},
        'prior_r2_frozen_files_unchanged': len(frozen),
        'verified_completed_pi_outer_records': len(audit['completed_pi_runs']),
        'visible_archived_artifacts': len(archive), 'local_links_checked': links,
        'open_items': ['E1: restore original evidence Git visibility', 'E2: append accurate chronology and source attribution'],
        'codex_helper_failure': 'review-r2-evidence2 miscounted 26 as 27; retained, corrected in new evidence3 RUN',
        'next_round': 'manual Pi + authorized bonsai2-27b, evidence only; no product/tests/full/models/Codinator',
    }
    (TASK / 'review-r2/final-audit.json').write_text(json.dumps(final, ensure_ascii=False, indent=2) + '\n')
    print(f'PASS: review closure; code/tests passed, E1/E2 remain; {len(frozen)} frozen files, 26 visible archive copies, {links} local links. R3 baseline metadata is finalized after the recorder exits.')


if __name__ == '__main__':
    main()
