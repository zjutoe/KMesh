"""Independent finite probes, definition oracle and exact README reproduction."""
import importlib.util
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

from kmesh.logic.types import Atom, Clause, LogicValidationError
from kmesh.logic.proof import ProofStep, ProofLimitError, verify_proof
import kmesh.logic.proof_key as target
from kmesh.logic.proof_enumeration import enumerate_proofs

ROOT = Path(__file__).resolve().parents[3]
OUT = (ROOT / sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location('planning_definition', ROOT / 'reports/T0012/planning_examples.py')
definition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(definition)  # main is not called; no old artifact writes.
A, F, S = definition.a, definition.fact, definition.step
results = []

def check(world, proof):
    query = proof[-1].conclusion
    assert verify_proof(world, query, proof) is True
    actual = target.canonical_proof_key(world, query, proof)
    assert actual == definition.oracle(world, proof)
    return actual

base = (F('p','a','a'), F('s','a','a'), Clause((A('s','?x','?y'),), A('p','?x','?y')))
pieces = ((S(0,(),'p','a','a'),), (S(1,(),'s','a','a'), S(2,(0,),'p','a','a')))
for name, rule, count in (
    ('K5', Clause((A('p','?z','?x'), A('p','?x','?y')), A('q','?x','?x')), 4),
    ('K6', Clause((A('p','?x','?y'), A('p','?x','?y')), A('q','?x','?y')), 3),
):
    world = (*base, rule)
    keys = set()
    for left, right in itertools.product(pieces, repeat=2):
        offset = len(left)
        proof = (*left, *(ProofStep(s.clause_index, tuple(r+offset for r in s.premise_steps), s.conclusion) for s in right), S(3,(offset-1,offset+len(right)-1),'q','a','a'))
        actual = check(world, proof)
        keys.add(actual)
        changed = (*base, Clause(tuple(reversed(rule.body)), rule.head))
        swapped = (*proof[:-1], ProofStep(3, tuple(reversed(proof[-1].premise_steps)), proof[-1].conclusion))
        assert check(changed, swapped) == actual
    raw = enumerate_proofs(world, A('q','a','a'), max_fact_checks=3, max_derivations=4, max_proof_steps=20)
    assert len(raw) == 4 and len(keys) == count and {check(world,p) for p in raw} == keys
    results.append(dict(case=name, raw=4, keys=count, joint_swap=True, exhaustive_definition=True))

world = (F('q','a','b'),F('r','b','a'),F('q','a','c'),F('r','c','a'),
         Clause((A('q','?x','?y'),A('r','?y','?z')),A('p','?x','?z')),
         Clause((A('p','?x','?y'),A('p','?x','?y')),A('t','?x','?y')))
branches = ((S(0,(),'q','a','b'),S(1,(),'r','b','a'),S(4,(0,1),'p','a','a')),
            (S(2,(),'q','a','c'),S(3,(),'r','c','a'),S(4,(0,1),'p','a','a')))
keys = []
for left,right in itertools.product(branches,repeat=2):
    proof=(*left,*(ProofStep(s.clause_index,tuple(r+3 for r in s.premise_steps),s.conclusion) for s in right),S(5,(2,5),'t','a','a'))
    keys.append(check(world,proof))
assert keys[1] == keys[2] and len(set(keys)) == 3
results.append(dict(case='K8', exhaustive_definition=True, comparisons=4))

world=(F('p','a','b'),F('q','b','c'))
proof=(S(0,(),'p','a','b'), S(1,(),'q','b','c'))
assert verify_proof(world, proof[-1].conclusion, proof) is True
try:
    target.canonical_proof_key(world,proof[-1].conclusion,proof)
except LogicValidationError as exc:
    assert str(exc) == 'proof_key.proof must be a single occurrence tree'
else:
    raise AssertionError('unused step accepted')
results.append(dict(case='unused_step', result='correctly rejected after verifier True'))

original = target.verify_proof
for sentinel in (LogicValidationError('sentinel'), ProofLimitError('sentinel')):
    seen=[]
    def spy(*args,**kwargs):
        seen.append((args,kwargs))
        raise sentinel
    target.verify_proof=spy
    try:
        try:
            target.canonical_proof_key(world,proof[-1].conclusion,proof,max_steps=37)
        except type(sentinel) as caught:
            assert caught is sentinel
        else:
            raise AssertionError('sentinel not raised')
        assert len(seen)==1 and all(x is y for x,y in zip(seen[0][0],(world,proof[-1].conclusion,proof)))
        assert seen[0][1] == {'max_steps':37}
    finally:
        target.verify_proof=original
results.append(dict(case='delegation', identity_and_budget=True))

clauses=[F('n0','a','b')]
proof=[S(0,(),'n0','a','b')]
for i in range(1,1201):
    clauses.append(Clause((A(f'n{i-1}','?x','?y'),),A(f'n{i}','?x','?y')))
    proof.append(S(i,(i-1,),f'n{i}','a','b'))
clauses,proof=tuple(clauses),tuple(proof)
key=target.canonical_proof_key(clauses,proof[-1].conclusion,proof,max_steps=1201)
expected=[]
for i in range(1200,0,-1):
    expected.append(((f'n{i}','a','b'), ('clause_key_v1',(f'n{i}',('v',0),('v',1)),((f'n{i-1}',('v',0),('v',1)),))))
expected.append(definition.hf('n0','a','b'))
assert key==('proof_key_v1',tuple(expected))
assert key==target.canonical_proof_key(clauses,proof[-1].conclusion,proof,max_steps=1201)
short=target.canonical_proof_key(clauses,proof[0].conclusion,proof[:1])
assert sorted([key,short]) == [short,key] and {key: True}[key] and len({key,short})==2
results.append(dict(case='distinct_predicate_chain', steps=1201, full_headers=True, native_sort=True))

readme=(ROOT/'README.md').read_text().split('单棵证明的规范键（T0012',1)[1]
code=re.search(r'```python\n(.*?)```',readme,re.S).group(1)
(OUT/'submitted-readme.py').write_text(code)
p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,timeout=10)
(OUT/'readme.stdout').write_bytes(p.stdout)
(OUT/'readme.stderr').write_bytes(p.stderr)
assert p.returncode==1 and b'LogicValidationError: proof_key.proof must be a valid proof of query' in p.stderr
results.append(dict(case='submitted_README', exit_code=p.returncode, result='reproduced invalid example'))
(OUT/'probe.json').write_text(json.dumps(dict(product_probes='PASS',readme='FAIL_REPRODUCED',checks=results),indent=2)+'\n')
print(json.dumps(results,indent=2))
