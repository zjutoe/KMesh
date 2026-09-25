"""Check handoff fixture validity against accepted APIs; no motif implementation."""
import json
from pathlib import Path

from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.proof_key import canonical_proof_key
from kmesh.logic.types import Atom, Clause, LogicValidationError

ROOT = Path(__file__).resolve().parents[2]
rows = []


def a(pred, x, y):
    return Atom(pred, (x, y))


def fact(pred, x, y):
    return Clause((), a(pred, x, y))


def rule(body, head):
    return Clause(tuple(a(*atom) for atom in body), a(*head))


def step(index, refs, pred, x, y):
    return ProofStep(index, refs, a(pred, x, y))


def check(label, clauses, proof, binary_positions):
    query = proof[-1].conclusion
    assert verify_proof(clauses, query, proof, max_steps=len(proof)) is True, label
    key = canonical_proof_key(clauses, query, proof, max_steps=len(proof))
    positions = [i for i, header in enumerate(key[1]) if len(header[1][2]) == 2]
    assert positions == binary_positions, (label, positions)
    rows.append(dict(fixture=label, verified=True, nodes=len(proof), binary_positions=positions,
                     orientations=2 ** len(positions), accepted_proof_key=key if len(proof) < 20 else 'omitted long chain'))
    return key


x, y, z = '?x', '?y', '?z'
c = (fact('p', 'a', 'b'),)
check('fact', c, (step(0, (), 'p', 'a', 'b'),), [])
c = (fact('p', 'a', 'b'), rule((('p', x, y),), ('q', x, y)))
check('copy', c, (step(0, (), 'p', 'a', 'b'), step(1, (0,), 'q', 'a', 'b')), [])

for inv in (False, True):
    tail = (y, x) if inv else (x, y)
    c = (fact('p', 'a', 'a'), rule((('p', x, y),), ('q', *tail)),
         rule((('q', x, y),), ('r', *tail)))
    p = (step(0, (), 'p', 'a', 'a'), step(1, (0,), 'q', 'a', 'a'), step(2, (1,), 'r', 'a', 'a'))
    check('M3-' + ('inv' if inv else 'copy'), c, p, [])

c = (fact('p', 'a', 'b'), fact('q', 'b', 'c'), rule((('p', x, y), ('q', y, z)), ('r', x, z)))
p = (step(0, (), 'p', 'a', 'b'), step(1, (), 'q', 'b', 'c'), step(2, (0, 1), 'r', 'a', 'c'))
k = check('join', c, p, [0])
mapping = {'p': 'z', 'q': 'a', 'r': 'm'}
renamed_a = lambda atom: a(mapping[atom.pred], *atom.args)
cc = tuple(Clause(tuple(renamed_a(v) for v in clause.body), renamed_a(clause.head)) for clause in c)
pp = tuple(ProofStep(s.clause_index, s.premise_steps, renamed_a(s.conclusion)) for s in p)
kk = check('join-renamed-actual-T0012-slot-flip', cc, pp, [0])
assert k[1][0][1][2][0][1] == ('v', 0)
assert kk[1][0][1][2][0][1] == ('v', 2)

c = (fact('p', 'a', 'a'), fact('s', 'a', 'a'), rule((('s', x, y),), ('p', x, y)),
     rule((('p', z, x), ('p', x, y)), ('q', x, x)))
p = (step(0, (), 'p', 'a', 'a'), step(1, (), 's', 'a', 'a'), step(2, (1,), 'p', 'a', 'a'), step(3, (0, 2), 'q', 'a', 'a'))
pp = (step(1, (), 's', 'a', 'a'), step(2, (0,), 'p', 'a', 'a'), step(0, (), 'p', 'a', 'a'), step(3, (1, 2), 'q', 'a', 'a'))
check('M5-AB', c, p, [0])
check('M5-BA', c, pp, [0])

c = (fact('f', 'a', 'b'), fact('g', 'b', 'c'), fact('f', 'a', 'd'), fact('g', 'd', 'c'),
     rule((('f', x, y), ('g', y, z)), ('p', x, z)), rule((('p', x, z), ('p', x, z)), ('r', x, z)))
for other in (False, True):
    indices = (0, 1, 4, 2, 3, 4, 5) if other else (0, 1, 4, 0, 1, 4, 5)
    refs = ((), (), (0, 1), (), (), (3, 4), (2, 5))
    conclusions = (c[0].head, c[1].head, a('p', 'a', 'c'), c[indices[3]].head,
                   c[indices[4]].head, a('p', 'a', 'c'), a('r', 'a', 'c'))
    p = tuple(ProofStep(i, r, atom) for i, r, atom in zip(indices, refs, conclusions))
    check('M6-' + ('AB' if other else 'AA'), c, p, [0, 1, 4])

for last in ('p', 'r'):
    c = (fact('p', 'a', 'b'), rule((('p', x, y),), ('q', x, y)), rule((('q', x, y),), (last, x, y)))
    p = (step(0, (), 'p', 'a', 'b'), step(1, (0,), 'q', 'a', 'b'), step(2, (1,), last, 'a', 'b'))
    check('M7-' + last, c, p, [])

c = (fact('p', 'a', 'b'), rule((('p', 'a', y),), ('q', 'a', y)))
check('M8-schema-constant', c, (step(0, (), 'p', 'a', 'b'), step(1, (0,), 'q', 'a', 'b')), [])
c = (fact('p', 'a', 'b'), rule((('p', x, y), ('p', x, y)), ('q', x, y)))
p = (step(0, (), 'p', 'a', 'b'), step(0, (), 'p', 'a', 'b'), step(1, (0, 1), 'q', 'a', 'b'))
check('M9-occurrences', c, p, [0])
shared = (p[0], step(1, (0, 0), 'q', 'a', 'b'))
assert verify_proof(c, shared[-1].conclusion, shared) is True
try:
    canonical_proof_key(c, shared[-1].conclusion, shared)
except LogicValidationError as exc:
    assert str(exc) == 'proof_key.proof must be a single occurrence tree'
else:
    raise AssertionError('shared proof must be rejected')

c = (fact('p0', 'a', 'b'),) + tuple(rule(((f'p{i-1}', x, y),), (f'p{i}', x, y)) for i in range(1, 1201))
p = (step(0, (), 'p0', 'a', 'b'),) + tuple(step(i, (i-1,), f'p{i}', 'a', 'b') for i in range(1, 1201))
check('unary-1201', c, p, [])
result = dict(scope='accepted verifier/proof-key fixture checks only; no new motif implementation or motif execution', fixtures=rows,
              shared_proof_rejected=True, renamed_join_base_order_actually_flipped=True)
out = ROOT / 'reports/T0014/planning-examples/examples.json'
with out.open('x') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(f'PASS: {len(rows)} valid proof fixtures, real T0012 JOIN orientation change, M6 indices 0/1/4, shared-reference rejection')
