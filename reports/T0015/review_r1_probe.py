"""Independent T0015 ordinary-input and accepted-subclass boundary probes."""
from dataclasses import dataclass
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.proof_key import canonical_proof_key
from kmesh.logic.proof_subtree import extract_proof_subtree


def a(pred,x,y):
    return Atom(pred,(x,y))


w = (Clause((a('u','?x','?y'),a('v','?y','?z')),a('w','?x','?z')),
     Clause((),a('q','b','c')), Clause((a('p','?x','?y'),),a('u','?x','?y')),
     Clause((),a('p','a','b')), Clause((a('q','?x','?y'),),a('v','?x','?y')))
p = (ProofStep(3,(),a('p','a','b')),ProofStep(1,(),a('q','b','c')),
     ProofStep(2,(0,),a('u','a','b')),ProofStep(4,(1,),a('v','b','c')),
     ProofStep(0,(2,3),a('w','a','c')))
expected = ((p[0],),(p[1],),(p[0],ProofStep(2,(0,),a('u','a','b'))),
            (p[1],ProofStep(4,(0,),a('v','b','c'))),p)
for i, want in enumerate(expected):
    got = extract_proof_subtree(w,p[-1].conclusion,p,i)
    assert got == want and verify_proof(w,p[i].conclusion,got) is True
rw = w[::-1]
rp = tuple(ProofStep(4-s.clause_index,s.premise_steps,s.conclusion) for s in p)
got = extract_proof_subtree(rw,rp[-1].conclusion,rp,3)
assert got == (ProofStep(3,(),a('q','b','c')),ProofStep(0,(0,),a('v','b','c')))
assert verify_proof(rw,rp[3].conclusion,got) is True


@dataclass(frozen=True)
class AnnotatedStep(ProofStep):
    note: str


annotated = tuple(AnnotatedStep(s.clause_index,s.premise_steps,s.conclusion,'offline note') for s in p)
assert verify_proof(w,p[-1].conclusion,annotated) is True
assert canonical_proof_key(w,p[-1].conclusion,annotated) == canonical_proof_key(w,p[-1].conclusion,p)
failure = None
try:
    got = extract_proof_subtree(w,p[-1].conclusion,annotated,3)
except TypeError as exc:
    failure = dict(type=type(exc).__name__, message=str(exc))
    assert 'note' in str(exc)
else:
    assert verify_proof(w,p[3].conclusion,got) is True
    assert tuple((s.clause_index,s.premise_steps,s.conclusion) for s in got) == tuple((s.clause_index,s.premise_steps,s.conclusion) for s in expected[3])
result = dict(ordinary_roots='5/5 PASS', world_reversal='PASS',
    accepted_ProofStep_subclass_T0006=True, accepted_ProofStep_subclass_T0012=True,
    extraction_subclass_error=failure)
(ROOT/'reports/T0015/review-r1-probe/result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
