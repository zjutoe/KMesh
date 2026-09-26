"""T0015 R3 evidence-only preflight/docs checks; never run product tests."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
BASELINE = TASK / 'rework-r3-baseline.json'
DOCS = ('README.md', 'docs/implementation_status.md', 'docs/handoffs/T0015-proof-subtree.md')
IGNORE = ('reports/T0015/pi-r1-r2full/.gitignore', 'reports/T0015/pi-r1-r2guards/.gitignore')
SCRATCH = {'pytest-tmp', '__pycache__'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def visible_files():
    raw = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'], cwd=ROOT)
    return set(raw.decode().split('\0')) - {''}


def actual_evidence_files():
    return {p.relative_to(ROOT).as_posix() for p in TASK.rglob('*')
            if p.is_file() and not SCRATCH.intersection(p.relative_to(TASK).parts)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('preflight','docs'))
    parser.add_argument('run')
    args = parser.parse_args()
    assert re.fullmatch(r'pi-r3[a-z0-9_-]*',args.run)
    out = TASK / args.run
    assert out.is_dir()
    base = json.loads(BASELINE.read_text())
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() == base['head']
    assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip() == base['branch']
    for rel,h in base['files'].items():
        if rel in DOCS or (args.phase == 'docs' and rel in IGNORE):
            continue
        assert (ROOT/rel).is_file() and sha(ROOT/rel) == h, f'frozen changed/missing: {rel}'
    visible = visible_files()
    for rel in visible | actual_evidence_files():
        assert rel in base['files'] or rel == BASELINE.relative_to(ROOT).as_posix() or rel.startswith('reports/T0015/pi-r3'), f'outside scope: {rel}'
    expected_state = 'in_progress' if args.phase == 'preflight' else 'awaiting_review'
    handoff = (ROOT/DOCS[2]).read_text()
    status = (ROOT/DOCS[1]).read_text()
    assert f'- 状态：`{expected_state}`' in handoff
    assert expected_state in next(s for s in status.splitlines() if s.startswith('- T0015'))
    if args.phase == 'preflight':
        print('PASS: HEAD/branch, frozen product/tests/history, actual evidence scope, original ignore files, in_progress')
        return
    for rel in IGNORE:
        original = base['ignore_original'][rel]
        expected = original + ''.join('!' + line + '\n' for line in original.splitlines())
        assert (ROOT/rel).read_text() == expected, f'only append the specified unignore rules: {rel}'
    for rel in base['previously_hidden_artifacts']:
        assert rel in visible, f'evidence still invisible to Git: {rel}'
    provenance = TASK / 'pi-r3/provenance.md'
    assert sorted(TASK.glob('pi-r3*/provenance.md')) == [provenance]
    text = provenance.read_text()
    for key in ('E1','E2','pi-r1-r2full','pi-r1-r2guards','pi-r2-regression','preflight','unknown','bonsai2-27b'):
        assert key in text, f'missing correction topic: {key}'
    assert '../../reports/T0015/pi-r3/provenance.md' in handoff
    assert expected_state in next(s for s in status.splitlines() if s.startswith('| 完整有根证明子树抽取 |'))
    section = (ROOT/DOCS[0]).read_text().split('## 完整证明子树（T0015',1)[1]
    assert expected_state in section
    rows = []
    for rec in TASK.glob('pi-*/record.json'):
        if rec.parent == out:
            continue
        r = json.loads(rec.read_text())
        assert r['status'] == 'finished'
        for stream in ('stdout','stderr'):
            assert sha(rec.parent/(stream+'.txt')) == r[stream+'_sha256'],rec
        rows.append({'run':rec.parent.name,'started_at_utc':r['started_at_utc'],
                     'exit_code':r['exit_code'],'argv':r['argv']})
    rows.sort(key=lambda r:r['started_at_utc'])
    # Missing historical records remain missing: list them, never synthesize one.
    orphans = [p.name for p in sorted(TASK.glob('pi-*')) if p.is_dir() and not (p/'record.json').exists()]
    (out/'run-index.json').write_text(json.dumps({'completed_recorded_runs':rows,
        'current_excluded':args.run,'directories_without_outer_record':orphans,
        'visibility_restored':base['previously_hidden_artifacts']},indent=2)+'\n')
    links = 0
    for path in [*(ROOT/p for p in DOCS),provenance,*(ROOT/p for p in IGNORE)]:
        content = path.read_text()
        assert content.endswith('\n') and all(s == s.rstrip() for s in content.splitlines()),path
        if path.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',content):
                u = urlsplit(target.strip().strip('<>'))
                if not u.scheme and not u.netloc and u.path:
                    assert (path.parent/unquote(u.path)).exists(),(path,target)
                    links += 1
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    print(f'PASS: frozen code/history, real scope, {len(base["previously_hidden_artifacts"])} restored artifacts, states, correction topics, {links} links; no tests/models invoked')


if __name__ == '__main__':
    main()
