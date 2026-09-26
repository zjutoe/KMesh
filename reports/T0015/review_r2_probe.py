"""Independent, bounded R2 checks; no changes to submitted implementation/tests."""
import ast
import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'reports/T0015'
OUT = TASK / 'review-r2-probe'
sys.path.insert(0, str(ROOT / 'src'))
from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.proof_key import canonical_proof_key
from kmesh.logic.proof_subtree import extract_proof_subtree
from kmesh.logic.types import Atom, Clause

product = 'src/kmesh/logic/proof_subtree.py'
test = 'tests/test_proof_subtree.py'
source = (ROOT / product).read_text()
original = (TASK / 'review-r1/input-snapshot' / product).read_text()
expected = original.replace('from kmesh.logic.proof_key import',
                            'from kmesh.logic.proof import ProofStep\nfrom kmesh.logic.proof_key import')
expected = expected.replace(') -> tuple:', ') -> tuple[ProofStep, ...]:')
expected = expected.replace('type(step)(', 'ProofStep(')
assert source == expected, 'product changed beyond the three prescribed edits'

def a(pred, x, y):
    return Atom(pred, (x, y))

w = (Clause((a('u','?x','?y'), a('v','?y','?z')), a('w','?x','?z')),
     Clause((), a('q','b','c')), Clause((a('p','?x','?y'),), a('u','?x','?y')),
     Clause((), a('p','a','b')), Clause((a('q','?x','?y'),), a('v','?x','?y')))
p = (ProofStep(3,(),a('p','a','b')), ProofStep(1,(),a('q','b','c')),
     ProofStep(2,(0,),a('u','a','b')), ProofStep(4,(1,),a('v','b','c')),
     ProofStep(0,(2,3),a('w','a','c')))
q = p[-1].conclusion
expected_roots = ((p[0],), (p[1],), (p[0],ProofStep(2,(0,),a('u','a','b'))),
                  (p[1],ProofStep(4,(0,),a('v','b','c'))), p)

@dataclass(frozen=True)
class AnnotatedStep(ProofStep):
    note: str

annotated = tuple(AnnotatedStep(s.clause_index,s.premise_steps,s.conclusion,'required note') for s in p)
assert verify_proof(w,q,annotated) is True
assert canonical_proof_key(w,q,annotated) == canonical_proof_key(w,q,p)
before = copy.deepcopy((w,q,p,annotated))
before_hash = hash((w,q,p,annotated))
for proof in (p, annotated):
    for root, want in enumerate(expected_roots):
        got = extract_proof_subtree(w,q,proof,root,max_steps=5)
        assert got == want
        assert type(got) is tuple and all(type(s) is ProofStep for s in got)
        assert verify_proof(w,proof[root].conclusion,got) is True
        assert all(type(ref) is int and 0 <= ref < i for i,s in enumerate(got) for ref in s.premise_steps)
assert (w,q,p,annotated) == before and hash((w,q,p,annotated)) == before_hash

wr = w[::-1]
pr = tuple(ProofStep(4-s.clause_index,s.premise_steps,s.conclusion) for s in p)
for root,want in enumerate(expected_roots):
    expected_r = tuple(ProofStep(4-s.clause_index,s.premise_steps,s.conclusion) for s in want)
    got = extract_proof_subtree(wr,q,pr,root)
    assert got == expected_r and verify_proof(wr,p[root].conclusion,got) is True

def functions(text):
    return {n.name: ast.dump(n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}

old = functions((TASK/'review-r1/input-snapshot'/test).read_text())
new = functions((ROOT/test).read_text())
changed = sorted(k for k in old if old[k] != new.get(k))
assert set(new) - set(old) == {'test_accepted_proofstep_subclass'}
allowed = {'test_single_occurrence_rejection_propagates','test_sentinel_priority',
           'test_input_generation_and_list_rejected','test_root_type_boundaries',
           'test_root_giant_integer_not_echoed','test_signature_type_errors',
           'test_reorder_premise_remap','test_input_pure_and_output_shape','test_1201_step_copy_chain'}
assert set(changed) == allowed, changed
frozen = {}
for name in (product,test,'README.md','docs/implementation_status.md','docs/handoffs/T0015-proof-subtree.md'):
    dest = OUT/'input-snapshot'/name
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/name,dest)
    frozen[name] = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
result = {'result':'PASS','product_edits':'exactly the three prescribed replacements',
          'ordinary_and_subclass_roots':'10/10 PASS','reversed_world_roots':'5/5 PASS',
          'actual_input_hash_and_structure_unchanged':True,'changed_test_functions':changed,
          'added_test_functions':['test_accepted_proofstep_subclass'],'frozen_sha256':frozen}
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
