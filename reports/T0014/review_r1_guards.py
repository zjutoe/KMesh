"""Bounded Codex mutation checks, isolated copies only. Optional --enforce for rework."""
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
out = ROOT / args.out
assert out.is_dir() and not (out / 'guards.json').exists()
original = (ROOT / 'src/kmesh/logic/motif.py').read_text()
test = (ROOT / 'tests/test_motif.py').read_text()
assert hashlib.sha256(original.encode()).hexdigest() == '23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f'


def replace_once(before, after):
    assert original.count(before) == 1, before
    return original.replace(before, after, 1)


mutants = {
    'submitted': original,
    'sparse_direction_bits': replace_once('bits[i] = b', 'bits[i] = i'),
    'rebuild_logic_exception': replace_once(
        '    key, stream = canonical_proof_key(\n        clauses, query, proof, max_steps=max_steps\n    )',
        '    try:\n        key, stream = canonical_proof_key(clauses, query, proof, max_steps=max_steps)\n'
        '    except LogicValidationError as exc:\n        raise LogicValidationError(str(exc))'),
    'consume_generator': replace_once(
        '    key, stream = canonical_proof_key(',
        '    if type(proof).__name__ == "generator":\n        tuple(proof)\n    key, stream = canonical_proof_key('),
    'mix_symbol_namespaces': replace_once(
        '        def gent(e):\n',
        '        def gent(e):\n            if e in rel_table:\n                return rel_table[e]\n'),
    'import_forbidden_enumerator': replace_once(
        '    n = len(stream)\n',
        '    __import__("kmesh.logic.proof_enumeration")\n    n = len(stream)\n'),
    'corrupt_long_chain_body': replace_once(
        '            out.append((ground_enc, head_enc, tuple(body_enc)))',
        '            if n > 1000 and body_enc:\n                body_enc[0] = (9999, ("v", 0), ("v", 1))\n'
        '            out.append((ground_enc, head_enc, tuple(body_enc)))'),
}
rows = []
for name, source in mutants.items():
    case = out / 'pytest-tmp' / name
    case.mkdir(parents=True)
    shutil.copytree(ROOT / 'src/kmesh', case / 'src/kmesh', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    # The submitted test incorrectly replaces PYTHONPATH with the repo root.
    # Make that root resolve this isolated copy too, never the live editable package.
    (case / 'kmesh').symlink_to('src/kmesh', target_is_directory=True)
    (case / 'tests').mkdir()
    (case / 'src/kmesh/logic/motif.py').write_text(source)
    (case / 'tests/test_motif.py').write_text(test)
    (out / (name + '.source.py')).write_text(source)
    command = [sys.executable, '-m', 'pytest', '-q', str(case / 'tests/test_motif.py'),
               '--basetemp', str(case / 'temp')]
    env = os.environ | {'PYTHONPATH': str(case / 'src'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'CUDA_VISIBLE_DEVICES': ''}
    p = subprocess.run(command, cwd=case, env=env, capture_output=True, timeout=20)
    (out / (name + '.stdout.txt')).write_bytes(p.stdout)
    (out / (name + '.stderr.txt')).write_bytes(p.stderr)
    rows.append(dict(name=name, argv=command, cwd=str(case), pythonpath=env['PYTHONPATH'], exit_code=p.returncode,
                     source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                     guard_valid=(p.returncode == (0 if name == 'submitted' else 1))))
result = dict(test_sha256=hashlib.sha256(test.encode()).hexdigest(), runs=rows,
              all_guards_valid=all(r['guard_valid'] for r in rows))
(out / 'guards.json').write_text(json.dumps(result, indent=2) + '\n')
for row in rows:
    print(f'{row["name"]}: exit={row["exit_code"]}, guard_valid={row["guard_valid"]}')
if args.enforce and not result['all_guards_valid']:
    raise SystemExit(1)
