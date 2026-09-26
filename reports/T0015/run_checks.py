"""T0015 fixed driver: RUN preflight|focused|full|docs; never reuse a RUN."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PYTHON = '.venv/bin/python'
TASK = 'reports/T0015'
TESTS = [
    'tests/test_proof_subtree.py',
    'tests/test_motif.py',
    'tests/test_proof_count.py',
    'tests/test_proof_key.py', 'tests/test_clause_key.py', 'tests/test_depth.py',
    'tests/test_proof_enumeration.py', 'tests/test_derivations.py',
    'tests/test_dependency.py', 'tests/test_proof.py', 'tests/test_engine.py',
    'tests/test_reference_engine.py', 'tests/test_logic_types.py',
    'tests/test_config.py', 'tests/test_doctor.py',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('phase', choices=('preflight', 'focused', 'full', 'docs'))
    args = parser.parse_args()
    if args.phase in ('focused', 'full'):
        files = TESTS[:1] if args.phase == 'focused' else TESTS
        command = [PYTHON, '-m', 'pytest', '-q', *files, '--basetemp', f'{TASK}/{args.run}/pytest-tmp']
    else:
        command = [PYTHON, f'{TASK}/check_delivery.py', args.phase, f'{TASK}/{args.run}']
    return subprocess.call([PYTHON, f'{TASK}/record_check.py', args.run, '--', *command], cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
