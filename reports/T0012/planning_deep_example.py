"""Verify the equal-header/different-descendants canonical comparison fixture."""
import json
from pathlib import Path

from planning_examples import a, fact, step, ck, v, hf, pk, oracle
from kmesh.logic.types import Clause
from kmesh.logic.proof import ProofStep, verify_proof

world = (
    fact('q', 'a', 'b'), fact('r', 'b', 'a'), fact('q', 'a', 'c'), fact('r', 'c', 'a'),
    Clause((a('q', '?x', '?y'), a('r', '?y', '?z')), a('p', '?x', '?z')),
    Clause((a('p', '?x', '?y'), a('p', '?x', '?y')), a('t', '?x', '?y')),
)
children = {
    'A': (step(0, (), 'q', 'a', 'b'), step(1, (), 'r', 'b', 'a'), step(4, (0, 1), 'p', 'a', 'a')),
    'B': (step(2, (), 'q', 'a', 'c'), step(3, (), 'r', 'c', 'a'), step(4, (0, 1), 'p', 'a', 'a')),
}
keys = {}
for left, right in (('A', 'B'), ('B', 'A'), ('A', 'A')):
    l, r = children[left], children[right]
    proof = (*l, *(ProofStep(s.clause_index, tuple(i + 3 for i in s.premise_steps), s.conclusion) for s in r), step(5, (2, 5), 't', 'a', 'a'))
    assert len(proof) == 7 and verify_proof(world, a('t', 'a', 'a'), proof)
    keys[left + right] = oracle(world, proof)
root = (('t', 'a', 'a'), ck(('t', v(0), v(1)), ('p', v(0), v(1)), ('p', v(0), v(1))))
child = (('p', 'a', 'a'), ck(('p', v(0), v(1)), ('q', v(0), v(2)), ('r', v(2), v(1))))
expected = pk(root, child, hf('q', 'a', 'b'), hf('r', 'b', 'a'), child, hf('q', 'a', 'c'), hf('r', 'c', 'a'))
assert keys['AB'] == keys['BA'] == expected and keys['AA'] != expected
out = dict(result='PASS', case='K8', steps=7, same_root_header=True, AB_equals_BA=True, AA_differs=True, expected=expected)
Path('reports/T0012/planning-deep-example/example.json').write_text(json.dumps(out, indent=2) + '\n')
print('PASS: K8 equal child headers require descendant comparison; AB=BA and AA!=AB')
