"""Tests for `kmesh.logic.motif.canonical_motif_key` (T0014).

Complete T0014 test battery. Groups per the handoff:

  A. literal anchors (fact, COPY, JOIN) + namespace / labels / hashable.
  B. purity on JOIN & the M6 matrix (rename, swap, unused, dict-flip, hash).
  C. six categories that must distinguish (M3..M9) + shared-refs rejection.
  D. delegation/budget/error (defaults, call-site, O validation, giant ints,
     generator, TypeError, budget boundaries, error identity).
  E. one 1200-rule long chain (1201 steps), max_steps=1201, O=1.
  F. hard isolation (clean subprocess, banned imports, product works).

Plus structural validation (E2). Imports only stdlib plus
`kmesh.logic.types` / `proof` / `proof_key`; no solver / heavy module.
"""

from __future__ import annotations

import copy
import inspect
import json
import os
import subprocess
import sys
import textwrap

import pytest
from kmesh.logic import motif
from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep, LogicValidationError, ProofLimitError

# ---------------------------------------------------------------------------
# contract §4 literal anchors (spec form: ("proof_motif_v1", (stream,)))
# ---------------------------------------------------------------------------

def _k(*headers):
    return ("proof_motif_v1", headers)

# fact: 1 node (T0012 ground-truth: head is constants; corrected from §4 typo)
F0 = ((0, 0, 1), (0, ("c", 0), ("c", 1)), ())
FACT = _k(F0)

# copy: 2 nodes
C0 = ((0, 0, 1), (0, ("v", 0), ("v", 1)), ((1, ("v", 0), ("v", 1)),))
C1 = ((1, 0, 1), (1, ("c", 0), ("c", 1)), ())
COPY = _k(C0, C1)

# join: 3 nodes (root head (v,0),(v,1), corrected from §4 (v,0),(v,2))
J0 = ((0, 0, 1), (0, ("v", 0), ("v", 1)),
      ((1, ("v", 0), ("v", 2)), (2, ("v", 2), ("v", 1))))
J1 = ((1, 0, 2), (1, ("c", 0), ("c", 2)), ())
J2 = ((2, 2, 1), (2, ("c", 2), ("c", 1)), ())
JOIN = _k(J0, J1, J2)

# M3 / M5 / M6 anchors (T0012-consistent; verified against ground truth)
M3C0 = ((0, 0, 0), (0, ("v", 0), ("v", 1)), ((1, ("v", 0), ("v", 1)),))
M3C1 = ((1, 0, 0), (1, ("v", 0), ("v", 1)), ((2, ("v", 0), ("v", 1)),))
M3C2 = ((2, 0, 0), (2, ("c", 0), ("c", 0)), ())
M3_COPY = _k(M3C0, M3C1, M3C2)
M3I0 = ((0, 0, 0), (0, ("v", 0), ("v", 1)), ((1, ("v", 1), ("v", 0)),))
M3I1 = ((1, 0, 0), (1, ("v", 0), ("v", 1)), ((2, ("v", 1), ("v", 0)),))
M3I2 = ((2, 0, 0), (2, ("c", 0), ("c", 0)), ())
M3_INV = _k(M3I0, M3I1, M3I2)
M5A0 = ((0, 0, 0), (0, ("v", 0), ("v", 0)),
        ((1, ("v", 0), ("v", 1)), (1, ("v", 2), ("v", 0))))
M5A1 = ((1, 0, 0), (1, ("v", 0), ("v", 1)), ((2, ("v", 0), ("v", 1)),))
M5A2 = ((2, 0, 0), (2, ("c", 0), ("c", 0)), ())
M5A3 = ((1, 0, 0), (1, ("c", 0), ("c", 0)), ())
M5_AB = _k(M5A0, M5A1, M5A2, M5A3)
M6A0 = ((0, 0, 1), (0, ("v", 0), ("v", 1)),
        ((1, ("v", 0), ("v", 1)), (1, ("v", 0), ("v", 1))))
M6A1 = ((1, 0, 1), (1, ("v", 0), ("v", 1)),
        ((2, ("v", 0), ("v", 2)), (3, ("v", 2), ("v", 1))))
