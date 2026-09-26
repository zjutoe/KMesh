"""Verify hand-calculated inputs/outputs using accepted T0006/T0012 only.

This file never implements or calls the proposed extraction API.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from kmesh.logic.types import Atom, Clause, LogicValidationError
from kmesh.logic.proof import ProofStep, ProofLimitError, verify_proof
from kmesh.logic.proof_key import canonical_proof_key

old = json.loads((ROOT / 'reports/T0014/review-r4-close/record.json').read_text())['after']['source_sha256']
for name in ('src/kmesh/logic/types.py', 'src/kmesh/logic/proof.py', 'src/kmesh/logic/proof_key.py'):
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == old[name]


def a(pred, x, y):
    return Atom(pred, (x, y))


world = (
    Clause((a('u', '?x', '?y'), a('v', '?y', '?z')), a('w', '?x', '?z')),
    Clause((), a('q', 'b', 'c')),
    Clause((a('p', '?x', '?y'),), a('u', '?x', '?y')),
    Clause((), a('p', 'a', 'b')),
    Clause((a('q', '?x', '?y'),), a('v', '?x', '?y')),
)
query = a('w', 'a', 'c')
proof = (
    ProofStep(3, (), a('p', 'a', 'b')),
    ProofStep(1, (), a('q', 'b', 'c')),
    ProofStep(2, (0,), a('u', 'a', 'b')),
    ProofStep(4, (1,), a('v', 'b', 'c')),
    ProofStep(0, (2, 3), query),
)
expected = {
    0: (ProofStep(3, (), a('p', 'a', 'b')),),
    1: (ProofStep(1, (), a('q', 'b', 'c')),),
    2: (ProofStep(3, (), a('p', 'a', 'b')), ProofStep(2, (0,), a('u', 'a', 'b'))),
    3: (ProofStep(1, (), a('q', 'b', 'c')), ProofStep(4, (0,), a('v', 'b', 'c'))),
    4: proof,
}
assert verify_proof(world, query, proof) is True
canonical_proof_key(world, query, proof, max_steps=5)
for root, subproof in expected.items():
    assert verify_proof(world, proof[root].conclusion, subproof) is True
    canonical_proof_key(world, proof[root].conclusion, subproof)
try:
    canonical_proof_key(world, query, proof, max_steps=4)
except ProofLimitError:
    pass
else:
    raise AssertionError('full-proof budget was skipped')

dw = (Clause((), a('p', 'a', 'b')),
      Clause((a('p', '?x', '?y'), a('p', '?x', '?y')), a('q', '?x', '?y')))
same = ProofStep(0, (), a('p', 'a', 'b'))
dp = (same, same, ProofStep(1, (0, 1), a('q', 'a', 'b')))
assert dp[0] is dp[1]
canonical_proof_key(dw, dp[-1].conclusion, dp)
bad = (same, ProofStep(1, (0, 0), a('q', 'a', 'b')))
assert verify_proof(dw, bad[-1].conclusion, bad) is True
try:
    canonical_proof_key(dw, bad[-1].conclusion, bad)
except LogicValidationError as exc:
    assert str(exc) == 'proof_key.proof must be a single occurrence tree'
else:
    raise AssertionError('shared tree accepted')

cw = (Clause((), a('p', 'a', 'b')),
      Clause((a('p', '?x', '?y'),), a('q', '?x', '?y')),
      Clause((a('q', '?x', '?y'),), a('p', '?x', '?y')))
cp = (ProofStep(0, (), a('p', 'a', 'b')), ProofStep(1, (0,), a('q', 'a', 'b')),
      ProofStep(2, (1,), a('p', 'a', 'b')))
canonical_proof_key(cw, cp[-1].conclusion, cp)
canonical_proof_key(cw, cp[1].conclusion, cp[:2])

result = dict(main_roots=list(expected), main_budget='5 accepted / 4 ProofLimitError',
    repeated_same_object='two occurrences accepted', shared_refs='T0006 True / T0012 rejected',
    finite_cycle='accepted', result='PASS', extraction_implementation='not_run / not_created')
(ROOT / 'reports/T0015/planning-examples/result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
