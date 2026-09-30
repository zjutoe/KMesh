"""Codex hand-written fixture checks using accepted APIs, not T0019 code.

This deliberately does not generate the proposed 80-candidate directory or
implement its report. It checks seven explicit witnesses and their relations.
"""

import json

from kmesh.logic.depth import minimum_proof_depth
from kmesh.logic.heldout_motifs import heldout_motif_hits
from kmesh.logic.motif import canonical_motif_key
from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.proof_count import count_canonical_proofs
from kmesh.logic.types import Atom, Clause


def atom(p, x, y):
    return Atom(p, (x, y))


def fact(p, x, y):
    return Clause((), atom(p, x, y))


def copy(p, q):
    return Clause((atom(p, '?x', '?y'),), atom(q, '?x', '?y'))


def inv(p, q):
    return Clause((atom(p, '?x', '?y'),), atom(q, '?y', '?x'))


def join(p, s, q):
    return Clause((atom(p, '?x', '?y'), atom(s, '?y', '?z')),
                  atom(q, '?x', '?z'))


def inter(p, s, q):
    return Clause((atom(p, '?x', '?y'), atom(s, '?x', '?y')),
                  atom(q, '?x', '?y'))


base = fact('p0', 'e0', 'e1')
base_step = ProofStep(0, (), atom('p0', 'e0', 'e1'))
cc = (
    (base, copy('p0', 'p1'), copy('p1', 'p2')),
    atom('p2', 'e0', 'e1'),
    (base_step, ProofStep(1, (0,), atom('p1', 'e0', 'e1')),
     ProofStep(2, (1,), atom('p2', 'e0', 'e1'))),
)
ii = (
    (base, inv('p0', 'p1'), inv('p1', 'p2')),
    atom('p2', 'e0', 'e1'),
    (base_step, ProofStep(1, (0,), atom('p1', 'e1', 'e0')),
     ProofStep(2, (1,), atom('p2', 'e0', 'e1'))),
)
cj = (
    (base, copy('p0', 'p1'), fact('s2', 'e1', 'e3'), join('p1', 's2', 'p2')),
    atom('p2', 'e0', 'e3'),
    (base_step, ProofStep(1, (0,), atom('p1', 'e0', 'e1')),
     ProofStep(2, (), atom('s2', 'e1', 'e3')),
     ProofStep(3, (1, 2), atom('p2', 'e0', 'e3'))),
)
jc = (
    (base, fact('s1', 'e1', 'e2'), join('p0', 's1', 'p1'), copy('p1', 'p2')),
    atom('p2', 'e0', 'e2'),
    (base_step, ProofStep(1, (), atom('s1', 'e1', 'e2')),
     ProofStep(2, (0, 1), atom('p1', 'e0', 'e2')),
     ProofStep(3, (2,), atom('p2', 'e0', 'e2'))),
)
cjc = (
    cj[0] + (copy('p2', 'p3'),), atom('p3', 'e0', 'e3'),
    cj[2] + (ProofStep(4, (3,), atom('p3', 'e0', 'e3')),),
)
jj = (
    (base, fact('s1', 'e1', 'e2'), join('p0', 's1', 'p1'),
     fact('s2', 'e2', 'e3'), join('p1', 's2', 'p2')),
    atom('p2', 'e0', 'e3'),
    (base_step, ProofStep(1, (), atom('s1', 'e1', 'e2')),
     ProofStep(2, (0, 1), atom('p1', 'e0', 'e2')),
     ProofStep(3, (), atom('s2', 'e2', 'e3')),
     ProofStep(4, (2, 3), atom('p2', 'e0', 'e3'))),
)
ttt = (
    (base, fact('s1', 'e0', 'e1'), inter('p0', 's1', 'p1'),
     fact('s2', 'e0', 'e1'), inter('p1', 's2', 'p2'),
     fact('s3', 'e0', 'e1'), inter('p2', 's3', 'p3')),
    atom('p3', 'e0', 'e1'),
    (base_step, ProofStep(1, (), atom('s1', 'e0', 'e1')),
     ProofStep(2, (0, 1), atom('p1', 'e0', 'e1')),
     ProofStep(3, (), atom('s2', 'e0', 'e1')),
     ProofStep(4, (2, 3), atom('p2', 'e0', 'e1')),
     ProofStep(5, (), atom('s3', 'e0', 'e1')),
     ProofStep(6, (4, 5), atom('p3', 'e0', 'e1'))),
)

cases = (('CC', cc, 2, 3), ('II', ii, 2, 3), ('CJ', cj, 2, 4),
         ('JC', jc, 2, 4), ('CJC', cjc, 3, 5), ('JJ', jj, 2, 5),
         ('TTT', ttt, 3, 7))
keys = []
for name, ref, depth, steps in cases:
    clauses, query, proof = ref
    assert verify_proof(*ref), name
    assert len(proof) == len(clauses) == steps, name
    assert minimum_proof_depth(clauses, query) == depth, name
    assert count_canonical_proofs(clauses, query) == 1, name
    keys.append(canonical_motif_key(*ref))
assert len(set(keys)) == 7
refs = tuple(case[1] for case in cases)
expected = ({0}, {1}, {2}, {3}, {2, 4}, {5}, {6})
for (name, ref, _, _), want in zip(cases, expected):
    assert heldout_motif_hits(ref[0], (ref[1],), refs) == (frozenset(want),), name

print(json.dumps({
    'scope': 'Seven hand-written witnesses checked with accepted dependencies only',
    'witnesses': [{'id': n, 'depth': d, 'proof_steps': z, 'canonical_proof_count': 1}
                  for n, _, d, z in cases],
    'distinct_motif_keys': 7,
    'CJC_hits_CJ_but_not_JC': True,
    'CC_and_II_have_equal_endpoints_but_distinct_keys': True,
    'full_80_candidate_audit': 'not_run: assigned to Pi in T0019',
}, ensure_ascii=False, indent=2))