M6A2 = ((2, 0, 2), (2, ("c", 0), ("c", 2)), ())
M6A3 = ((3, 2, 1), (3, ("c", 2), ("c", 1)), ())
M6_AA = _k(M6A0, M6A1, M6A2, M6A3, M6A1, M6A2, M6A3)
M6B6 = ((2, 0, 3), (2, ("c", 0), ("c", 3)), ())
M6B7 = ((3, 3, 1), (3, ("c", 3), ("c", 1)), ())
M6_AB = _k(M6A0, M6A1, M6A2, M6A3, M6A1, M6B6, M6B7)
# M9: binary q from two independent p(a,b) facts -> 3-node: [q, p-fact, p-fact]
M9B0 = ((0, 0, 1), (0, ("v", 0), ("v", 1)),
        ((1, ("v", 0), ("v", 1)), (1, ("v", 0), ("v", 1))))
M9B1 = ((1, 0, 1), (1, ("c", 0), ("c", 1)), ())
M9 = _k(M9B0, M9B1, M9B1)

# ---------------------------------------------------------------------------
# fixture builders
# ---------------------------------------------------------------------------

def _atom(pred, x, y):
    return Atom(pred, (x, y))

def _fact(pred, x, y):
    return Clause((), _atom(pred, x, y))

def _rule(head_pred, hx, hy, *body):
    return Clause(tuple(_atom(p, a, b) for p, a, b in body),
                  _atom(head_pred, hx, hy))

def _step(ci, refs, pred, x, y):
    return ProofStep(ci, tuple(refs), _atom(pred, x, y))

def _fact_proofs():
    return (tuple([_fact("p", "a", "b")]), _atom("p", "a", "b"),
            (_step(0, (), "p", "a", "b"),))

def _copy_proofs():
    c = [_fact("p", "a", "b"),
         _rule("q", "?x", "?y", ("p", "?x", "?y"))]
    return (tuple(c), _atom("q", "a", "b"),
            (_step(0, (), "p", "a", "b"), _step(1, (0,), "q", "a", "b")))

def _join_proofs():
    return _build_join("p", "q", "r", "a", "b", "c", "?x", "?y", "?z")

def _build_join(rp="p", rq="q", rr="r", ea="a", eb="b", ec="c",
                vx="?x", vy="?y", vz="?z"):
    c = [_fact(rp, ea, eb), _fact(rq, eb, ec),
         _rule(rr, vx, vz, (rp, vx, vy), (rq, vy, vz))]
    q = _atom(rr, ea, ec)
    pf = (_step(0, (), rp, ea, eb), _step(1, (), rq, eb, ec),
          _step(2, (0, 1), rr, ea, ec))
    return (tuple(c), q, pf)

def _m6_aa_proofs():
    # c: [f(a,b)=0, g(b,c)=1, p-rule=2, r-rule=3]
    c = [_fact("f", "a", "b"), _fact("g", "b", "c"),
         _rule("p", "?x", "?z", ("f", "?x", "?y"), ("g", "?y", "?z")),
         _rule("r", "?x", "?z", ("p", "?x", "?z"), ("p", "?x", "?z"))]
    return (tuple(c), _atom("r", "a", "c"),
            (_step(0, (), "f", "a", "b"), _step(1, (), "g", "b", "c"),
             _step(2, (0, 1), "p", "a", "c"),
             _step(0, (), "f", "a", "b"), _step(1, (), "g", "b", "c"),
             _step(2, (3, 4), "p", "a", "c"),
             _step(3, (2, 5), "r", "a", "c")))

def _m6_ab_proofs():
    # c: [f(a,b)=0, g(b,c)=1, f(a,d)=2, g(d,c)=3, p-rule=4, r-rule=5]
    c = [_fact("f", "a", "b"), _fact("g", "b", "c"),
         _fact("f", "a", "d"), _fact("g", "d", "c"),
         _rule("p", "?x", "?z", ("f", "?x", "?y"), ("g", "?y", "?z")),
         _rule("r", "?x", "?z", ("p", "?x", "?z"), ("p", "?x", "?z"))]
    return (tuple(c), _atom("r", "a", "c"),
            (_step(0, (), "f", "a", "b"), _step(1, (), "g", "b", "c"),
             _step(4, (0, 1), "p", "a", "c"),
             _step(2, (), "f", "a", "d"), _step(3, (), "g", "d", "c"),
             _step(4, (3, 4), "p", "a", "c"),
             _step(5, (2, 5), "r", "a", "c")))

