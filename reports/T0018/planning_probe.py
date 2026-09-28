"""Codex planning check of accepted dependencies; no T0018 implementation."""

import json

from kmesh.logic.motif import MotifLimitError, canonical_motif_key
from kmesh.logic.proof import ProofStep
from kmesh.logic.proof_enumeration import ProofEnumerationLimitError
from kmesh.logic.query_motifs import query_subtree_motif_keys
from kmesh.logic.types import Atom, Clause


def a(p, x, y):
    return Atom(p, (x, y))


def f(p, x, y):
    return Clause((), a(p, x, y))


def c(p, q):
    return Clause((a(p, "?x", "?y"),), a(q, "?x", "?y"))


def inv(p, q):
    return Clause((a(p, "?x", "?y"),), a(q, "?y", "?x"))


def j(p, r, q):
    return Clause((a(p, "?x", "?y"), a(r, "?y", "?z")), a(q, "?x", "?z"))


# Each reference has a manually supplied complete proof, not an enumerated one.
references = (
    ((f("p", "a", "b"),), a("p", "a", "b"),
     (ProofStep(0, (), a("p", "a", "b")),)),
    ((f("p", "a", "b"), c("p", "q")), a("q", "a", "b"),
     (ProofStep(0, (), a("p", "a", "b")), ProofStep(1, (0,), a("q", "a", "b")))),
    ((f("p", "a", "b"), inv("p", "q")), a("q", "b", "a"),
     (ProofStep(0, (), a("p", "a", "b")), ProofStep(1, (0,), a("q", "b", "a")))),
    ((f("p", "a", "b"), f("r", "b", "c"), j("p", "r", "q")), a("q", "a", "c"),
     (ProofStep(0, (), a("p", "a", "b")), ProofStep(1, (), a("r", "b", "c")),
      ProofStep(2, (0, 1), a("q", "a", "c")))),
    ((f("f", "m", "n"), f("g", "n", "o"), c("f", "h"), j("h", "g", "k")), a("k", "m", "o"),
     (ProofStep(0, (), a("f", "m", "n")), ProofStep(2, (0,), a("h", "m", "n")),
      ProofStep(1, (), a("g", "n", "o")), ProofStep(3, (1, 2), a("k", "m", "o")))),
    ((f("s", "m", "n"), c("s", "t")), a("t", "m", "n"),
     (ProofStep(0, (), a("s", "m", "n")), ProofStep(1, (0,), a("t", "m", "n")))),
)
keys = tuple(canonical_motif_key(*ref) for ref in references)
assert keys[1] == keys[5]
assert len(set(keys)) == 5

world_a = (f("p", "a", "b"), f("r", "b", "a"), c("p", "q"), inv("r", "q"))
world_b = (f("p", "a", "b"), f("r", "b", "c"), c("p", "u"), j("u", "r", "v"), c("v", "t"))
world_c = (f("q", "a", "c"), f("p", "a", "b"), f("r", "b", "c"), j("p", "r", "q"))

# Expected reference membership is hand specified. This checks T0014/T0017
# compatibility; it is not an independent proof of either dependency.
cases = (
    ("A:q", world_a, a("q", "a", "b"), {0, 1, 2, 5}),
    ("A:p", world_a, a("p", "a", "b"), {0}),
    ("A:absent", world_a, a("z", "a", "b"), set()),
    ("B:t", world_b, a("t", "a", "c"), {0, 1, 4, 5}),
    ("B:v", world_b, a("v", "a", "c"), {0, 1, 4, 5}),
    ("B:u", world_b, a("u", "a", "b"), {0, 1, 5}),
    ("B:p", world_b, a("p", "a", "b"), {0}),
    ("C:q", world_c, a("q", "a", "c"), {0, 3}),
    ("empty", (), a("z", "a", "b"), set()),
)
for name, world, query, expected in cases:
    observed = query_subtree_motif_keys(world, query)
    for index, key in enumerate(keys):
        assert (key in observed) == (index in expected), (name, index)

limits = dict(max_fact_checks=2, max_derivations=4, max_proof_steps=6, max_orientations=2)
assert query_subtree_motif_keys(world_c, a("q", "a", "c"), **limits) == frozenset((keys[0], keys[3]))
assert query_subtree_motif_keys(world_c, a("p", "a", "b"), **(limits | {"max_orientations": 1})) == frozenset((keys[0],))
for changed, exception in (({"max_orientations": 1}, MotifLimitError), ({"max_proof_steps": 5}, ProofEnumerationLimitError)):
    try:
        query_subtree_motif_keys(world_c, a("q", "a", "c"), **(limits | changed))
    except exception:
        pass
    else:
        raise AssertionError(changed)

print(json.dumps({"scope": "T0014/T0017 planning checks only", "reference_proofs": 6,
                  "distinct_reference_keys": 5, "hand_specified_query_cases": len(cases),
                  "exact_C_D_S_O": [2, 4, 6, 2], "S_5_and_O_1_rejected": True,
                  "T0018_implementation": "not_run"}, indent=2))
