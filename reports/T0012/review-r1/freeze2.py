"""Codex review input freeze; run once through the immutable recorder."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'reports/T0012/review-r1-freeze2'
MUTABLE = ('src/kmesh/logic/proof_key.py', 'tests/test_proof_key.py',
           'README.md', 'docs/implementation_status.md', 'docs/handoffs/T0012-proof-key.md')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def main():
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    manifest = {n: sha(ROOT / n) for n in sorted(set(names)) if n and not n.startswith('reports/T0012/review-r1')}
    write('input-manifest.json', manifest)
    for n in MUTABLE:
        dest = OUT / 'input-snapshot' / n
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / n).read_bytes())
    frozen = json.loads((ROOT / 'reports/T0012/planning-files.json').read_text())
    differences = [n for n, digest in frozen.items() if manifest.get(n) != digest]
    planned = json.loads((ROOT / 'reports/T0012/planning-baseline.json').read_text())
    ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', planned['head'], 'HEAD'], cwd=ROOT).returncode
    rows = []
    for p in (ROOT / 'reports/T0012').glob('pi-*/record.json'):
        r = json.loads(p.read_text())
        for stream in ('stdout', 'stderr'):
            assert sha(p.parent / (stream + '.txt')) == r[stream + '_sha256']
        rows.append({k: r[k] for k in ('argv', 'started_at_utc', 'finished_at_utc', 'elapsed_s', 'exit_code')} | {
            'run': p.parent.name, 'before': {n: r['before']['source_sha256'][n] for n in MUTABLE[:2]},
            'after': {n: r['after']['source_sha256'][n] for n in MUTABLE[:2]},
            'stdout': (p.parent / 'stdout.txt').read_text(), 'stderr': (p.parent / 'stderr.txt').read_text()})
    rows.sort(key=lambda r: r['started_at_utc'])
    result = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  branch=subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
                  input_sha256={n: manifest[n] for n in MUTABLE}, frozen_count=len(frozen),
                  frozen_differences=differences, planned_head_is_ancestor=ancestor == 0, pi_runs=rows)
    previous_test_sha = rows[1]['before']['tests/test_proof_key.py']
    submitted = (ROOT / MUTABLE[1]).read_bytes()
    result['test_without_last_newline_sha256'] = hashlib.sha256(submitted[:-1]).hexdigest()
    result['previous_test_sha256'] = previous_test_sha
    write('input-audit.json', result)
    assert not differences and ancestor == 0
    print(f'PASS: {len(frozen)} planning files unchanged; {len(manifest)} input files frozen; {len(rows)} Pi RUN streams authenticated')
    for r in rows:
        print(r['run'], r['exit_code'], r['started_at_utc'])

if __name__ == '__main__':
    main()