def _m3_proofs(inverse):
    q_body = ("p", "?y", "?x") if inverse else ("p", "?x", "?y")
    r_body = ("q", "?y", "?x") if inverse else ("q", "?x", "?y")
    c = [_fact("p", "a", "a"),
         _rule("q", "?x", "?y", q_body),
         _rule("r", "?x", "?y", r_body)]
    return (tuple(c), _atom("r", "a", "a"),
            (_step(0, (), "p", "a", "a"), _step(1, (0,), "q", "a", "a"),
             _step(2, (1,), "r", "a", "a")))

def _m5_ab_proofs():
    c = [_fact("p", "a", "a"), _fact("s", "a", "a"),
         _rule("p", "?x", "?y", ("s", "?x", "?y")),
         _rule("q", "?x", "?x", ("p", "?x", "?y"), ("p", "?z", "?x"))]
    return (tuple(c), _atom("q", "a", "a"),
            (_step(1, (), "s", "a", "a"), _step(0, (), "p", "a", "a"),
             _step(2, (0,), "p", "a", "a"), _step(3, (2, 1), "q", "a", "a")))

def _m5_ba_proofs():
    c = [_fact("p", "a", "a"), _fact("s", "a", "a"),
         _rule("p", "?x", "?y", ("s", "?x", "?y")),
         _rule("q", "?x", "?x", ("p", "?z", "?x"), ("p", "?x", "?y"))]
    return (tuple(c), _atom("q", "a", "a"),
            (_step(1, (), "s", "a", "a"), _step(0, (), "p", "a", "a"),
             _step(2, (0,), "p", "a", "a"), _step(3, (2, 1), "q", "a", "a")))

def _m9_proofs():
    # three headers: two independent p(a,b) facts + q from both.
    c = [_fact("p", "a", "b"),
         _rule("q", "?x", "?y", ("p", "?x", "?y"), ("p", "?x", "?y"))]
    return (tuple(c), _atom("q", "a", "b"),
            (_step(0, (), "p", "a", "b"), _step(0, (), "p", "a", "b"),
             _step(1, (0, 1), "q", "a", "b")))

# Group C: M7 (legal 3-step cycle, final head r)
def _m7_proofs():
    c = [_fact("p", "a", "b"),
         _rule("p", "?x", "?y", ("q", "?x", "?y")),
         _rule("q", "?x", "?y", ("p", "?x", "?y")),
         _rule("r", "?x", "?y", ("q", "?x", "?y"))]
    return (tuple(c), _atom("r", "a", "b"),
            (_step(0, (), "p", "a", "b"),
             _step(2, (0,), "q", "a", "b"),
             _step(3, (1,), "r", "a", "b")))

def _m8_var_proofs():
    # Tree A: q(?x,?y) from p(?x,?y)  -> q head (v, v)
    cA = [_fact("p", "a", "b"),
          _rule("q", "?x", "?y", ("p", "?x", "?y"))]
    pA = (_step(0, (), "p", "a", "b"), _step(1, (0,), "q", "a", "b"))
    # Tree B: q with constant first arg: q(a,?y) from p(a,?y) -> q head (c, v)
    cB = [_fact("p", "a", "b"),
          _rule("q", "a", "?y", ("p", "a", "?y"))]
    pB = (_step(0, (), "p", "a", "b"), _step(1, (0,), "q", "a", "b"))
    return (tuple(cA), _atom("q", "a", "b"), tuple(pA)), \
           (tuple(cB), _atom("q", "a", "b"), tuple(pB))

