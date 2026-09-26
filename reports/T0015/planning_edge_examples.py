"""Check the internal JOIN/unused-step/long-chain handoff fixtures, not extraction."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from kmesh.logic.types import Atom, Clause, LogicValidationError
from kmesh.logic.proof import ProofStep, verify_proof, ProofLimitError
from kmesh.logic.proof_key import canonical_proof_key


def a(p, x, y):
    return Atom(p, (x, y))


w = (Clause((a('u','?x','?y'), a('v','?y','?z')),a('w','?x','?z')),
     Clause((),a('q','b','c')), Clause((a('p','?x','?y'),),a('u','?x','?y')),
     Clause((),a('p','a','b')), Clause((a('q','?x','?y'),),a('v','?x','?y')),
     Clause((a('w','?x','?y'),),a('z','?x','?y')))
p = (ProofStep(3,(),a('p','a','b')), ProofStep(1,(),a('q','b','c')),
     ProofStep(2,(0,),a('u','a','b')), ProofStep(4,(1,),a('v','b','c')),
     ProofStep(0,(2,3),a('w','a','c')), ProofStep(5,(4,),a('z','a','c')))
canonical_proof_key(w, p[-1].conclusion, p)
assert verify_proof(w, p[4].conclusion, p[:5]) is True
canonical_proof_key(w, p[4].conclusion, p[:5])

dw = (Clause((),a('p','a','b')),
      Clause((a('p','?x','?y'),a('p','?x','?y')),a('q','?x','?y')))
s = ProofStep(0,(),a('p','a','b'))
unused = (s,s,s,ProofStep(1,(1,2),a('q','a','b')))
assert verify_proof(dw, unused[-1].conclusion, unused) is True
try:
    canonical_proof_key(dw, unused[-1].conclusion, unused)
except LogicValidationError as exc:
    assert str(exc) == 'proof_key.proof must be a single occurrence tree'
else:
    raise AssertionError('unused steps accepted')

cw = (Clause((),a('p0','a','b')), *(Clause((a(f'p{i-1}','?x','?y'),),a(f'p{i}','?x','?y')) for i in range(1,1201)))
cp = (ProofStep(0,(),a('p0','a','b')), *(ProofStep(i,(i-1,),a(f'p{i}','a','b')) for i in range(1,1201)))
canonical_proof_key(cw, cp[-1].conclusion, cp, max_steps=1201)
assert verify_proof(cw, cp[600].conclusion, cp[:601]) is True
try:
    canonical_proof_key(cw, cp[-1].conclusion, cp, max_steps=600)
except ProofLimitError:
    pass
else:
    raise AssertionError('input length budget skipped')
result = dict(internal_join='valid full/expected five-step subtree', unused='T0006 True / T0012 rejected',
              chain='1201 input / 601 expected subtree / full budget600 rejected', result='PASS', new_API='not_created')
(ROOT/'reports/T0015/planning-edge-examples/result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
