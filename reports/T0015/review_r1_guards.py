"""Bounded faulty-copy probes; never edit the submitted implementation/tests.

Usage through record_check.py: python review_r1_guards.py RUN [--enforce]
--enforce requires the submitted control to pass and each named fault to fail
at its intended test. Without it, surviving faults are review observations.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = 'src/kmesh/logic/proof_subtree.py'
TEST = 'tests/test_proof_subtree.py'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--enforce', action='store_true')
    args = parser.parse_args()
    out = ROOT / 'reports/T0015' / args.run
    assert out.is_dir() and out.parent == ROOT / 'reports/T0015'
    source = (ROOT / PRODUCT).read_text()
    call = '    canonical_proof_key(clauses, query, proof, max_steps=max_steps)'
    assert source.count(call) == 1
    tail = '    return tuple(out)'
    assert source.count(tail) == 1
    faults = {
        'submitted': (source, None),
        'corrupt_chain_refs': (source.replace(tail,
            '    if len(proof) > 1000:\n'
            '        from dataclasses import replace\n'
            '        out = [replace(s, premise_steps=tuple(0 for _ in s.premise_steps)) for s in out]\n'
            + tail), 'test_1201_step_copy_chain'),
        'retry_logic_error': (source.replace(call,
            '    try:\n    ' + call + '\n'
            '    except LogicValidationError:\n    ' + call), 'test_sentinel_priority'),
        'consume_generator': (source.replace(call,
            '    from types import GeneratorType\n'
            '    if isinstance(proof, GeneratorType):\n'
            '        proof = tuple(proof)\n' + call), 'test_input_generation_and_list_rejected'),
        'lazy_forbidden_import': (source.replace(call,
            '    import kmesh.logic.motif\n' + call), 'test_hard_isolation'),
    }
    results = {}
    for name, (code, target) in faults.items():
        case = out / name
        case.mkdir(exist_ok=False)
        work = case / 'pytest-tmp' / 'work'
        shutil.copytree(ROOT / 'src', work / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
        (work / 'tests').mkdir()
        shutil.copyfile(ROOT / TEST, work / TEST)
        (work / PRODUCT).write_text(code)
        env = os.environ | {'PYTHONPATH': str(work / 'src'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'CUDA_VISIBLE_DEVICES': ''}
        command = [sys.executable, '-m', 'pytest', '-q', TEST, '--basetemp', str(case / 'pytest-tmp' / 'basetemp')]
        result = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=30)
        (case / 'stdout.txt').write_text(result.stdout)
        (case / 'stderr.txt').write_text(result.stderr)
        (case / 'product.py.txt').write_text(code)
        detected = result.returncode == 1 and f'FAILED {TEST}::{target}' in result.stdout if target else result.returncode == 0
        row = dict(exit_code=result.returncode, target=target, guard_valid=detected,
                   argv=command, cwd=str(work), product_sha256=hashlib.sha256(code.encode()).hexdigest(),
                   test_sha256=hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest(),
                   stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),
                   stderr_sha256=hashlib.sha256(result.stderr.encode()).hexdigest())
        results[name] = row
        (case / 'result.json').write_text(json.dumps(row, indent=2) + '\n')
        print(name, 'exit=', result.returncode, 'guard_valid=', detected, 'target=', target)
    report = dict(all_guards_valid=all(r['guard_valid'] for r in results.values()), cases=results)
    (out / 'guards.json').write_text(json.dumps(report, indent=2) + '\n')
    if args.enforce:
        assert report['all_guards_valid'], 'a faulty copy survived or control failed; inspect guards.json'


if __name__ == '__main__':
    main()