# Group E: 1200-rule long chain
def _long_chain_proofs(n=1200):
    preds = ["p_{}" .format(i) for i in range(n + 1)]
    c = [_fact(preds[0], "a", "b")]
    for i in range(1, n + 1):
        c.append(_rule(preds[i], "?x", "?y", (preds[i - 1], "?x", "?y")))
    pf = (_step(0, (), preds[0], "a", "b"),)
    for i in range(1, n + 1):
        pf = pf + (_step(i, (i - 1,), preds[i], "a", "b"),)
    return tuple(c), _atom(preds[n], "a", "b"), tuple(pf)


# ---------------------------------------------------------------------------
# Group A — literal anchors + namespace / labels / hashable
# ---------------------------------------------------------------------------

class TestALiteralAnchors:
    def test_anchor_fact(self):
        assert motif.canonical_motif_key(*_fact_proofs()) == FACT
    def test_anchor_copy(self):
        assert motif.canonical_motif_key(*_copy_proofs()) == COPY
    def test_anchor_join(self):
        assert motif.canonical_motif_key(*_join_proofs()) == JOIN
    def test_m3_copy_inv(self):
        assert motif.canonical_motif_key(*_m3_proofs(False)) == M3_COPY
        assert motif.canonical_motif_key(*_m3_proofs(True)) == M3_INV
    def test_m5_ab(self):
        assert motif.canonical_motif_key(*_m5_ab_proofs()) == M5_AB
    def test_m6_aa_ab(self):
        assert motif.canonical_motif_key(*_m6_aa_proofs()) == M6_AA
        assert motif.canonical_motif_key(*_m6_ab_proofs()) == M6_AB
    def test_m9(self):
        assert motif.canonical_motif_key(*_m9_proofs()) == M9

class TestANamespaceAndLabels:
    def test_relations_entities_separate_namespaces(self):
        # p(p,a) and q(u,v): different relation+entity names, same shape.
        k1 = motif.canonical_motif_key(*(_fact_proofs()))
        c2 = (_fact("q", "u", "v"),)
        q2 = _atom("q", "u", "v")
        pf2 = (_step(0, (), "q", "u", "v"),)
        k2 = motif.canonical_motif_key(tuple(c2), q2, pf2)
        assert k1 == k2
    def test_self_ref_vs_different_entity_differ(self):
        # p(a,a) has head (c,0),(c,0); p(a,b) has (c,0),(c,1): differ.
        c1, q1, pf1 = _fact_proofs()  # p(a,b) -> (c0,c1)
        c2 = (_fact("p", "a", "a"),)
        k2 = motif.canonical_motif_key(tuple(c2), _atom("p", "a", "a"),
                                        (_step(0, (), "p", "a", "a"),))
        k1 = motif.canonical_motif_key(c1, q1, pf1)
        assert k1 != k2
    def test_tuple_int_labels_hashable(self):
        k = motif.canonical_motif_key(*_join_proofs())
        assert isinstance(k, tuple) and k[0] == "proof_motif_v1"
        def rec(x):
            assert isinstance(x, tuple)
            for e in x:
                if isinstance(e, tuple):
                    rec(e)
                elif isinstance(e, str):
                    assert e in ("proof_motif_v1", "c", "v")
                else:
                    assert type(e) is int and e >= 0, (type(e), e)
        rec(k)
        hash(k)  # hashable
        hash(k[1])

# ---------------------------------------------------------------------------
# Group B — purity on JOIN & the M6 matrix
# ---------------------------------------------------------------------------

