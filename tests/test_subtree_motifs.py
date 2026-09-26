"""T0016 tests for ``subtree_motifs.proof_subtree_motif_keys`` (D34).

Per-occurrence-position complete rooted subtree motif directory, hand-checked
against the frozen literal keys of the contract §5 (never derived from the
product), plus object-identity spy checks, delegation/budget propagation,
input errors identical to a direct T0014 call, and hard import isolation.

Only the allowed whitelist is imported (stdlib + ``kmesh.logic.types`` /
``kmesh.logic.proof`` verifier + T0014 ``motif`` key + T0015 ``proof_subtree``
for the fragment reference + the target). No solver / enumeration / torch /
YAML / file / cache / recursion.  All fixtures are fixed literals.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest

from kmesh.logic.types import Atom, Clause, LogicValidationError
from kmesh.logic.proof import ProofStep, ProofLimitError, verify_proof
from kmesh.logic.motif import canonical_motif_key, MotifLimitError
import kmesh.logic.subtree_motifs as stm
from kmesh.logic.subtree_motifs import proof_subtree_motif_keys

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def a(pred, x, y):
    return Atom(pred, (x, y))

def fact(pred, x, y):
    return Clause((), a(pred, x, y))

def rule(head, hx, hy, *body):
    return Clause(
        tuple(a(b[0], b[1], b[2]) for b in body), a(head, hx, hy))

def step(ci, refs, pred, x, y):
    return ProofStep(ci, tuple(refs), a(pred, x, y))

def tolist(x):
    return tuple(tolist(v) for v in x) if isinstance(x, tuple) else x

def _snapshot(w, q, p):
    def atom_plain(at):
        return (at.pred, at.args)
    def clause_plain(c):
        return (tuple(atom_plain(x) for x in c.body), atom_plain(c.head))
    cl = tuple(clause_plain(c) for c in w)
    qn = atom_plain(q)
    pn = tuple(
        (s.clause_index, s.premise_steps, atom_plain(s.conclusion)) for s in p)
    raw = json.dumps([cl, qn, pn], ensure_ascii=False, sort_keys=True).encode("utf-8")
    return (cl, qn, pn, hashlib.sha256(raw).hexdigest())

# frozen main-example world (order 0..4)
W = (
    rule("w", "?x", "?z", ("u", "?x", "?y"), ("v", "?y", "?z")),
    fact("q", "b", "c"),
    rule("u", "?x", "?y", ("p", "?x", "?y")),
    fact("p", "a", "b"),
    rule("v", "?x", "?y", ("q", "?x", "?y")),
)
QUERY = a("w", "a", "c")
P = (
    ProofStep(3, (), a("p", "a", "b")),
    ProofStep(1, (), a("q", "b", "c")),
    ProofStep(2, (0,), a("u", "a", "b")),
    ProofStep(4, (1,), a("v", "b", "c")),
    ProofStep(0, (2, 3), QUERY),
)
assert verify_proof(W, QUERY, P, max_steps=10) is True

# contract §5 literals (immutable)
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
EXPECTED = (FACT_KEY, FACT_KEY, COPY_KEY, COPY_KEY, MAIN_KEY)


# ---------------------------------------------------------------------------
# Group A: semantics & occurrence positions
# ---------------------------------------------------------------------------

def test_single_fact_and_main_example_literals():
    wf = (fact("p", "a", "b"),)
    qf = a("p", "a", "b")
    pf = (ProofStep(0, (), a("p", "a", "b")),)
    assert verify_proof(wf, qf, pf, max_steps=10) is True
    dk = proof_subtree_motif_keys(wf, qf, pf, max_steps=2, max_orientations=1)
    assert dk == (FACT_KEY,)
    assert type(dk) is tuple
    # main example: strict tuple, keys hashable, literal match
    k = proof_subtree_motif_keys(W, QUERY, P, max_steps=5, max_orientations=2)
    assert type(k) is tuple
    assert k == EXPECTED
    h = None
    for x in k:
        h = hash(x)  # raises TypeError if any key unhashable
    assert isinstance(h, int)


def test_main_example_reorder_storage():
    # storage order (old 0,2,1,3,4); premise refs remapped, ci kept
    P2 = (
        step(3, (), "p", "a", "b"),
        step(2, (0,), "u", "a", "b"),
        step(1, (), "q", "b", "c"),
        step(4, (2,), "v", "b", "c"),
        step(0, (1, 3), "w", "a", "c"),
    )
    assert verify_proof(W, QUERY, P2, max_steps=10) is True
    d2 = proof_subtree_motif_keys(W, QUERY, P2, max_steps=5, max_orientations=2)
    d0 = proof_subtree_motif_keys(W, QUERY, P, max_steps=5, max_orientations=2)
    assert d2 == (FACT_KEY, COPY_KEY, FACT_KEY, COPY_KEY, MAIN_KEY)
    assert d2 != d0  # storage order changed the directory
    assert type(d2) is tuple


def test_main_example_reversed_world_remap_ci():
    # reverse world clauses; remap clause_index only, refs unchanged
    W_rev = W[::-1]
    ci_map = {i: 4 - i for i in range(5)}
    P3 = tuple(
        ProofStep(ci_map[s.clause_index], s.premise_steps, s.conclusion) for s in P)
    assert verify_proof(W_rev, QUERY, P3, max_steps=10) is True
    d3 = proof_subtree_motif_keys(W_rev, QUERY, P3, max_steps=5, max_orientations=2)
    d0 = proof_subtree_motif_keys(W, QUERY, P, max_steps=5, max_orientations=2)
    assert d3 == d0  # renaming clause storage does not change the directory


def _renamed_main():
    rel_map = {"u": "G", "w": "T", "v": "M", "q": "R", "p": "Z"}
    ent_map = {"a": "A", "b": "B", "c": "C"}
    def rn_term(t, var):
        return var[t] if t.startswith("?") else ent_map[t]
    def rn_atom(at, var):
        return Atom(rel_map[at.pred], tuple(rn_term(x, var) for x in at.args))
    def build_var(i, c):
        if not c.body:
            return {}
        vs = []
        for at in [c.head] + list(c.body):
            for t in at.args:
                if t.startswith("?") and t not in vs:
                    vs.append(t)
        return {v: "?x%d%d" % (i, j) for j, v in enumerate(vs)}
    newW = []
    for i, c in enumerate(W):
        var = build_var(i, c)
        newW.append(
            Clause(tuple(rn_atom(b, var) for b in c.body), rn_atom(c.head, var)))
    newW = tuple(newW)
    newQ = rn_atom(QUERY, {})
    # preserve clause_index / premise_steps; only rename relation / constant / variable
    newP = tuple(
        ProofStep(s.clause_index, s.premise_steps, rn_atom(s.conclusion, {})) for s in P)
    return newW, newQ, newP


def test_main_example_rename_invariant():
    nW, nQ, nP = _renamed_main()
    assert verify_proof(nW, nQ, nP, max_steps=10) is True
    # actual fields changed
    assert (nW, nQ, nP) != (W, QUERY, P)
    dn = proof_subtree_motif_keys(nW, nQ, nP, max_steps=5, max_orientations=2)
    d0 = proof_subtree_motif_keys(W, QUERY, P, max_steps=5, max_orientations=2)
    assert dn == d0 == EXPECTED


def test_main_example_purity_and_hash():
    # deep copy of input fields before / after the call must be unchanged
    before = deepcopy((W, QUERY, P))
    d0 = proof_subtree_motif_keys(W, QUERY, P, max_steps=5, max_orientations=2)
    after = deepcopy((W, QUERY, P))
    assert (W, QUERY, P) == before
    assert _snapshot(*before) == _snapshot(*after)  # fields stable, unchanged
    # and the returned directory is value-stable and hashable
    d1 = proof_subtree_motif_keys(W, QUERY, P, max_steps=5, max_orientations=2)
    assert tolist(d0) == tolist(d1)
    assert hash(d0) == hash(d1)


# ---------------------------------------------------------------------------
# Group B: complete support & boundaries
# ---------------------------------------------------------------------------

def _dup_occurrence():
    w = (fact("p", "a", "b"),
         rule("q", "?x", "?y", ("p", "?x", "?y"), ("p", "?x", "?y")))
    q = a("q", "a", "b")
    s = ProofStep(0, (), a("p", "a", "b"))
    return w, q, (s, s, ProofStep(1, (0, 1), a("q", "a", "b")))

def test_duplicate_occurrence_not_deduped():
    w, q, proof = _dup_occurrence()
    assert verify_proof(w, q, proof, max_steps=10) is True
    d = proof_subtree_motif_keys(w, q, proof, max_steps=3, max_orientations=2)
    # not deduplicated: the two occurrences each contribute a key, so the
    # directory has 3 entries (two FACT keys + the 3-header whole key), not 2.
    assert type(d) is tuple and len(d) == 3
    assert d[0] == FACT_KEY and d[1] == FACT_KEY
    assert tuple(len(x[1]) for x in d) == (1, 1, 3)


def test_duplicate_occurrence_O_boundary():
    # per-subtree orientation budget: subtree 0/1 cost 1 each, whole tree
    # B=1 cost 2 (directory cost sums to 4 but O=2 suffices per subtree);
    # O=1 fails on the whole tree first (it runs before any subtree).
    w, q, proof = _dup_occurrence()
    dk = proof_subtree_motif_keys(w, q, proof, max_steps=3, max_orientations=2)
    assert type(dk) is tuple and len(dk) == 3
    assert dk[0] == FACT_KEY and dk[1] == FACT_KEY
    assert tuple(len(x[1]) for x in dk) == (1, 1, 3)
    with pytest.raises(MotifLimitError) as exc:
        proof_subtree_motif_keys(w, q, proof, max_steps=3, max_orientations=1)
    assert type(exc.value) is MotifLimitError
    assert str(exc.value) == "motif.max_orientations insufficient for complete canonicalization"


def test_bounded_cycle_three_keys():
    w = (fact("p", "a", "b"),
         rule("q", "?x", "?y", ("p", "?x", "?y")),
         rule("p", "?x", "?y", ("q", "?x", "?y")))
    q = a("p", "a", "b")
    p = (ProofStep(0, (), a("p", "a", "b")),
         ProofStep(1, (0,), a("q", "a", "b")),
         ProofStep(2, (1,), a("p", "a", "b")))
    assert verify_proof(w, q, p, max_steps=3) is True
    d = proof_subtree_motif_keys(w, q, p, max_steps=3, max_orientations=100)
    assert type(d) is tuple and len(d) == 3
    assert tuple(len(x[1]) for x in d) == (1, 2, 3)
    # relation cycle is legal, not rejected
    assert all(hash(x) is not None for x in d)


@dataclass(frozen=True)
class NoteStep(ProofStep):
    note: str


def test_main_example_required_note_subclass():
    Ws = W
    Qs = QUERY
    Ps = (
        NoteStep(3, (), a("p", "a", "b"), note="n0"),
        NoteStep(1, (), a("q", "b", "c"), note="n1"),
        NoteStep(2, (0,), a("u", "a", "b"), note="n2"),
        NoteStep(4, (1,), a("v", "b", "c"), note="n3"),
        NoteStep(0, (2, 3), QUERY, note="n4"),
    )
    assert verify_proof(Ws, Qs, Ps, max_steps=5) is True
    d = proof_subtree_motif_keys(Ws, Qs, Ps, max_steps=5, max_orientations=2)
    assert d == EXPECTED


def test_thirty_two_copy_chain():
    # 1 fact p0(a,b) + 31 distinct-predicate copy rules -> 32 steps
    w = (fact("p0", "a", "b"),)
    for i in range(1, 32):
        w = w + (rule("p%d" % i, "?x", "?y", ("p%d" % (i - 1), "?x", "?y")),)
    q = a("p31", "a", "b")
    p = (ProofStep(0, (), a("p0", "a", "b")),)
    for i in range(1, 32):
        p = p + (ProofStep(i, (i - 1,), a("p%d" % i, "a", "b")),)
    assert verify_proof(w, q, p, max_steps=40) is True
    d = proof_subtree_motif_keys(w, q, p, max_steps=40, max_orientations=1)
    assert type(d) is tuple and len(d) == 32
    lens = tuple(len(x[1]) for x in d)
    assert lens == tuple(range(1, 33))
    assert sum(lens) == 528  # 32*33/2
    assert len(w) == 32


def _fragment_world():
    w4 = (
        fact("p", "a", "b"),
        rule("q", "?x", "?y", ("p", "?x", "?y")),          # COPY (same order)
        rule("r", "?y", "?x", ("q", "?x", "?y")),          # INV (swapped)
        rule("s", "?y", "?x", ("r", "?x", "?y")),          # INV (swapped)
    )
    q4 = a("s", "a", "b")
    p4 = (
        ProofStep(0, (), a("p", "a", "b")),
        ProofStep(1, (0,), a("q", "a", "b")),
        ProofStep(2, (1,), a("r", "b", "a")),
        ProofStep(3, (2,), a("s", "a", "b")),
    )
    return w4, q4, p4

def _fragment_independent():
    w3 = (
        fact("p", "a", "b"),
        rule("q", "?y", "?x", ("p", "?x", "?y")),   # INV
        rule("r", "?y", "?x", ("q", "?x", "?y")),   # INV
    )
    q3 = a("r", "a", "b")
    p3 = (
        ProofStep(0, (), a("p", "a", "b")),
        ProofStep(1, (0,), a("q", "b", "a")),
        ProofStep(2, (1,), a("r", "a", "b")),
    )
    return w3, q3, p3

def test_fragment_not_in_directory():
    w4, q4, p4 = _fragment_world()
    assert verify_proof(w4, q4, p4, max_steps=40) is True
    d4 = proof_subtree_motif_keys(w4, q4, p4, max_steps=40, max_orientations=10)
    assert type(d4) is tuple and len(d4) == 4
    assert tuple(len(x[1]) for x in d4) == (1, 2, 3, 4)
    # independent FACT->INV->INV T0014 key (reference), not any internal
    # clipped fragment of the 4-step directory.
    w3, q3, p3 = _fragment_independent()
    assert verify_proof(w3, q3, p3, max_steps=40) is True
    k3 = canonical_motif_key(w3, q3, p3, max_steps=40, max_orientations=10)
    assert len(k3[1]) == 3
    assert not any(k3 == x for x in d4)


# ---------------------------------------------------------------------------
# Group C: call order & budget
# ---------------------------------------------------------------------------

def _main_example_args():
    return W, QUERY, P, dict(max_steps=5, max_orientations=2)


def test_call_order_and_budget_identity():
    w, q, p, kw = _main_example_args()
    calls = []
    subs = []
    o_ck = stm.canonical_motif_key
    o_es = stm.extract_proof_subtree
    def spy_ck(*a, **k):
        calls.append(("ck", a, k))
        return o_ck(*a, **k)
    def spy_es(*a, **k):
        calls.append(("es", a, k))
        res = o_es(*a, **k)
        subs.append(res)
        return res
    stm.canonical_motif_key = spy_ck
    stm.extract_proof_subtree = spy_es
    try:
        res = proof_subtree_motif_keys(w, q, p, **kw)
    finally:
        stm.canonical_motif_key = o_ck
        stm.extract_proof_subtree = o_es
    assert res == EXPECTED
    kinds = [c[0] for c in calls]
    assert kinds == ["ck", "es", "ck", "es", "ck", "es", "ck", "es", "ck"]
    assert sum(1 for c in calls if c[0] == "ck") == 5
    assert sum(1 for c in calls if c[0] == "es") == 4
    # 1st = whole tree, original objects + original budget
    kind, aargs, kkw = calls[0]
    assert kind == "ck"
    assert aargs[0] is w and aargs[1] is q and aargs[2] is p
    assert kkw["max_steps"] == 5 and kkw["max_orientations"] == 2
    # each es root 0..3 in order, then its subtree ck
    for i, r in enumerate(range(4)):
        ekind, eargs, ekw = calls[1 + 2 * i]
        assert ekind == "es"
        assert eargs[0] is w and eargs[1] is q and eargs[2] is p
        assert eargs[3] == r
        assert ekw["max_steps"] == 5
        sck, sac, skw = calls[2 + 2 * i]
        assert sck == "ck"
        assert sac[0] is w
        assert sac[1] is p[r].conclusion  # subtree query = original step conclusion
        assert sac[2] is subs[r]          # sub = extracted returned object
        assert skw["max_steps"] == 5 and skw["max_orientations"] == 2
    # last root not extracted / recomputed: es roots are only 0..3
    assert all(c[1][3] == i for i, c in enumerate([c for c in calls if c[0] == "es"]))


def test_budget_default_and_nondefault_passthrough():
    calls = []
    o_ck = stm.canonical_motif_key
    o_es = stm.extract_proof_subtree
    def spy_ck(*a, **k):
        calls.append(("ck", a, k))
        return o_ck(*a, **k)
    def spy_es(*a, **k):
        calls.append(("es", a, k))
        return o_es(*a, **k)
    stm.canonical_motif_key = spy_ck
    stm.extract_proof_subtree = spy_es
    try:
        # default budgets
        proof_subtree_motif_keys(W, QUERY, P)
        assert len(calls) == 9
    finally:
        stm.canonical_motif_key = o_ck
        stm.extract_proof_subtree = o_es
    calls.clear()
    stm.canonical_motif_key = spy_ck
    stm.extract_proof_subtree = spy_es
    try:
        proof_subtree_motif_keys(W, QUERY, P, max_steps=7, max_orientations=2)
    finally:
        stm.canonical_motif_key = o_ck
        stm.extract_proof_subtree = o_es
    for kind, aargs, kkw in calls:
        if kind == "ck":
            assert kkw["max_steps"] == 7 and kkw["max_orientations"] == 2
        else:
            assert kkw["max_steps"] == 7
    # re-run default to inspect default values
    calls.clear()
    stm.canonical_motif_key = spy_ck
    stm.extract_proof_subtree = spy_es
    try:
        proof_subtree_motif_keys(W, QUERY, P)
    finally:
        stm.canonical_motif_key = o_ck
        stm.extract_proof_subtree = o_es
    for kind, aargs, kkw in calls:
        if kind == "ck":
            assert kkw["max_steps"] == 10000 and kkw["max_orientations"] == 100000
        else:
            assert kkw["max_steps"] == 10000


def test_single_fact_no_extraction():
    wf = (fact("p", "a", "b"),)
    qf = a("p", "a", "b")
    pf = (ProofStep(0, (), a("p", "a", "b")),)
    calls = []
    o_ck = stm.canonical_motif_key
    o_es = stm.extract_proof_subtree
    def spy_ck(*a, **k):
        calls.append(("ck", a, k))
        return o_ck(*a, **k)
    def spy_es(*a, **k):
        calls.append(("es", a, k))
        raise LogicValidationError("should-not-reach")
    stm.canonical_motif_key = spy_ck
    stm.extract_proof_subtree = spy_es
    try:
        d = proof_subtree_motif_keys(wf, qf, pf)
    finally:
        stm.canonical_motif_key = o_ck
        stm.extract_proof_subtree = o_es
    assert d == (FACT_KEY,)
    ck = sum(1 for c in calls if c[0] == "ck")
    es = sum(1 for c in calls if c[0] == "es")
    assert ck == 1 and es == 0


def test_sentinel_first_whole_tree():
    w, q, p, kw = _main_example_args()
    calls = []
    sent = LogicValidationError("c-first-whole")
    o_ck = stm.canonical_motif_key
    o_es = stm.extract_proof_subtree
    def spy_ck(*a, **k):
        calls.append(("ck", a, k))
        raise sent
    def spy_es(*a, **k):
        # recording extraction spy: any post-failure extraction is observed and
        # re-throws the original instance, so a mutant that extracts and re-raises
        # is visible through the combined call log below.
        calls.append(("es", a, k))
        raise sent
    stm.canonical_motif_key = spy_ck
    stm.extract_proof_subtree = spy_es
    try:
        with pytest.raises(LogicValidationError) as exc:
            proof_subtree_motif_keys(w, q, p, **kw)
    finally:
        stm.canonical_motif_key = o_ck
        stm.extract_proof_subtree = o_es
    assert exc.value is sent
    # the combined call log holds only the initial whole-tree ck: no subsequent
    # dependency call (no extraction, no subtree key, no retry) occurred after
    # the first T0014 failure -> stopped at the failure point.
    assert calls == [("ck", (w, q, p), kw)]
    assert len(calls) == 1
    assert all(c[0] == "ck" for c in calls)
    assert "es" not in (c[0] for c in calls)


def test_sentinel_extraction():
    w, q, p, kw = _main_example_args()
    calls = []
    sent = ProofLimitError("c-extract-sentinel")
    o_ck = stm.canonical_motif_key
    o_es = stm.extract_proof_subtree
    def spy_ck(*a, **k):
        calls.append(("ck", a, k))
        return o_ck(*a, **k)
    def spy_es(*a, **k):
        calls.append(("es", a, k))
        raise sent
    stm.canonical_motif_key = spy_ck
    stm.extract_proof_subtree = spy_es
    try:
        with pytest.raises(ProofLimitError) as exc:
            proof_subtree_motif_keys(w, q, p, **kw)
    finally:
        stm.canonical_motif_key = o_ck
        stm.extract_proof_subtree = o_es
    assert exc.value is sent
    # whole-tree ck once (succeeded), es(root0) raised; no further calls
    n_ck = sum(1 for c in calls if c[0] == "ck")
    n_es = sum(1 for c in calls if c[0] == "es")
    assert n_ck == 1 and n_es == 1
    assert calls[-1] == ("es", (w, q, p, 0), {"max_steps": 5})


def test_sentinel_subtree():
    w, q, p, kw = _main_example_args()
    calls = []
    sent = LogicValidationError("c-subtree-sentinel")
    o_ck = stm.canonical_motif_key
    o_es = stm.extract_proof_subtree
    ck_count = [0]
    def spy_ck(*a, **k):
        calls.append(("ck", a, k))
        ck_count[0] += 1
        if ck_count[0] == 2:  # first subtree ck
            raise sent
        return o_ck(*a, **k)
    def spy_es(*a, **k):
        calls.append(("es", a, k))
        return o_es(*a, **k)  # delegate: root0 must be extracted & succeed
    stm.canonical_motif_key = spy_ck
    stm.extract_proof_subtree = spy_es
    try:
        with pytest.raises(LogicValidationError) as exc:
            proof_subtree_motif_keys(w, q, p, **kw)
    finally:
        stm.canonical_motif_key = o_ck
        stm.extract_proof_subtree = o_es
    assert exc.value is sent
    # whole ck (1) + es root0 (1, delegated) + subtree ck (raised) -> 2 ck, 1 es
    n_ck = sum(1 for c in calls if c[0] == "ck")
    n_es = sum(1 for c in calls if c[0] == "es")
    assert n_ck == 2 and n_es == 1


# ---------------------------------------------------------------------------
# Group D: input delegation
# ---------------------------------------------------------------------------

def _direct_raises(args, kws):
    try:
        canonical_motif_key(*args, **kws)
        raise AssertionError("expected LogicValidationError/ProofLimitError from T0014")
    except (LogicValidationError, ProofLimitError) as e:
        return type(e), str(e)
    except Exception as e:  # pragma: no cover
        raise AssertionError("unexpected") from e


def test_delegation_empty_proof():
    w, q, p = _dup_occurrence()
    kws = dict(max_steps=10, max_orientations=1)
    t_direct, m_direct = _direct_raises((w, q, (),), kws)
    try:
        proof_subtree_motif_keys(w, q, (), **kws)
        raise AssertionError("expected LogicValidationError from T0014")
    except (LogicValidationError, ProofLimitError) as e:
        t_api, m_api = type(e), str(e)
    assert (t_direct, m_direct) == (t_api, m_api)
    assert str(m_direct) == "proof_key.proof must be a valid proof of query"


def test_delegation_generator_consumed():
    wf = (fact("p", "a", "b"),)
    qf = a("p", "a", "b")
    def gen():
        yield ProofStep(0, (), a("p", "a", "b"))
    g = gen()
    t_direct, m_direct = _direct_raises((wf, qf, g), dict(max_steps=10, max_orientations=1))
    try:
        proof_subtree_motif_keys(wf, qf, g, max_steps=10, max_orientations=1)
        raise AssertionError("expected LogicValidationError")
    except (LogicValidationError, ProofLimitError) as e:
        t_api, m_api = type(e), str(e)
    assert (t_direct, m_direct) == (t_api, m_api)
    assert list(g) != []  # body never consumed (type-checked before iteration)


def test_delegation_clauses_list():
    w, q, p = _dup_occurrence()
    try:
        proof_subtree_motif_keys(list(w), q, p, max_steps=3, max_orientations=2)
        raise AssertionError("expected LogicValidationError")
    except (LogicValidationError, ProofLimitError) as e:
        t_api, m_api = type(e), str(e)
    t_direct, m_direct = _direct_raises((list(w), q, p), dict(max_steps=3, max_orientations=2))
    assert (t_direct, m_direct) == (t_api, m_api)


def test_delegation_invalid_O():
    w, q, p = W, QUERY, P
    t_direct, m_direct = _direct_raises((w, q, p), dict(max_steps=5, max_orientations=-1))
    t_api, m_api = None, None
    try:
        proof_subtree_motif_keys(w, q, p, max_steps=5, max_orientations=-1)
        raise AssertionError("expected LogicValidationError")
    except (LogicValidationError, ProofLimitError) as e:
        t_api, m_api = type(e), str(e)
    assert (t_direct, m_direct) == (t_api, m_api)
    assert str(m_direct) == (
        "motif.max_orientations must be a non-bool positive integer; got int")


def test_delegation_main_steps_limit():
    # main example needs 5 steps; max_steps=4 -> ProofLimitError, same as T0014
    t_direct, m_direct = _direct_raises((W, QUERY, P), dict(max_steps=4, max_orientations=2))
    try:
        proof_subtree_motif_keys(W, QUERY, P, max_steps=4, max_orientations=2)
        raise AssertionError("expected ProofLimitError")
    except (LogicValidationError, ProofLimitError) as e:
        t_api, m_api = type(e), str(e)
    assert (t_direct, m_direct) == (t_api, m_api)
    assert m_api == "verify.proof length exceeds verify.max_steps"
    # 5/2 succeeds
    assert proof_subtree_motif_keys(W, QUERY, P, max_steps=5, max_orientations=2) == EXPECTED


def test_delegation_invalid_proof_then_invalid_O_priority():
    # empty proof + invalid O -> whole-tree proof-validity error first (T0014 order)
    t_direct, m_direct = _direct_raises((W, QUERY, ()), dict(max_steps=10, max_orientations=-1))
    try:
        proof_subtree_motif_keys(W, QUERY, (), max_steps=10, max_orientations=-1)
        raise AssertionError("expected LogicValidationError")
    except (LogicValidationError, ProofLimitError) as e:
        t_api, m_api = type(e), str(e)
    assert (t_direct, m_direct) == (t_api, m_api)
    assert "valid proof" in m_api  # proof-validity, not O, first
    assert m_api != "motif.max_orientations must be a non-bool positive integer; got int"


def test_signature_type():
    try:
        proof_subtree_motif_keys(W, QUERY)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    try:
        proof_subtree_motif_keys(W, QUERY, P, 99, max_steps=5, max_orientations=2)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    try:
        proof_subtree_motif_keys(W, QUERY, P, max_steps=5, max_orientations=2, extra=1)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass


def test_all_public():
    assert stm.__all__ == ["proof_subtree_motif_keys"]


# ---------------------------------------------------------------------------
# Group E: hard import isolation
# ---------------------------------------------------------------------------

_ISOLATION_SCRIPT = r'''
import sys, importlib, types, os
SRC = @SRC_DIR@
sys.path.insert(0, SRC)
BLOCKED = ["torch", "yaml",
            "kmesh.logic.engine", "kmesh.logic.reference_engine", "kmesh.logic.proof_enumeration"]
MSG = "t0016-blocked: "
class BlockFinder:
    def __init__(self, roots):
        self.roots = roots
    def find_spec(self, fullname, path=None, target=None):
        for r in self.roots:
            if fullname == r or fullname.startswith(r + "."):
                raise ModuleNotFoundError(MSG + fullname)
        return None
mf = BlockFinder(BLOCKED)
sys.meta_path.insert(0, mf)
try:
    for r in BLOCKED:
        try:
            importlib.import_module(r)
            print("UNBLOCKED-R:" + r)
            sys.exit(1)
        except ModuleNotFoundError as e:
            assert str(e) == MSG + r, "root wrong: " + repr(e)
            print("BLOCKED-R:" + r)
    for r in BLOCKED:
        mod = types.ModuleType(r); mod.__name__ = r; mod.__path__ = [BlockFinder(BLOCKED)]
        sys.modules[r] = mod
        try:
            importlib.import_module(r + ".t0016_probe")
            print("UNBLOCKED-S:" + r + ".t0016_probe")
            sys.exit(1)
        except ModuleNotFoundError as e:
            assert str(e) == MSG + r + ".t0016_probe", "sub wrong: " + repr(e)
            print("BLOCKED-S:" + r + ".t0016_probe")
        finally:
            sys.modules.pop(r, None)
    import kmesh.logic.subtree_motifs as stm
    want = os.path.realpath(os.path.join(SRC, "kmesh", "logic", "subtree_motifs.py"))
    assert os.path.realpath(stm.__file__) == want, "path: " + str(stm.__file__)
    from kmesh.logic.types import Atom, Clause
    from kmesh.logic.proof import ProofStep
    def atom(p,x,y): return Atom(p,(x,y))
    def fct(p,x,y): return Clause((),atom(p,x,y))
    def rle(h,hx,hy,*b): return Clause(tuple(atom(b[0],b[1],b[2]) for b in b), atom(h,hx,hy))
    def stp(ci,refs,p,x,y): return ProofStep(ci,tuple(refs),atom(p,x,y))
    w = (
        rle("w","?x","?z",("u","?x","?y"),("v","?y","?z")),
        fct("q","b","c"),
        rle("u","?x","?y",("p","?x","?y")),
        fct("p","a","b"),
        rle("v","?x","?y",("q","?x","?y")),
    )
    q = atom("w","a","c")
    p = (
        stp(3,(),"p","a","b"),
        stp(1,(),"q","b","c"),
        stp(2,(0,),"u","a","b"),
        stp(4,(1,),"v","b","c"),
        stp(0,(2,3),"w","a","c"),
    )
    # real main example (5-step) with finder active
    stm.proof_subtree_motif_keys(w, q, p, max_steps=5, max_orientations=2)
    # also exercise single-fact + a join
    stm.proof_subtree_motif_keys((fct("p","a","b"),), atom("p","a","b"),
                                 (stp(0,(),"p","a","b"),), max_steps=20, max_orientations=100)
    stm.proof_subtree_motif_keys(
        (fct("p","a","b"), fct("q","b","c"),
         rle("r","?x","?z",("p","?x","?y"),("q","?y","?z"))),
        atom("r","a","c"),
        (stp(0,(),"p","a","b"), stp(1,(),"q","b","c"), stp(2,(0,1),"r","a","c")),
        max_steps=20, max_orientations=100)
    banned = set()
    for m in sys.modules:
        for r in BLOCKED:
            if m == r or m.startswith(r + "."):
                banned.add(m)
    if banned:
        print("BAD:" + ",".join(sorted(banned)))
        sys.exit(1)
    print("ISOLATION-OK")
finally:
    if mf in sys.meta_path:
        sys.meta_path.remove(mf)
'''


def test_hard_isolation():
    root = Path(__file__).resolve().parents[1]
    src_dir = str(root / "src")
    script = _ISOLATION_SCRIPT.replace("@SRC_DIR@", json.dumps(src_dir))
    env = dict(os.environ)
    env["PYTHONPATH"] = src_dir
    env["PYTHONHASHSEED"] = "0"
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, "-I", "-c", script],
                       capture_output=True, text=True, timeout=120, env=env)
    assert r.returncode == 0, "exit=%d\n%s\n%s" % (r.returncode, r.stdout, r.stderr)
    for tag in ("torch", "yaml", "kmesh.logic.engine",
                "kmesh.logic.reference_engine", "kmesh.logic.proof_enumeration"):
        assert "BLOCKED-R:" + tag in r.stdout, "missing " + tag
        assert "BLOCKED-S:" + tag + ".t0016_probe" in r.stdout, "missing sub " + tag
    assert "ISOLATION-OK" in r.stdout
    assert "BAD:" not in r.stdout
    assert "UNBLOCKED" not in r.stdout
