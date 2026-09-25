"""Bounded copies exposing four remaining R3 contract gaps; never edit product."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('out')
parser.add_argument('--enforce', action='store_true')
args = parser.parse_args()
OUT = ROOT / args.out
assert OUT.is_dir() and not (OUT / 'guards.json').exists()
source = (ROOT / 'src/kmesh/logic/motif.py').read_text()
test = (ROOT / 'tests/test_motif.py').read_text()


def change(before, after):
    assert source.count(before) == 1
    return source.replace(before, after, 1)


call = '    key, stream = canonical_proof_key(\n        clauses, query, proof, max_steps=max_steps\n    )'
cases = {
    'submitted': source,
    'format_unvalidated_integer': change('    orientations = max_orientations',
        '    orientations = max_orientations\n'
        '    if type(orientations) is int:\n        str(orientations)'),
    'logic_error_loses_to_invalid_O': change(call,
        '    try:\n        key, stream = canonical_proof_key(clauses, query, proof, max_steps=max_steps)\n'
        '    except LogicValidationError:\n'
        '        if type(max_orientations) is not int or max_orientations <= 0:\n'
        '            raise LogicValidationError("motif.max_orientations must be a non-bool positive integer; "\n'
        '                                       f"got {type(max_orientations).__name__}")\n'
        '        raise'),
    # Incorrectly count only structurally equal twin subtrees at a repeated root.
    'underbudget_distinct_twins': change('    B = b',
        '    B = b\n'
        '    if B == 3 and stream[0][1][2][0] == stream[0][1][2][1]:\n'
        '        a, z = children[0]\n'
        '        if tuple(stream[c][0] for c in children[a]) != tuple(stream[c][0] for c in children[z]):\n'
        '            B -= 1'),
    'header_tuple_subclass': change('            out.append((ground_enc, head_enc, tuple(body_enc)))',
        '            class Header(tuple):\n                pass\n'
        '            out.append(Header((ground_enc, head_enc, tuple(body_enc))))'),
}
rows = []
for name, src in cases.items():
    case = OUT / 'pytest-tmp' / name
    case.mkdir(parents=True)
    shutil.copytree(ROOT / 'src/kmesh', case / 'src/kmesh', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (case / 'tests').mkdir()
    (case / 'src/kmesh/logic/motif.py').write_text(src)
    (case / 'tests/test_motif.py').write_text(test)
    (OUT / (name + '.source.py')).write_text(src)
    cmd = [sys.executable, '-m', 'pytest', '-q', str(case / 'tests/test_motif.py'), '--basetemp', str(case / 'temp')]
    env = os.environ | {'PYTHONPATH': str(case / 'src'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'CUDA_VISIBLE_DEVICES': ''}
    r = subprocess.run(cmd, cwd=case, env=env, capture_output=True, timeout=20)
    (OUT / (name + '.stdout.txt')).write_bytes(r.stdout)
    (OUT / (name + '.stderr.txt')).write_bytes(r.stderr)
    rows.append(dict(name=name, argv=cmd, exit_code=r.returncode,
                     source_sha256=hashlib.sha256(src.encode()).hexdigest(),
                     guard_valid=r.returncode == (0 if name == 'submitted' else 1)))
result = dict(test_sha256=hashlib.sha256(test.encode()).hexdigest(), runs=rows,
              all_guards_valid=all(r['guard_valid'] for r in rows))
(OUT / 'guards.json').write_text(json.dumps(result, indent=2) + '\n')
for r in rows:
    print(f'{r["name"]}: exit={r["exit_code"]}, guard_valid={r["guard_valid"]}')
if args.enforce and not result['all_guards_valid']:
    raise SystemExit(1)