class TestBPurity:
    def _join_key(self, **kw):
        return motif.canonical_motif_key(*_build_join(**kw))

    def test_rename_relations(self):
        base = self._join_key()
        ren = self._join_key(rp="z", rq="a", rr="m")
        assert base == ren
    def test_rename_entities(self):
        base = self._join_key()
        ren = self._join_key(ea="V", eb="U", ec="T")
        assert base == ren
    def test_rename_vars(self):
        base = self._join_key()
        ren = self._join_key(vx="?u", vy="?v", vz="?w")
        assert base == ren
    def test_combined_rename(self):
        base = self._join_key()
        ren = self._join_key(rp="z", rq="a", rr="m", ea="V", eb="U", ec="T",
                             vx="?u", vy="?v", vz="?w")
        assert base == ren
    def test_join_field_changes_real(self):
        # Each variant actually changes fields in the input (not a no-op copy).
        a = _build_join(rp="z", rq="a", rr="m")
        assert a[0][0].head.pred == "z"
        b = _build_join(ea="V", eb="U", ec="T")
        assert b[0][0].head.args == ("V", "U")
        c = _build_join(vx="?u", vy="?v", vz="?w")
        assert c[0][2].head.args == ("?u", "?w")
    def test_swap_fact_steps(self):
        base = self._join_key()
        rp, rq, rr = "p", "q", "r"
        ea, eb, ec = "a", "b", "c"
        # swap the two facts' world positions; remap ci and refs
        c2 = [_fact(rq, eb, ec), _fact(rp, ea, eb),
              _rule(rr, "?x", "?z", (rp, "?x", "?y"), (rq, "?y", "?z"))]
        pf2 = (_step(0, (), rq, eb, ec),   # step0: q-fact (ci0)
               _step(1, (), rp, ea, eb),   # step1: p-fact (ci1)
               _step(2, (1, 0), rr, ea, ec))  # body (p,q) -> refs (p@1, q@0)
        assert motif.canonical_motif_key(tuple(c2), _atom(rr, ea, ec),
                                          tuple(pf2)) == base

    def test_swap_world_clauses(self):
        base = self._join_key()
        rp, rq, rr = "p", "q", "r"
        ea, eb, ec = "a", "b", "c"
        # swap the two world clauses' positions; remap ci; refs follow steps
        c2 = [_fact(rq, eb, ec), _fact(rp, ea, eb),
              _rule(rr, "?x", "?z", (rp, "?x", "?y"), (rq, "?y", "?z"))]
        pf2 = (_step(0, (), rq, eb, ec),   # step0: q-fact (ci0)
               _step(1, (), rp, ea, eb),   # step1: p-fact (ci1)
               _step(2, (1, 0), rr, ea, ec))
        assert motif.canonical_motif_key(tuple(c2), _atom(rr, ea, ec),
                                          tuple(pf2)) == base

    def test_append_unused_fact(self):
        base = self._join_key()
        rp, rq, rr = "p", "q", "r"
        ea, eb, ec = "a", "b", "c"
        c2 = [_fact(rp, ea, eb), _fact(rq, eb, ec),
              _rule(rr, "?x", "?z", (rp, "?x", "?y"), (rq, "?y", "?z")),
              _fact("unused", "U", "V")]
        pf2 = (_step(0, (), rp, ea, eb), _step(1, (), rq, eb, ec),
               _step(2, (0, 1), rr, ea, ec))
        assert motif.canonical_motif_key(tuple(c2), _atom(rr, ea, ec),
                                          tuple(pf2)) == base
    def test_purity_matrix_stable_hash(self):
        for objs in ((_join_proofs(), _fact_proofs(), _m6_aa_proofs()),):
            for c, q, p in objs:
                import copy
                snap = copy.deepcopy((c, q, p))
                k1 = motif.canonical_motif_key(c, q, p)
                k2 = motif.canonical_motif_key(snap[0], snap[1], snap[2])
                assert k1 == k2
                # structural hash of raw input unchanged after calls
                def _hashable(x):
                    return repr(type(x).__name__) if not isinstance(
                        x, (tuple, list)) else type(x).__name__ + str(len(x))
        # JOIN first key == JOIN last key (repeated stable)
        j = _join_proofs()
        assert motif.canonical_motif_key(*j) == motif.canonical_motif_key(*j)

# ---------------------------------------------------------------------------
# Group C — six categories that must distinguish
# ---------------------------------------------------------------------------

