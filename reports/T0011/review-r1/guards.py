"""Run submitted tests against isolated product mutants; never edit the workspace.

Usage: guards.py RECORDER_RUN_DIRECTORY [--enforce]
Without --enforce, record detection gaps. With it, every mutant must be rejected.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
PRODUCT = 'src/kmesh/logic/clause_key.py'
TEST = 'tests/test_clause_key.py'
MUTANTS = {
    'diagnostic_suffix': ('got {type(clause).__name__}"', 'got {type(clause).__name__} EXTRA"'),
    'float_variable_number': ('return ("v", number)', 'return ("v", float(number))'),
    'conditional_reverse': ('if len(body) == 2:', 'if len(body) == 2 and body[0].pred <= body[1].pred:'),
    'no_reverse': ('if len(body) == 2:', 'if False:'),
    'drop_duplicate_premises': ('body = clause.body', 'body = tuple(dict.fromkeys(clause.body))'),
}


def main():
    out = Path(sys.argv[1]).resolve()
    enforce = sys.argv[2:] == ['--enforce']
    source = (ROOT / PRODUCT).read_text()
    rows = []
    for name, replacement in [('submitted', None), *MUTANTS.items()]:
        changed = source
        if replacement:
            old, new = replacement
            assert source.count(old) == 1, name
            changed = source.replace(old, new)
        work = out / 'pytest-tmp' / name
        shutil.copytree(ROOT / 'src/kmesh', work / 'src/kmesh', ignore=shutil.ignore_patterns('__pycache__'))
        (work / 'tests').mkdir()
        shutil.copyfile(ROOT / TEST, work / TEST)
        (work / PRODUCT).write_text(changed)
        command = [sys.executable, '-m', 'pytest', '-q', TEST, '--basetemp', str(work / 'scratch')]
        proc = subprocess.run(command, cwd=work, env=os.environ | {'PYTHONPATH': str(work / 'src'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'CUDA_VISIBLE_DEVICES': ''}, capture_output=True, timeout=30)
        (out / (name + '.stdout')).write_bytes(proc.stdout)
        (out / (name + '.stderr')).write_bytes(proc.stderr)
        (out / (name + '.diff.json')).write_text(json.dumps(dict(replacement=replacement, sha256=hashlib.sha256(changed.encode()).hexdigest()), indent=2) + '\n')
        rows.append(dict(name=name, argv=command, exit_code=proc.returncode, detected=proc.returncode == 1 if replacement else None))
    assert rows[0]['exit_code'] == 0, 'submitted test control failed'
    assert all(row['exit_code'] in (0, 1) for row in rows), 'mutation run failed outside test assertions'
    result = dict(mode='enforce' if enforce else 'inspect', product_sha256=hashlib.sha256(source.encode()).hexdigest(), test_sha256=hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest(), cases=rows)
    (out / 'guards.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if enforce:
        assert all(row['detected'] for row in rows[1:]), 'a contract violation survived'


if __name__ == '__main__':
    main()
