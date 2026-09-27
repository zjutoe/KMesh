"""Codex checks hand-derived T0017 fixtures using accepted APIs only.

This is planning evidence, not the T0017 implementation or its test oracle.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

import kmesh
from kmesh.logic.types import Atom, Clause, LogicValidationError
from kmesh.logic.proof_enumeration import enumerate_proofs, ProofEnumerationLimitError
from kmesh.logic.derivations import DerivationLimitError
from kmesh.logic.subtree_motifs import proof_subtree_motif_keys
from kmesh.logic.motif import MotifLimitError
from kmesh.logic.proof_count import count_canonical_proofs

ROOT = Path(__file__).resolve().parents[2]
assert Path(kmesh.__file__).resolve() == ROOT / "src/kmesh/__init__.py"
assert Path(sys.executable).parent == ROOT / ".venv/bin"
assert not (ROOT / "src/kmesh/logic/query_motifs.py").exists()
assert not (ROOT / "tests/test_query_motifs.py").exists()

F = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("c", 0), ("c", 1)), ()),
))
C = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)), ((1, ("v", 0), ("v", 1)),)),
    ((1, 0, 1), (1, ("c", 0), ("c", 1)), ()),
))
I = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)), ((1, ("v", 1), ("v", 0)),)),
    ((1, 1, 0), (1, ("c", 1), ("c", 0)), ()),
))
J = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)),
     ((1, ("v", 0), ("v", 2)), (2, ("v", 2), ("v", 1)))),
    ((1, 0, 2), (1, ("c", 0), ("c", 2)), ()),
    ((2, 2, 1), (2, ("c", 2), ("c", 1)), ()),
))
R = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)),
     ((1, ("v", 0), ("v", 1)), (1, ("v", 0), ("v", 1)))),
    ((1, 0, 1), (1, ("c", 0), ("c", 1)), ()),
    ((1, 0, 1), (1, ("c", 0), ("c", 1)), ()),
))


def a(p, x, y):
    return Atom(p, (x, y))


def f(p, x, y):
    return Clause((), a(p, x, y))


def copy(p, q):
    return Clause((a(p, "?x", "?y"),), a(q, "?x", "?y"))


def inv(p, q):
    return Clause((a(p, "?x", "?y"),), a(q, "?y", "?x"))


def join(p, r, q):
    return Clause((a(p, "?x", "?y"), a(r, "?y", "?z")), a(q, "?x", "?z"))


fixtures = [
    ("Q0", (), a("q", "a", "b"), (1, 1, 1, 1), 0, frozenset()),
    ("Q1", (f("p", "a", "b"),), a("p", "a", "b"), (1, 1, 1, 1), 1, frozenset((F,))),
    ("Q2", (f("p", "a", "b"), f("p", "a", "b")), a("p", "a", "b"), (1, 2, 2, 1), 2, frozenset((F,))),
    ("Q3", (f("p", "a", "b"), copy("p", "q")), a("q", "a", "b"), (1, 2, 3, 1), 1, frozenset((F, C))),
    ("Q4", (f("p", "a", "b"), f("r", "b", "a"), copy("p", "q"), inv("r", "q")),
     a("q", "a", "b"), (2, 4, 6, 1), 2, frozenset((F, C, I))),
    ("Q5", (f("q", "a", "b"), f("p", "a", "b"), f("r", "a", "b"), copy("p", "q"), copy("r", "q")),
     a("q", "a", "b"), (2, 5, 7, 1), 3, frozenset((F, C))),
    ("Q6", (f("p", "a", "b"), f("p", "a", "d"), f("r", "b", "c"), f("r", "d", "c"), join("p", "r", "q")),
     a("q", "a", "c"), (6, 6, 10, 2), 2, frozenset((F, J))),
    ("Q7", (f("q", "a", "c"), f("p", "a", "b"), f("r", "b", "c"), join("p", "r", "q")),
     a("q", "a", "c"), (2, 4, 6, 2), 2, frozenset((F, J))),
    ("Q8", (f("p", "a", "b"), copy("p", "q")), a("q", "z", "b"), (1, 2, 1, 1), 0, frozenset()),
    ("Q9", (f("p", "a", "b"), f("r", "b", "c"), inv("r", "s")),
     a("p", "a", "b"), (1, 3, 1, 1), 1, frozenset((F,))),
    ("Q10", (f("p", "a", "b"), Clause((a("p", "?x", "?y"), a("p", "?x", "?y")), a("q", "?x", "?y"))),
     a("q", "a", "b"), (2, 2, 4, 2), 1, frozenset((F, R))),
]

results = []
for label, world, query, (c, d, s, o), raw_count, expected in fixtures:
    proofs = enumerate_proofs(world, query, max_fact_checks=c, max_derivations=d, max_proof_steps=s)
    assert len(proofs) == raw_count, label
    directories = tuple(proof_subtree_motif_keys(world, query, p, max_steps=s, max_orientations=o) for p in proofs)
    found = frozenset(key for directory in directories for key in directory)
    assert found == expected, label
    boundary_errors = {}
    for name, amount in (("max_fact_checks", c), ("max_derivations", d), ("max_proof_steps", s)):
        if amount == 1:
            continue
        budgets = dict(max_fact_checks=c, max_derivations=d, max_proof_steps=s)
        budgets[name] -= 1
        expected_type = ProofEnumerationLimitError if name == "max_proof_steps" else DerivationLimitError
        try:
            enumerate_proofs(world, query, **budgets)
        except expected_type as exc:
            boundary_errors[name] = str(exc)
        else:
            raise AssertionError((label, name, "not an exact boundary"))
    results.append(dict(fixture=label, raw_proofs=len(proofs), motif_keys=len(found), budgets=[c, d, s, o], boundary_errors=boundary_errors))

# A valid fact proof precedes a JOIN that must fail under O=1.
_, world, query, _, _, _ = fixtures[7]
proofs = enumerate_proofs(world, query, max_fact_checks=2, max_derivations=4, max_proof_steps=6)
assert [len(p) for p in proofs] == [1, 3]
assert proof_subtree_motif_keys(world, query, proofs[0], max_steps=6, max_orientations=1) == (F,)
try:
    proof_subtree_motif_keys(world, query, proofs[1], max_steps=6, max_orientations=1)
except MotifLimitError as exc:
    assert str(exc) == "motif.max_orientations insufficient for complete canonicalization"
else:
    raise AssertionError("late orientation failure not detected")

_, world, query, _, _, _ = fixtures[5]
assert count_canonical_proofs(world, query, max_fact_checks=2, max_derivations=5, max_proof_steps=7) == 3

print(json.dumps({
    "result": "PASS", "scope": "accepted dependencies, not T0017",
    "environment": {"python": sys.version.split()[0], "pytest": importlib.metadata.version("pytest"),
                    "kmesh": importlib.metadata.version("kmesh"), "kmesh_path": kmesh.__file__},
    "fixtures": results, "late_orientation_failure": True, "motif_count_is_not_proof_count": True,
    "dependency_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted((ROOT / "src/kmesh/logic").glob("*.py"))},
}, indent=2))