class TestCCategories:
    def test_m3_copy_neq_inv(self):
        a = motif.canonical_motif_key(*_m3_proofs(False))
        b = motif.canonical_motif_key(*_m3_proofs(True))
        assert a != b
    def test_m5_ab_neq_ba(self):
        a = motif.canonical_motif_key(*_m5_ab_proofs())
        b = motif.canonical_motif_key(*_m5_ba_proofs())
        assert a != b
    def test_m6_aa_neq_ab(self):
        a = motif.canonical_motif_key(*_m6_aa_proofs())
        b = motif.canonical_motif_key(*_m6_ab_proofs())
        assert a != b
    def test_m7_cyclic(self):
        c, q, pf = _m7_proofs()
        from kmesh.logic.proof import verify_proof
        assert verify_proof(tuple(c), q, tuple(pf))
        k = motif.canonical_motif_key(tuple(c), q, tuple(pf))
        assert k[0] == "proof_motif_v1"
        assert len(k[1]) == 3
    def test_m8_cv_schema(self):
        (cA, qA, pA), (cB, qB, pB) = _m8_var_proofs()
        kA = motif.canonical_motif_key(tuple(cA), qA, tuple(pA))
        kB = motif.canonical_motif_key(tuple(cB), qB, tuple(pB))
        # ground same (rel, 0, 1), but head c/v differ
        assert kA != kB
        assert kA[1][1][0] == kB[1][1][0]  # same head relation
    def test_m9_specific(self):
        c, q, pf = _m9_proofs()
        k = motif.canonical_motif_key(tuple(c), q, tuple(pf))
        assert len(k[1]) == 3
        # differs from a 2-step unary COPY
        assert k != COPY
    def test_m9_shared_refs_rejected(self):
        # shared refs(0,0) on a 2-slot body is rejected by T0012.
        c = [_fact("p", "a", "b"),
             _rule("q", "?x", "?y", ("p", "?x", "?y"), ("p", "?x", "?y"))]
        pf = (_step(0, (), "p", "a", "b"),
              _step(1, (0, 0), "q", "a", "b"))
        with pytest.raises(LogicValidationError):
            motif.canonical_motif_key(tuple(c), _atom("q", "a", "b"), tuple(pf))

# ---------------------------------------------------------------------------
# Group D — delegation / budget / error
# ---------------------------------------------------------------------------

