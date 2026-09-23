"""Codex isolated behavioral mutants; --enforce requires every mutant rejected."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
PRODUCT = 'src/kmesh/logic/proof_key.py'
TEST = 'tests/test_proof_key.py'

def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)

def variants(source):
    call = '    if not verify_proof(clauses, query, proof, max_steps=max_steps):'
    rebuilt = '''    try:
        valid = verify_proof(clauses, query, proof, max_steps=max_steps)
    except (LogicValidationError, RuntimeError) as exc:
        raise type(exc)(str(exc)) from None
    if not valid:'''
    return {
        'submitted': source,
        'allow_unused_steps': replace_once(source, 'if ref_count[i] != 1:', 'if ref_count[i] > 1:'),
        'float_variable_number': replace_once(source, 'return ("v", number)', 'return ("v", float(number))'),
        'coerce_clauses': replace_once(source, call, '    clauses = tuple(clauses)\n' + call),
        'rebuild_exception': replace_once(source, call, rebuilt),
        'lazy_forbidden_import': replace_once(source, call, '    import kmesh.logic.engine\n' + call),
        'diagnostic_suffix': source.replace('proof_key.proof must be a valid proof of query"', 'proof_key.proof must be a valid proof of query EXTRA"').replace('proof_key.proof must be a single occurrence tree"', 'proof_key.proof must be a single occurrence tree EXTRA"'),
        'ignore_deep_tie': replace_once(source, 'cmp = _compare_subtrees(ref0, ref1, headers, children_order)', 'cmp = 0'),
        'always_sort_children': replace_once(source, '        conclusion = step.conclusion', '        if len(premise_steps) == 2:\n            cmp = _compare_subtrees(ref0, ref1, headers, children_order)\n            chosen_refs = (ref0, ref1) if cmp <= 0 else (ref1, ref0)\n\n        conclusion = step.conclusion'),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out')
    parser.add_argument('--enforce', action='store_true')
    args = parser.parse_args()
    out = (ROOT / args.out).resolve()
    assert out.is_dir() and out.parent == ROOT / 'reports/T0012'
    scratch = out / 'pytest-tmp'
    scratch.mkdir()
    source = (ROOT / PRODUCT).read_text()
    assert hashlib.sha256(source.encode()).hexdigest() == '92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1'
    results = []
    for name, code in variants(source).items():
        work = scratch / name
        shutil.copytree(ROOT / 'src', work / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
        (work / 'tests').mkdir()
        shutil.copyfile(ROOT / TEST, work / TEST)
        (work / PRODUCT).write_text(code)
        diff = ''.join(difflib.unified_diff(source.splitlines(True), code.splitlines(True), fromfile='submitted', tofile=name))
        (out / (name + '.diff')).write_text(diff)
        argv = [sys.executable, '-m', 'pytest', '-q', TEST, '--basetemp', str(work / 'tmp'), '--junitxml', str(out / (name + '.xml'))]
        env = os.environ | {'PYTHONPATH': str(work / 'src'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'CUDA_VISIBLE_DEVICES': ''}
        p = subprocess.run(argv, cwd=work, env=env, capture_output=True, timeout=45)
        (out / (name + '.stdout')).write_bytes(p.stdout)
        (out / (name + '.stderr')).write_bytes(p.stderr)
        failures = [node.attrib for node in ET.parse(out / (name + '.xml')).iter('testcase') if node.find('failure') is not None or node.find('error') is not None]
        row = dict(name=name, exit_code=p.returncode, failures=failures, argv=argv, cwd=str(work), source_sha256=hashlib.sha256(code.encode()).hexdigest())
        results.append(row)
        print(name, p.returncode, len(failures), flush=True)
    ok = results[0]['exit_code'] == 0 and all(r['exit_code'] == 1 and r['failures'] for r in results[1:])
    (out / 'guards.json').write_text(json.dumps(dict(all_guards_valid=ok, results=results), indent=2) + '\n')
    assert results[0]['exit_code'] == 0, 'submitted control failed'
    if args.enforce:
        assert ok, 'at least one contract violation survived'

if __name__ == '__main__':
    main()
