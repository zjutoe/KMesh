"""Codex planning checks against accepted T0014/T0015 only; not T0016 tests."""
import hashlib
import json
import sys
from pathlib import Path

from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.motif import canonical_motif_key
from kmesh.logic.proof_subtree import extract_proof_subtree

ROOT = Path(__file__).resolve().parents[2]
assert Path(sys.executable).parent == ROOT / ".venv/bin"
for path, digest in {
    "src/kmesh/logic/motif.py": "23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f",
    "src/kmesh/logic/proof_subtree.py": "8c6c439269961f5de53c760b6d38660effd5dfade5804154b1d2543f6cf9fe6c",
    "tests/test_proof_subtree.py": "955ca72abf90b0574afcd75b7ccc0bfe3a3c0a114c063534b5cc24d7440c3bce",
}.items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


def a(pred, x, y):
    return Atom(pred, (x, y))


W = (
    Clause((a("u", "?x", "?y"), a("v", "?y", "?z")), a("w", "?x", "?z")),
    Clause((), a("q", "b", "c")),
    Clause((a("p", "?x", "?y"),), a("u", "?x", "?y")),
    Clause((), a("p", "a", "b")),
    Clause((a("q", "?x", "?y"),), a("v", "?x", "?y")),
)
Q = a("w", "a", "c")
P = (ProofStep(3, (), a("p", "a", "b")),
     ProofStep(1, (), a("q", "b", "c")),
     ProofStep(2, (0,), a("u", "a", "b")),
     ProofStep(4, (1,), a("v", "b", "c")), ProofStep(0, (2, 3), Q))
FACT_KEY = ("proof_motif_v1", (((0, 0, 1), (0, ("c", 0), ("c", 1)), ()),))
COPY_KEY = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)), ((1, ("v", 0), ("v", 1)),)),
    ((1, 0, 1), (1, ("c", 0), ("c", 1)), ()),
))
MAIN_KEY = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)),
     ((1, ("v", 0), ("v", 2)), (2, ("v", 2), ("v", 1)))),
    ((1, 0, 2), (1, ("v", 0), ("v", 1)), ((3, ("v", 0), ("v", 1)),)),
    ((3, 0, 2), (3, ("c", 0), ("c", 2)), ()),
    ((2, 2, 1), (2, ("v", 0), ("v", 1)), ((4, ("v", 0), ("v", 1)),)),
    ((4, 2, 1), (4, ("c", 2), ("c", 1)), ()),
))


def existing_directory(w, q, p):
    assert verify_proof(w, q, p) is True
    return tuple(canonical_motif_key(w, step.conclusion,
                 extract_proof_subtree(w, q, p, i)) for i, step in enumerate(p))


expected = (FACT_KEY, FACT_KEY, COPY_KEY, COPY_KEY, MAIN_KEY)
assert existing_directory(W, Q, P) == expected
order = (0, 2, 1, 3, 4)
pos = {old: new for new, old in enumerate(order)}
reordered = tuple(ProofStep(P[i].clause_index,
                  tuple(pos[r] for r in P[i].premise_steps), P[i].conclusion) for i in order)
assert existing_directory(W, Q, reordered) == tuple(expected[i] for i in order)
assert tuple(expected[i] for i in order) != expected


def chain(inversions):
    w = [Clause((), a("p0", "a", "b"))]
    p = [ProofStep(0, (), w[0].head)]
    for i, inv in enumerate(inversions, 1):
        w.append(Clause((a(f"p{i-1}", "?x", "?y"),),
                        a(f"p{i}", "?y" if inv else "?x", "?x" if inv else "?y")))
        x, y = p[-1].conclusion.args
        p.append(ProofStep(i, (i-1,), a(f"p{i}", y if inv else x, x if inv else y)))
    return tuple(w), p[-1].conclusion, tuple(p)


small = chain((True, True))
large = chain((False, True, True))
assert canonical_motif_key(*small) not in existing_directory(*large)
keys = existing_directory(*chain((False,) * 31))
assert [len(k[1]) for k in keys] == list(range(1, 33))
assert sum(len(k[1]) for k in keys) == 528
print(json.dumps({"result": "PASS", "scope": "accepted dependencies only",
                  "main_literal": True, "storage_reorder": True,
                  "cropped_fragment_not_covered": True, "chain_headers": 528}))