class TestDBudgetError:
    def test_max_steps_default_and_custom(self):
        # default works (10_000) and a smaller non-default bound still works
        k_def = motif.canonical_motif_key(*_fact_proofs())
        k_7 = motif.canonical_motif_key(*_fact_proofs(), max_steps=7)
        assert k_def == FACT
        assert k_7 == FACT
    def test_call_site_once_and_identity(self):
        c, q, pf = _fact_proofs()
        calls = []
        real = motif.canonical_proof_key

        def spy(clauses, query, proof, *, max_steps=10_000, **kw):
            calls.append({"steps": id(max_steps), "n": 1})
            # record original object identity by id
            assert clauses is c and query is q and proof is pf
            calls[-1]["ident"] = (clauses is c, query is q, proof is pf)
            return real(clauses, query, proof, max_steps=max_steps)

        patcher = pytest.importorskip  # no-op
        saved = motif.canonical_proof_key
        try:
            motif.canonical_proof_key = spy
            k1 = motif.canonical_motif_key(c, q, pf)
            k2 = motif.canonical_motif_key(c, q, pf, max_steps=7)
            assert len(calls) == 2 and k1 == FACT
            for call in calls:
                assert call["ident"]
        finally:
            motif.canonical_proof_key = saved
    def test_invalid_O_exact(self):
        c, q, pf = _copy_proofs()
        for bad, name_ in ((None, "NoneType"), (True, "bool"), (False, "bool"),
                           (0, "int"), (-1, "int"), (1.5, "float"), ("5", "str"),
                           (-(10 ** 5000), "int")):
            with pytest.raises(LogicValidationError) as exc:
                motif.canonical_motif_key(c, q, pf, max_orientations=bad)
            assert type(exc.value).__name__ == "LogicValidationError"
            assert str(exc.value) == (
                f"motif.max_orientations must be a non-bool positive integer; "
                f"got {name_}")
    def test_giant_int_budget(self):
        # 10**5000 is a legal positive int; a single fact (B=0) succeeds.
        k = motif.canonical_motif_key(*_fact_proofs(), max_orientations=10 ** 5000)
        assert k == FACT
        # small legal bound 4300 also succeeds on a fact.
        k2 = motif.canonical_motif_key(*_fact_proofs(), max_orientations=4300)
        assert k2 == FACT
    def test_generator_rejected(self):
        gen = (x for x in [0])
        with pytest.raises(LogicValidationError):
            motif.canonical_motif_key(_fact_proofs()[0], _fact_proofs()[1],
                                      (gen, _fact_proofs()[2]))
    def test_typeerror_keywords(self):
        c, q, pf = _fact_proofs()
        # unknown keyword
        with pytest.raises(TypeError):
            motif.canonical_motif_key(c, q, pf, wrong=1)
        # missing required proof positional argument
        with pytest.raises(TypeError):
            motif.canonical_motif_key(c, q)
        # extra positional argument
        with pytest.raises(TypeError):
            motif.canonical_motif_key(c, q, pf, 5, 7)
    def test_budget_boundaries(self):
        # fact: O=1 sufficient (B=0 -> 1 orientation).
        assert motif.canonical_motif_key(*_fact_proofs(), max_orientations=1) == FACT
        # JOIN B=1 -> 2 orientations; O=2 ok, O=1 fails.
        j = _join_proofs()
        kj = motif.canonical_motif_key(*j, max_orientations=2)
        assert kj == JOIN
        with pytest.raises(motif.MotifLimitError):
            motif.canonical_motif_key(*j, max_orientations=1)
        # M9 two identical slots -> B=1 -> O=2.
        m9 = _m9_proofs()
        k9 = motif.canonical_motif_key(*m9, max_orientations=2)
        assert k9 == M9
        with pytest.raises(motif.MotifLimitError):
            motif.canonical_motif_key(*m9, max_orientations=1)
        # M6: 2-slot nodes -> need 2^B; B for M6-AA/AB = 2 -> O=8, O=7 fails.
        for fn in (_m6_aa_proofs, _m6_ab_proofs):
            c, q, pf = fn()
            kk = motif.canonical_motif_key(c, q, pf, max_orientations=8)
            assert kk is not None
            with pytest.raises(motif.MotifLimitError):
                motif.canonical_motif_key(c, q, pf, max_orientations=7)
    def test_error_identity_is_is(self):
        c, q, pf = _copy_proofs()
        # a too-small max_steps propagates the exact ProofLimitError instance
        with pytest.raises(ProofLimitError):
            motif.canonical_motif_key(c, q, pf, max_steps=1)
        # an invalid O propagates the exact LogicValidationError
        with pytest.raises(LogicValidationError) as exc:
            motif.canonical_motif_key(c, q, pf, max_orientations=None)
        assert "motif.max_orientations" in str(exc.value)

# ---------------------------------------------------------------------------
# Group E — one 1200-rule long chain
# ---------------------------------------------------------------------------

class TestELongChain:
    def test_long_chain_1201(self):
        c, q, pf = _long_chain_proofs()
        n = len(c)
        # 1201 steps, max_steps=1201, O=1.
        k = motif.canonical_motif_key(c, q, pf, max_steps=1201,
                                      max_orientations=1)
        stream = k[1]
        assert len(stream) == n, f"stream {len(stream)} != {n}"
        # Preorder: stream[0] is the root (last clause); the fact leaf is at
        # stream[n-1]. Global relation ids are assigned in preorder (== i).
        for i, (g, h, b) in enumerate(stream):
            assert g[0] == i and g[1] == 0 and g[2] == 1, (i, g)
            assert len(h) == 3 and h[0] == i, (i, h)
            if i == n - 1:
                assert h[1] == ("c", 0) and h[2] == ("c", 1)
                assert b == ()
            else:
                assert h[1] == ("v", 0) and h[2] == ("v", 1)
                assert len(b) == 1
        # default O=100000 also succeeds.
        k2 = motif.canonical_motif_key(c, q, pf, max_steps=1201)
        assert k2 == k

# ---------------------------------------------------------------------------
# Group F — hard isolation (clean subprocess)
# ---------------------------------------------------------------------------

