"""Additional bounded regression probes for the remaining R2 gaps; copies only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('out')
parser.add_argument('--enforce',action='store_true')
args=parser.parse_args()
OUT=ROOT/args.out
assert OUT.is_dir() and not (OUT/'guards.json').exists()
source=(ROOT/'src/kmesh/logic/motif.py').read_text()
test=(ROOT/'tests/test_motif.py').read_text()


def change(before, after):
    assert source.count(before)==1
    return source.replace(before,after,1)


cases={
    'submitted': (source,test,[]),
    'diagnostic_suffix': (change('f"got {type(orientations).__name__}"','f"got {type(orientations).__name__} WRONG"'),test,[]),
    'rebuild_limit_exception': (change(
        '    key, stream = canonical_proof_key(\n        clauses, query, proof, max_steps=max_steps\n    )',
        '    try:\n        key, stream = canonical_proof_key(clauses, query, proof, max_steps=max_steps)\n'
        '    except RuntimeError as exc:\n        raise type(exc)(str(exc))'),test,[]),
    'accept_shared_tree': (change('    key, stream = canonical_proof_key(',
        '    if isinstance(proof, tuple) and len(proof) == 2 and getattr(proof[-1], "premise_steps", None) == (0, 0):\n'
        '        return ("proof_motif_v1", ())\n    key, stream = canonical_proof_key('),test,[]),
}
# This test-only mutation must be caught by the genuine submodule self-check.
needle='if fullname == r or fullname.startswith(r + "."):'
assert test.count(needle)==1
cases['root_only_finder']=(source,test.replace(needle,'if fullname == r:',1),['-k','hard_isolation'])
rows=[]
for name,(src,tests,extra) in cases.items():
    case=OUT/'pytest-tmp'/name
    case.mkdir(parents=True)
    shutil.copytree(ROOT/'src/kmesh',case/'src/kmesh',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (case/'kmesh').symlink_to('src/kmesh',target_is_directory=True)
    (case/'tests').mkdir()
    (case/'src/kmesh/logic/motif.py').write_text(src)
    (case/'tests/test_motif.py').write_text(tests)
    (OUT/(name+'.source.py')).write_text(src)
    if tests!=test:
        (OUT/(name+'.test.py')).write_text(tests)
    cmd=[sys.executable,'-m','pytest','-q',str(case/'tests/test_motif.py'),'--basetemp',str(case/'temp'),*extra]
    env=os.environ|{'PYTHONPATH':str(case/'src'),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','CUDA_VISIBLE_DEVICES':''}
    r=subprocess.run(cmd,cwd=case,env=env,capture_output=True,timeout=20)
    (OUT/(name+'.stdout.txt')).write_bytes(r.stdout)
    (OUT/(name+'.stderr.txt')).write_bytes(r.stderr)
    rows.append(dict(name=name,argv=cmd,exit_code=r.returncode,
        guard_valid=r.returncode==(0 if name=='submitted' else 1)))
result=dict(test_sha256=hashlib.sha256(test.encode()).hexdigest(),runs=rows,all_guards_valid=all(r['guard_valid'] for r in rows))
(OUT/'guards.json').write_text(json.dumps(result,indent=2)+'\n')
for r in rows:
    print(f'{r["name"]}: exit={r["exit_code"]}, guard_valid={r["guard_valid"]}')
if args.enforce and not result['all_guards_valid']:
    raise SystemExit(1)