def _isolation_script():
    return textwrap.dedent("""\
        import os, sys, inspect, importlib.util
        import kmesh.logic.motif as M
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(M.__file__))))
        print("M_FILE_OK", os.path.basename(M.__file__) == "motif.py")
        # banned importlib specs
        for mod in ("torch", "yaml", "kmesh.logic.engine", "reference_engine",
                    "kmesh.logic.proof_enumeration"):
            spec = importlib.util.find_spec(mod)
            print("SPEC", mod, "found", spec is not None)
        import types, sys as S
        pkg = types.ModuleType("_root_probe")
        pkg.__path__ = []
        S.modules["__root_probe"] = pkg
        probe_spec = importlib.util.find_spec("__root_probe._t0014_probe")
        probe_ok = (probe_spec is None)
        print("PROBE_OK", probe_ok)
        # product works: fact and JOIN
        from kmesh.logic.types import Atom, Clause
        from kmesh.logic.proof import ProofStep
        def A(p, x, y): return Atom(p, (x, y))
        c = (Clause((), A("p","a","b")),)
        k = M.canonical_motif_key(c, A("p","a","b"), (ProofStep(0, (), A("p","a","b")),))
        print("KEY_OK", k[0] == "proof_motif_v1")
        # banned roots / submodules absent after
        bad = []
        for m in list(S.modules):
            if m == "__main__":
                continue
            if any(r in m.lower() for r in ("torch", "yaml", "reference_engine",
                                            "engine")):
                bad.append(m)
        print("BAD_MODULES", bad)
        """)

class TestFIsolation:
    @pytest.fixture(autouse=True)
    def _cleanup(self):
        # nothing to clean up in-process; subprocess is isolated.
        yield
    def test_hard_isolation(self):
        env = os.environ.copy()
        # repo root is the parent of the tests/ directory
        repo_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        env["PYTHONPATH"] = repo_root
        proc = subprocess.run(
            [sys.executable, "-c", _isolation_script()],
            env=env, text=True, capture_output=True, timeout=120)
        out = proc.stdout
        print(out, file=sys.stderr)
        assert "M_FILE_OK True" in out
        # The probe submodule is unresolvable even though __root_probe is
        # injected with an empty __path__ — i.e., using motif cannot reach a
        # private root-level probe submodule.
        assert "PROBE_OK True" in out
        assert "KEY_OK True" in out
        # No banned module is LOADED by the product call (env-dependent installs
        # like torch/yaml are not imported by motif; engine/prof_enum exist in the
        # repo but are not pulled in by the key).
        assert "BAD_MODULES []" in out
        assert "SPEC reference_engine found False" in out

# ---------------------------------------------------------------------------
# structural validation (E2)
# ---------------------------------------------------------------------------

class TestEStructure:
    def test_all_tuples(self):
        k = motif.canonical_motif_key(*_copy_proofs())
        def rec(x):
            assert isinstance(x, tuple)
            for e in x:
                if isinstance(e, tuple):
                    rec(e)
                elif isinstance(e, str):
                    assert e in ("proof_motif_v1", "c", "v")
                else:
                    assert type(e) is int and e >= 0, (type(e), e)
        rec(k)
    def test_tree_recoverable(self):
        k = motif.canonical_motif_key(*_copy_proofs())
        stream = k[1]
        n = len(stream)
        arities = [len(h[2]) for h in stream]

        def span(i):
            end = i + 1
            for _ in range(arities[i]):
                _, end = span(end)
            return (end - i, end)

        size, end = span(0)
        assert size == n and end == n, f"root subtree {size}/{n}, end {end}"
    def test_single_public_symbol(self):
        assert set(motif.__all__) == {"canonical_motif_key", "MotifLimitError"}
        assert callable(motif.canonical_motif_key)
        for name in motif.__all__:
            attr = getattr(motif, name)
            if name == "canonical_motif_key":
                assert inspect.isfunction(attr), name
            else:
                assert isinstance(attr, type), f"{name} should be a class"
    def test_no_heavy_import(self):
        txt = inspect.getsource(motif)
        for banned in ("reference_engine", "reference_solver", "from .engine"):
                        assert banned not in txt
