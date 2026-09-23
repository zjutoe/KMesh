"""T0012 tests: canonical_proof_key for a single submitted occurrence tree.

Groups A-F per the handoff.  Uses only the real verifier, the T0011 *public*
clause-key API (cross-check only), and the T0009 enumerator as an independent
reference.  No planning oracle / script is imported.
"""

from __future__ import annotations

import copy as _copy
import itertools
import pytest
import subprocess
import sys
import os

from kmesh.logic.proof import ProofLimitError, ProofStep, verify_proof
from kmesh.logic.proof_enumeration import enumerate_proofs
from kmesh.logic.types import Atom, Clause, LogicValidationError
from kmesh.logic.proof_key import canonical_proof_key


def _A(pred, a, b):
    return Atom(pred, (a, b))


def _fact(pred, a, b):
    return Clause((), _A(pred, a, b))


def _ps(ci, refs, pred, a, b):
    return ProofStep(ci, tuple(refs), _A(pred, a, b))


def key(clauses, query, proof, max_steps=None):
    """Thin wrapper: let the product's own exceptions propagate."""
    if max_steps is None:
        return canonical_proof_key(clauses, query, proof)
    return canonical_proof_key(clauses, query, proof, max_steps=max_steps)


def _reorder_world(clauses, proof, perm):
    """Apply a permutation to the clause world and re-map each step's
    ``clause_index`` to the clause's new position.  Premise references are
    step positions and are left untouched (the proof step order is fixed).
    ``perm[i]`` is the OLD index of the clause at NEW position i."""
    old_to_new = {old: i for i, old in enumerate(perm)}
    new_clauses = tuple(clauses[old] for old in perm)
    new_proof = tuple(
        ProofStep(clause_index=old_to_new[st.clause_index],
                  premise_steps=st.premise_steps,
                  conclusion=st.conclusion)
        for st in proof
    )
    return new_clauses, new_proof






def _ne(a, b, label=None):
    assert a != b, (f"{label}: unexpectedly equal" if label else "unexpectedly equal")


# ---------------------------------------------------------------------------
# Group A: full hand-computed keys (K0-K8)
# ---------------------------------------------------------------------------

class TestAHandComputed:
    def test_k0_fact(self):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        exp = ("proof_key_v1",
               ((("p", "a", "b"),
                 ("clause_key_v1", ("p", ("c", "a"), ("c", "b")), ())),))
        assert key(c, _A("p", "a", "b"), p) == exp

    def test_k1_copy_full_literal(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        exp = ("proof_key_v1",
               ((("q", "a", "b"),
                 ("clause_key_v1", ("q", ("v", 0), ("v", 1)),
                   (("p", ("v", 0), ("v", 1)),))),
                (("p", "a", "b"),
                 ("clause_key_v1", ("p", ("c", "a"), ("c", "b")), ()))))
        assert key(c, _A("q", "a", "b"), p) == exp

    def test_k2_inv_full_literal(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("q", "?y", "?x")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "b", "a"))
        exp = ("proof_key_v1",
               ((("q", "b", "a"),
                 ("clause_key_v1", ("q", ("v", 0), ("v", 1)),
                   (("p", ("v", 1), ("v", 0)),))),
                (("p", "a", "b"),
                 ("clause_key_v1", ("p", ("c", "a"), ("c", "b")), ()))))
        assert key(c, _A("q", "b", "a"), p) == exp

    def test_k3_join_full_literal(self):
        c = (_fact("p", "a", "b"), _fact("q", "b", "c"),
             Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                   _A("r", "?x", "?z")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "b", "c"),
             _ps(2, (0, 1), "r", "a", "c"))
        exp = ("proof_key_v1",
               (
                   (("r", "a", "c"),
                    ("clause_key_v1", ("r", ("v", 0), ("v", 1)),
                      (("p", ("v", 0), ("v", 2)), ("q", ("v", 2), ("v", 1))))),
                   (("p", "a", "b"),
                    ("clause_key_v1", ("p", ("c", "a"), ("c", "b")), ())),
                   (("q", "b", "c"),
                    ("clause_key_v1", ("q", ("c", "b"), ("c", "c")), ())),
               ))
        assert key(c, _A("r", "a", "c"), p) == exp

    def test_k4_symmetric_two_facts(self):
        c = (_fact("p", "a", "b"), _fact("p", "a", "c"),
             Clause((_A("p", "?x", "?z"), _A("p", "?x", "?w")),
                   _A("q", "?x", "?x")))
        ck_fa = ("clause_key_v1", ("p", ("c", "a"), ("c", "b")), ())
        ck_fc = ("clause_key_v1", ("p", ("c", "a"), ("c", "c")), ())
        ck_q = ("clause_key_v1", ("q", ("v", 0), ("v", 0)),
                (("p", ("v", 0), ("v", 1)),
                 ("p", ("v", 0), ("v", 2))))
        exp = ("proof_key_v1", (
            (("q", "a", "a"), ck_q),
            (("p", "a", "b"), ck_fa),
            (("p", "a", "c"), ck_fc),
        ))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "c"),
             _ps(2, (0, 1), "q", "a", "a"))
        assert key(c, _A("q", "a", "a"), p) == exp
        p_swap = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "c"),
                  _ps(2, (1, 0), "q", "a", "a"))
        assert key(c, _A("q", "a", "a"), p_swap) == exp

    def test_k5_nonsymmetric_degenerate(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?x")))
        ck_pfact = ("clause_key_v1", ("p", ("c", "a"), ("c", "a")), ())
        ck_sfact = ("clause_key_v1", ("s", ("c", "a"), ("c", "a")), ())
        ck_psr = ("clause_key_v1", ("p", ("v", 0), ("v", 1)),
                  (("s", ("v", 0), ("v", 1)),))
        ck_qr = ("clause_key_v1", ("q", ("v", 0), ("v", 0)),
                 (("p", ("v", 0), ("v", 1)), ("p", ("v", 2), ("v", 0))))
        kAB = ("proof_key_v1", (
            (("q", "a", "a"), ck_qr),
            (("p", "a", "a"), ck_psr),
            (("s", "a", "a"), ck_sfact),
            (("p", "a", "a"), ck_pfact),
        ))
        kBA = ("proof_key_v1", (
            (("q", "a", "a"), ck_qr),
            (("p", "a", "a"), ck_pfact),
            (("p", "a", "a"), ck_psr),
            (("s", "a", "a"), ck_sfact),
        ))
        AB = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        BA = (_ps(1, (), "s", "a", "a"), _ps(2, (0,), "p", "a", "a"),
              _ps(0, (), "p", "a", "a"), _ps(3, (1, 2), "q", "a", "a"))
        assert key(c, _A("q", "a", "a"), AB) == kAB
        assert key(c, _A("q", "a", "a"), BA) == kBA
        _ne(key(c, _A("q", "a", "a"), AB), kBA, "K5 AB!=BA")
        c2 = c[:3] + (Clause((_A("p", "?x", "?y"), _A("p", "?z", "?x")),
                              _A("q", "?x", "?x")),)
        ABf = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
               _ps(2, (1,), "p", "a", "a"), _ps(3, (2, 0), "q", "a", "a"))
        assert key(c2, _A("q", "a", "a"), ABf) == kAB

    def test_k6_duplicate_premises(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?y")))
        ck_pfact = ("clause_key_v1", ("p", ("c", "a"), ("c", "a")), ())
        ck_sfact = ("clause_key_v1", ("s", ("c", "a"), ("c", "a")), ())
        ck_psr = ("clause_key_v1", ("p", ("v", 0), ("v", 1)),
                  (("s", ("v", 0), ("v", 1)),))
        ck_qd = ("clause_key_v1", ("q", ("v", 0), ("v", 1)),
                 (("p", ("v", 0), ("v", 1)),
                  ("p", ("v", 0), ("v", 1))))
        kAA = ("proof_key_v1", (
            (("q", "a", "a"), ck_qd),
            (("p", "a", "a"), ck_pfact),
            (("p", "a", "a"), ck_pfact),
        ))
        kAB = ("proof_key_v1", (
            (("q", "a", "a"), ck_qd),
            (("p", "a", "a"), ck_pfact),
            (("p", "a", "a"), ck_psr),
            (("s", "a", "a"), ck_sfact),
        ))
        kBB = ("proof_key_v1", (
            (("q", "a", "a"), ck_qd),
            (("p", "a", "a"), ck_psr),
            (("s", "a", "a"), ck_sfact),
            (("p", "a", "a"), ck_psr),
            (("s", "a", "a"), ck_sfact),
        ))
        AA = (_ps(0, (), "p", "a", "a"), _ps(0, (), "p", "a", "a"),
              _ps(3, (0, 1), "q", "a", "a"))
        AB = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        BA = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (2, 0), "q", "a", "a"))
        BB = (_ps(1, (), "s", "a", "a"), _ps(2, (0,), "p", "a", "a"),
              _ps(1, (), "s", "a", "a"), _ps(2, (2,), "p", "a", "a"),
              _ps(3, (1, 3), "q", "a", "a"))
        assert key(c, _A("q", "a", "a"), AA) == kAA
        assert key(c, _A("q", "a", "a"), AB) == kAB
        assert key(c, _A("q", "a", "a"), BA) == kAB
        assert key(c, _A("q", "a", "a"), BB) == kBB
        _ne(kAA, kAB, "K6 AA!=AB")
        _ne(kAB, kBB, "K6 AB!=BB")
        _ne(kAA, kBB, "K6 AA!=BB")
        assert len(kAA[1]) == 3 and len(kAB[1]) == 4 and len(kBB[1]) == 5
        shared = (_ps(0, (), "p", "a", "a"), _ps(3, (0, 0), "q", "a", "a"))
        with pytest.raises(ValueError, match="single occurrence tree"):
            key(c, _A("q", "a", "a"), shared)

    def test_k7_valid_self_rule_differs_from_fact(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("p", "?x", "?y")))
        ck_fact = ("clause_key_v1", ("p", ("c", "a"), ("c", "b")), ())
        ck_self = ("clause_key_v1", ("p", ("v", 0), ("v", 1)),
                   (("p", ("v", 0), ("v", 1)),))
        k_rule = ("proof_key_v1", (
            (("p", "a", "b"), ck_self),
            (("p", "a", "b"), ck_fact),
        ))
        k_fact = ("proof_key_v1", (
            (("p", "a", "b"), ck_fact),
        ))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "p", "a", "b"))
        fact_only = (_ps(0, (), "p", "a", "b"),)
        _ne(key(c, _A("p", "a", "b"), p), k_fact, "K7 rule!=fact")
        assert key(c, _A("p", "a", "b"), p) == k_rule
        assert key(c, _A("p", "a", "b"), fact_only) == k_fact

    def test_k8_deep_same_header(self):
        c = (_fact("q", "a", "b"), _fact("r", "b", "a"),
             _fact("q", "a", "c"), _fact("r", "c", "a"),
             Clause((_A("q", "?x", "?y"), _A("r", "?y", "?z")),
                   _A("p", "?x", "?z")),
             Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")),
                   _A("t", "?x", "?y")))
        AB = (_ps(0, (), "q", "a", "b"), _ps(1, (), "r", "b", "a"),
              _ps(4, (0, 1), "p", "a", "a"),
              _ps(2, (), "q", "a", "c"), _ps(3, (), "r", "c", "a"),
              _ps(4, (3, 4), "p", "a", "a"),
              _ps(5, (2, 5), "t", "a", "a"))
        BA = (_ps(2, (), "q", "a", "c"), _ps(3, (), "r", "c", "a"),
              _ps(4, (0, 1), "p", "a", "a"),
              _ps(0, (), "q", "a", "b"), _ps(1, (), "r", "b", "a"),
              _ps(4, (3, 4), "p", "a", "a"),
              _ps(5, (2, 5), "t", "a", "a"))
        AA = (_ps(0, (), "q", "a", "b"), _ps(1, (), "r", "b", "a"),
              _ps(4, (0, 1), "p", "a", "a"),
              _ps(0, (), "q", "a", "b"), _ps(1, (), "r", "b", "a"),
              _ps(4, (3, 4), "p", "a", "a"),
              _ps(5, (2, 5), "t", "a", "a"))
        ck_qab = ("clause_key_v1", ("q", ("c", "a"), ("c", "b")), ())
        ck_rba = ("clause_key_v1", ("r", ("c", "b"), ("c", "a")), ())
        ck_qac = ("clause_key_v1", ("q", ("c", "a"), ("c", "c")), ())
        ck_rca = ("clause_key_v1", ("r", ("c", "c"), ("c", "a")), ())
        ck_pjoin = ("clause_key_v1", ("p", ("v", 0), ("v", 1)),
                    (("q", ("v", 0), ("v", 2)), ("r", ("v", 2), ("v", 1))))
        ck_tdd = ("clause_key_v1", ("t", ("v", 0), ("v", 1)),
                  (("p", ("v", 0), ("v", 1)),
                   ("p", ("v", 0), ("v", 1))))
        kAB = ("proof_key_v1", (
            (("t", "a", "a"), ck_tdd),
            (("p", "a", "a"), ck_pjoin),
            (("q", "a", "b"), ck_qab),
            (("r", "b", "a"), ck_rba),
            (("p", "a", "a"), ck_pjoin),
            (("q", "a", "c"), ck_qac),
            (("r", "c", "a"), ck_rca),
        ))
        assert key(c, _A("t", "a", "a"), AB) == kAB
        assert key(c, _A("t", "a", "a"), BA) == kAB
        _ne(key(c, _A("t", "a", "a"), AB), key(c, _A("t", "a", "a"), AA), "K8 AB!=AA")
        hdrs = [h[0] for h in kAB[1]]
        assert hdrs == [("t", "a", "a"), ("p", "a", "a"), ("q", "a", "b"),
                        ("r", "b", "a"), ("p", "a", "a"), ("q", "a", "c"),
                        ("r", "c", "a")]


# ---------------------------------------------------------------------------
# Group B: transformations and distinctions
# ---------------------------------------------------------------------------

class TestBTransformations:
    def test_var_bijection_same(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        c2 = (_fact("p", "a", "b"),
              Clause((_A("p", "?u", "?v"),), _A("q", "?u", "?v")))
        assert key(c, _A("q", "a", "b"), p) == key(c2, _A("q", "a", "b"), p)

    def test_world_reorder_remapped_same(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        c2 = (Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")),
              _fact("p", "a", "b"))
        p2 = (_ps(1, (), "p", "a", "b"), _ps(0, (0,), "q", "a", "b"))
        assert key(c, _A("q", "a", "b"), p) == key(c2, _A("q", "a", "b"), p2)

    def test_joint_swap_two_slot_clause(self):
        # same slot content, reversed body order + matching refs; independent
        # premises so the bridge is consistent under the swap.
        cA = (_fact("p", "a", "b"), _fact("q", "a", "b"),
              Clause((_A("p", "?x", "?y"), _A("q", "?x", "?y")),
                    _A("r", "?x", "?y")))
        pA = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "a", "b"),
              _ps(2, (0, 1), "r", "a", "b"))
        cB = (_fact("q", "a", "b"), _fact("p", "a", "b"),
              Clause((_A("q", "?x", "?y"), _A("p", "?x", "?y")),
                    _A("r", "?x", "?y")))
        pB = (_ps(0, (), "q", "a", "b"), _ps(1, (), "p", "a", "b"),
              _ps(2, (0, 1), "r", "a", "b"))
        assert key(cA, _A("r", "a", "b"), pA) == key(cB, _A("r", "a", "b"), pB)

    def test_non_contiguous_topology(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("p", "?x", "?y")),
             _fact("q", "b", "c"),
             Clause((_A("q", "?x", "?y"),), _A("q", "?x", "?y")),
             Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                   _A("r", "?x", "?z")))
        # contiguous: A0,A1,B0,B1,root  (A=p-side, B=q-side)
        cont = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "p", "a", "b"),
                _ps(2, (), "q", "b", "c"), _ps(3, (2,), "q", "b", "c"),
                _ps(4, (1, 3), "r", "a", "c"))
        # interleaved: A0,B0,A1,B1,root
        interp = (_ps(0, (), "p", "a", "b"), _ps(2, (), "q", "b", "c"),
                  _ps(1, (0,), "p", "a", "b"), _ps(3, (1,), "q", "b", "c"),
                  _ps(4, (2, 3), "r", "a", "c"))
        assert key(c, _A("r", "a", "c"), cont) == key(c, _A("r", "a", "c"), interp)

    def test_k1_insert_equivalent_duplicate_same(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        c2 = (c[0], c[1], _fact("p", "a", "b"))
        p2 = (_ps(2, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        assert key(c, _A("q", "a", "b"), p) == key(c2, _A("q", "a", "b"), p2)

    def test_add_unused_clauses_same(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        c2 = (c[0], c[1],
              Clause((_A("p", "?a", "?b"),), _A("p", "?a", "?b")),
              Clause((), _A("z", "a", "b")))
        assert key(c, _A("q", "a", "b"), p) == key(c2, _A("q", "a", "b"), p)

    def test_constant_change_differs(self):
        c1 = (_fact("p", "a", "b"),
              Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p1 = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        c2 = (_fact("p", "a", "c"),
              Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p2 = (_ps(0, (), "p", "a", "c"), _ps(1, (0,), "q", "a", "c"))
        _ne(key(c1, _A("q", "a", "b"), p1), key(c2, _A("q", "a", "c"), p2))

    def test_two_bridge_supports_differ(self):
        c = (_fact("p", "a", "b"), _fact("q", "b", "c"),
             _fact("p", "a", "d"), _fact("q", "d", "c"),
             Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                   _A("r", "?x", "?z")))
        via_b = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "b", "c"),
                 _ps(4, (0, 1), "r", "a", "c"))
        via_d = (_ps(2, (), "p", "a", "d"), _ps(3, (), "q", "d", "c"),
                 _ps(4, (0, 1), "r", "a", "c"))
        _ne(key(c, _A("r", "a", "c"), via_b), key(c, _A("r", "a", "c"), via_d))

    def test_copy_inv_schema_differs(self):
        c1 = (_fact("p", "a", "a"),
              Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        c2 = (_fact("p", "a", "a"),
              Clause((_A("p", "?x", "?y"),), _A("q", "?y", "?x")))
        p1 = (_ps(0, (), "p", "a", "a"), _ps(1, (0,), "q", "a", "a"))
        p2 = (_ps(0, (), "p", "a", "a"), _ps(1, (0,), "q", "a", "a"))
        _ne(key(c1, _A("q", "a", "a"), p1), key(c2, _A("q", "a", "a"), p2))

    def test_input_purity_and_stability(self):
        c = (_fact("p", "a", "b"), _fact("q", "b", "c"),
             Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                   _A("r", "?x", "?z")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "b", "c"),
             _ps(2, (0, 1), "r", "a", "c"))
        q = _A("r", "a", "c")
        c0, q0, p0 = _copy.deepcopy(c), _copy.deepcopy(q), _copy.deepcopy(p)
        k1 = key(c, q, p)
        assert key(c, q, p) == k1
        assert c == c0 and q == q0 and p == p0
        assert k1 in {k1}
        assert {k1: 1}[k1] == 1
        assert hash(k1) == hash(key(c, q, p))

    def test_type_soundness(self):
        # K3 join: exercises top, header, ground-key, clause-key, pred,
        # arg-key, and body (two distinct premises) layers.
        c = (_fact("p", "a", "b"), _fact("q", "b", "c"),
             Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                   _A("r", "?x", "?z")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "b", "c"),
             _ps(2, (0, 1), "r", "a", "c"))
        k = key(c, _A("r", "a", "c"), p)
        assert type(k) is tuple and len(k) == 2
        assert type(k[0]) is str and k[0] == "proof_key_v1"
        assert type(k[1]) is tuple
        def _argkey(a):
            assert type(a) is tuple and len(a) == 2
            assert type(a[0]) is str and a[0] in ("c", "v")
            if a[0] == "c":
                assert type(a[1]) is str
            else:
                assert type(a[1]) is int and not isinstance(a[1], bool)
                assert a[1] >= 0
        def _predkey(pkey):
            assert type(pkey) is tuple and len(pkey) == 3
            assert type(pkey[0]) is str and not pkey[0].startswith("?")
            _argkey(pkey[1]); _argkey(pkey[2])
        for h in k[1]:
            assert type(h) is tuple and len(h) == 2
            g, ck = h
            assert type(g) is tuple and len(g) == 3
            for x in g:
                assert type(x) is str and not x.startswith("?")
            assert type(ck) is tuple and len(ck) == 3
            assert type(ck[0]) is str and ck[0] == "clause_key_v1"
            _predkey(ck[1])
            assert type(ck[2]) is tuple
            for prem in ck[2]:
                _predkey(prem)
        # a body-free fact node must exist (K3 has no fact here; check K0-style)
        c0 = (_fact("p", "a", "b"),)
        p0 = (_ps(0, (), "p", "a", "b"),)
        k0 = key(c0, _A("p", "a", "b"), p0)
        h0 = k0[1][0][1]
        assert h0[2] == ()
        assert h0[1] == ("p", ("c", "a"), ("c", "b"))

    # ---- remaining transformation-matrix entries (K3/K4/K5/K6) ----
    def test_k3_var_bijection_same(self):
        c3 = (_fact("p", "a", "b"), _fact("q", "b", "c"),
               Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                      _A("r", "?x", "?z")))
        p3 = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "b", "c"),
               _ps(2, (0, 1), "r", "a", "c"))
        c3r = (_fact("p", "a", "b"), _fact("q", "b", "c"),
                Clause((_A("p", "?i", "?j"), _A("q", "?j", "?k")),
                       _A("r", "?i", "?k")))
        p3r = p3
        assert verify_proof(c3r, _A("r", "a", "c"), p3r) is True
        assert key(c3, _A("r", "a", "c"), p3) == key(c3r, _A("r", "a", "c"), p3r)

    def test_k5_var_bijection_same(self):
        c5 = (_fact("p", "a", "a"), _fact("s", "a", "a"),
               Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
               Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                      _A("q", "?x", "?x")))
        p5 = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
               _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        c5r = (_fact("p", "a", "a"), _fact("s", "a", "a"),
                Clause((_A("s", "?i", "?j"),), _A("p", "?i", "?j")),
                Clause((_A("p", "?k", "?i"), _A("p", "?i", "?j")),
                       _A("q", "?i", "?i")))
        p5r = p5
        assert verify_proof(c5r, _A("q", "a", "a"), p5r) is True
        assert key(c5, _A("q", "a", "a"), p5) == key(c5r, _A("q", "a", "a"), p5r)

    def test_k6_var_bijection_same(self):
        c6 = (_fact("p", "a", "a"), _fact("s", "a", "a"),
               Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
               Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")),
                      _A("q", "?x", "?y")))
        p6 = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
               _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        c6r = (_fact("p", "a", "a"), _fact("s", "a", "a"),
                Clause((_A("s", "?i", "?j"),), _A("p", "?i", "?j")),
                Clause((_A("p", "?i", "?j"), _A("p", "?i", "?j")),
                       _A("q", "?i", "?j")))
        p6r = p6
        assert verify_proof(c6r, _A("q", "a", "a"), p6r) is True
        assert key(c6, _A("q", "a", "a"), p6) == key(c6r, _A("q", "a", "a"), p6r)

    def test_k4_world_reorder_remapped_same(self):
        c4 = (_fact("p", "a", "b"), _fact("p", "a", "c"),
               Clause((_A("p", "?x", "?z"), _A("p", "?x", "?w")),
                      _A("q", "?x", "?x")))
        p4 = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "c"),
               _ps(2, (0, 1), "q", "a", "a"))
        c4r, p4r = _reorder_world(c4, p4, perm=(1, 0, 2))
        assert verify_proof(c4r, _A("q", "a", "a"), p4r) is True
        assert key(c4, _A("q", "a", "a"), p4) == key(c4r, _A("q", "a", "a"), p4r)

    def test_k5_world_reorder_remapped_same(self):
        c5 = (_fact("p", "a", "a"), _fact("s", "a", "a"),
               Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
               Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                      _A("q", "?x", "?x")))
        p5 = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
               _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        c5r, p5r = _reorder_world(c5, p5, perm=(1, 0, 2, 3))
        assert verify_proof(c5r, _A("q", "a", "a"), p5r) is True
        assert key(c5, _A("q", "a", "a"), p5) == key(c5r, _A("q", "a", "a"), p5r)

    def test_k6_world_reorder_remapped_same(self):
        c6 = (_fact("p", "a", "a"), _fact("s", "a", "a"),
               Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
               Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")),
                      _A("q", "?x", "?y")))
        p6 = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
               _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        c6r, p6r = _reorder_world(c6, p6, perm=(1, 0, 2, 3))
        assert verify_proof(c6r, _A("q", "a", "a"), p6r) is True
        assert key(c6, _A("q", "a", "a"), p6) == key(c6r, _A("q", "a", "a"), p6r)

    def test_k5_ab_ba_two_orderings(self):
        # K5 AB is hand-checked in A; the BA ordering is a different legal layout
        # of the SAME non-symmetric tree, and both are real verifiable proofs.
        c5 = (_fact("p", "a", "a"), _fact("s", "a", "a"),
               Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
               Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                      _A("q", "?x", "?x")))
        p_ab = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
                _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        p_ba = (_ps(1, (), "s", "a", "a"), _ps(2, (0,), "p", "a", "a"),
                _ps(0, (), "p", "a", "a"), _ps(3, (1, 2), "q", "a", "a"))
        assert verify_proof(c5, _A("q", "a", "a"), p_ab) is True
        assert verify_proof(c5, _A("q", "a", "a"), p_ba) is True
        k_ab = key(c5, _A("q", "a", "a"), p_ab)
        k_ba = key(c5, _A("q", "a", "a"), p_ba)
        assert k_ab is not None and k_ba is not None
        # (A group proves k_ab != k_ba for the degenerate non-symmetric tree;)
        # both orderings are real, verifiable, and each maps to its own key.

    def test_duplicate_copy_source_k1_new_index(self):
        # a fully identical COPY of the fact at a new mid index: the proof must
        # be re-derived from that copy, yet the full key is unchanged.
        c1 = (_fact("p", "a", "b"),
               Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p1 = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        c2 = (c1[0], _fact("p", "a", "b"), c1[1])
        # the COPY sits at clause index 1; the proof derives the COPY as the
        # (earlier) step and then the rule from it, so the ref targets index 0
        p2 = (_ps(1, (), "p", "a", "b"), _ps(2, (0,), "q", "a", "b"))
        assert verify_proof(c2, _A("q", "a", "b"), p2) is True
        assert key(c1, _A("q", "a", "b"), p1) == key(c2, _A("q", "a", "b"), p2)

    def test_actual_case_differ(self):
        # actual symbols are case-sensitive: same shape, different actual case ->
        # different keys (guards the lowercase_actual_symbols mutation).
        c1 = (_fact("Foo", "a", "b"),
               Clause((_A("Foo", "?x", "?y"),), _A("Bar", "?x", "?y")))
        p1 = (_ps(0, (), "Foo", "a", "b"), _ps(1, (0,), "Bar", "a", "b"))
        c2 = (_fact("foo", "a", "b"),
               Clause((_A("foo", "?x", "?y"),), _A("Bar", "?x", "?y")))
        p2 = (_ps(0, (), "foo", "a", "b"), _ps(1, (0,), "Bar", "a", "b"))
        assert verify_proof(c1, _A("Bar", "a", "b"), p1) is True
        assert verify_proof(c2, _A("Bar", "a", "b"), p2) is True
        _ne(key(c1, _A("Bar", "a", "b"), p1), key(c2, _A("Bar", "a", "b"), p2), "case differs")

    def test_asymmetric_rename_differ(self):
        # an asymmetric chain-variable split (not a uniform rename) is a different
        # actual structure; both still prove the same ground query.
        c_sym = (_fact("p", "a", "b"), _fact("p", "b", "c"),
                   Clause((_A("p", "?x", "?y"), _A("p", "?y", "?z")),
                          _A("q", "?x", "?z")))
        p_sym = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "b", "c"),
                  _ps(2, (0, 1), "q", "a", "c"))
        c_asym = (_fact("p", "a", "b"), _fact("p", "b", "c"),
                   Clause((_A("p", "?x", "?m"), _A("p", "?y", "?z")),
                          _A("q", "?x", "?z")))
        p_asym = p_sym
        assert verify_proof(c_sym, _A("q", "a", "c"), p_sym) is True
        assert verify_proof(c_asym, _A("q", "a", "c"), p_asym) is True
        _ne(key(c_sym, _A("q", "a", "c"), p_sym),
            key(c_asym, _A("q", "a", "c"), p_asym), "asym rename differs")

    def test_cross_fixture_stability_purity(self):
        # K3 -> K0 -> K5 -> K3: first and last keys identical (stateless);
        # inputs unmutated and hash-stable across the sequence.
        k3c = (_fact("p", "a", "b"), _fact("q", "b", "c"),
               Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                      _A("r", "?x", "?z")))
        k3p = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "b", "c"),
               _ps(2, (0, 1), "r", "a", "c"))
        k0c = (_fact("p", "a", "b"),)
        k0p = (_ps(0, (), "p", "a", "b"),)
        k5c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
               Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
               Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                      _A("q", "?x", "?x")))
        k5p = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
               _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        k3a = key(k3c, _A("r", "a", "c"), k3p)
        key(k0c, _A("p", "a", "b"), k0p)
        key(k5c, _A("q", "a", "a"), k5p)
        k3b = key(k3c, _A("r", "a", "c"), k3p)
        assert k3a == k3b
        # input hash/fields unchanged across the sequence
        h_a = hash((k3c, _A("r", "a", "c"), k3p))
        h_b = hash((k3c, _A("r", "a", "c"), k3p))
        assert h_a == h_b
        k3c0 = key(_copy.deepcopy(k3c), _A("r", "a", "c"), _copy.deepcopy(k3p))
        assert k3c0 == k3a

# ---------------------------------------------------------------------------
# Group C: independent small oracle + T0009 enumeration cross-check
# ---------------------------------------------------------------------------

def _build_nodes(clauses, proof):
    nodes = [None] * len(proof)
    for i, step in enumerate(proof):
        clause = clauses[step.clause_index]
        child_nodes = tuple(nodes[j] for j in step.premise_steps)
        nodes[i] = (step.conclusion, clause.head, clause.body, child_nodes)
    return nodes


def _atom_match(a1, a2, sigma):
    if a1.pred != a2.pred:
        return False
    for arg1, arg2 in zip(a1.args, a2.args):
        if arg1.startswith("?"):
            if arg2 != sigma.get(arg1):
                return False
        elif arg2 != arg1:
            return False
    return True


def _sigmas(v1, v2):
    if len(v1) != len(v2):
        return []
    return [{a: perm[i] for i, a in enumerate(sorted(v1))}
            for perm in itertools.permutations(v2)]


def oracle_equiv(n1, n2):
    """Brute-force structural equivalence for small occurrence trees."""
    if n1[0] != n2[0]:
        return False
    h1, b1, ch1 = n1[1], n1[2], n1[3]
    h2, b2, ch2 = n2[1], n2[2], n2[3]
    if len(b1) != len(b2):
        return False
    v1 = {arg for a in (h1, *b1) for arg in a.args if arg.startswith("?")}
    v2 = {arg for a in (h2, *b2) for arg in a.args if arg.startswith("?")}
    for perm in itertools.permutations(range(len(b1))):
        atom_pairs = [(h1, h2)] + [(b1[i], b2[perm[i]]) for i in range(len(b1))]
        child_pairs = [(ch1[i], ch2[perm[i]]) for i in range(len(b1))]
        for sigma in _sigmas(v1, v2):
            if all(_atom_match(*p, sigma) for p in atom_pairs) \
                    and all(oracle_equiv(ck1, ck2) for ck1, ck2 in child_pairs):
                return True
    return False


class TestCOracleAndEnumeration:
    def test_k1_oracle_matches(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p1 = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        c2 = (_fact("p", "a", "b"),
              Clause((_A("p", "?u", "?v"),), _A("q", "?u", "?v")))
        assert verify_proof(c2, _A("q", "a", "b"), p1) is True
        assert oracle_equiv(_build_nodes(c, p1)[-1], _build_nodes(c2, p1)[-1])
        assert key(c, _A("q", "a", "b"), p1) == key(c2, _A("q", "a", "b"), p1)

    def test_k3_world_reorder_oracle(self):
        c = (_fact("p", "a", "b"), _fact("q", "b", "c"),
             Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                   _A("r", "?x", "?z")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "b", "c"),
             _ps(2, (0, 1), "r", "a", "c"))
        c2 = (_fact("q", "b", "c"), _fact("p", "a", "b"),
              Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                    _A("r", "?x", "?z")))
        p2 = (_ps(0, (), "q", "b", "c"), _ps(1, (), "p", "a", "b"),
              _ps(2, (1, 0), "r", "a", "c"))
        assert verify_proof(c2, _A("r", "a", "c"), p2) is True
        assert oracle_equiv(_build_nodes(c, p)[-1], _build_nodes(c2, p2)[-1])
        assert key(c, _A("r", "a", "c"), p) == key(c2, _A("r", "a", "c"), p2)

    def test_k4_var_rename_oracle(self):
        c = (_fact("p", "a", "b"), _fact("p", "a", "c"),
             Clause((_A("p", "?x", "?z"), _A("p", "?x", "?w")),
                   _A("q", "?x", "?x")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "c"),
             _ps(2, (0, 1), "q", "a", "a"))
        c2 = (c[0], c[1],
              Clause((_A("p", "?u", "?z"), _A("p", "?u", "?w")),
                    _A("q", "?u", "?u")))
        p2 = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "c"),
              _ps(2, (0, 1), "q", "a", "a"))
        assert verify_proof(c2, _A("q", "a", "a"), p2) is True
        assert oracle_equiv(_build_nodes(c, p)[-1], _build_nodes(c2, p2)[-1])
        assert key(c, _A("q", "a", "a"), p) == key(c2, _A("q", "a", "a"), p2)

    def test_k5_two_supports_oracle(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?x")))
        AB = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        BA = (_ps(1, (), "s", "a", "a"), _ps(2, (0,), "p", "a", "a"),
              _ps(0, (), "p", "a", "a"), _ps(3, (1, 2), "q", "a", "a"))
        assert verify_proof(c, _A("q", "a", "a"), AB) is True
        assert verify_proof(c, _A("q", "a", "a"), BA) is True
        assert not oracle_equiv(_build_nodes(c, AB)[-1], _build_nodes(c, BA)[-1])
        assert key(c, _A("q", "a", "a"), AB) != key(c, _A("q", "a", "a"), BA)

    def test_k6_ab_vs_aa_and_ba_oracle(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?y")))
        AA = (_ps(0, (), "p", "a", "a"), _ps(0, (), "p", "a", "a"),
              _ps(3, (0, 1), "q", "a", "a"))
        AB = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        BA = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (2, 0), "q", "a", "a"))
        assert verify_proof(c, _A("q", "a", "a"), AA) is True
        assert verify_proof(c, _A("q", "a", "a"), AB) is True
        assert verify_proof(c, _A("q", "a", "a"), BA) is True
        # AB vs AA: different support -> not equivalent.
        assert not oracle_equiv(_build_nodes(c, AA)[-1], _build_nodes(c, AB)[-1])
        assert key(c, _A("q", "a", "a"), AA) != key(c, _A("q", "a", "a"), AB)
        # AB vs BA: duplicate premises -> equivalent (joint swap).
        assert oracle_equiv(_build_nodes(c, AB)[-1], _build_nodes(c, BA)[-1])
        assert key(c, _A("q", "a", "a"), AB) == key(c, _A("q", "a", "a"), BA)

    def test_k8_successor_and_branch_oracle(self):
        c = (_fact("q", "a", "b"), _fact("r", "b", "a"),
             _fact("q", "a", "c"), _fact("r", "c", "a"),
             Clause((_A("q", "?x", "?y"), _A("r", "?y", "?z")),
                   _A("p", "?x", "?z")),
             Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")),
                   _A("t", "?x", "?y")))
        AB = (_ps(0, (), "q", "a", "b"), _ps(1, (), "r", "b", "a"),
              _ps(4, (0, 1), "p", "a", "a"),
              _ps(2, (), "q", "a", "c"), _ps(3, (), "r", "c", "a"),
              _ps(4, (3, 4), "p", "a", "a"),
              _ps(5, (2, 5), "t", "a", "a"))
        AA = (_ps(0, (), "q", "a", "b"), _ps(1, (), "r", "b", "a"),
              _ps(4, (0, 1), "p", "a", "a"),
              _ps(0, (), "q", "a", "b"), _ps(1, (), "r", "b", "a"),
              _ps(4, (3, 4), "p", "a", "a"),
              _ps(5, (2, 5), "t", "a", "a"))
        BA = (_ps(2, (), "q", "a", "c"), _ps(3, (), "r", "c", "a"),
              _ps(4, (0, 1), "p", "a", "a"),
              _ps(0, (), "q", "a", "b"), _ps(1, (), "r", "b", "a"),
              _ps(4, (3, 4), "p", "a", "a"),
              _ps(5, (2, 5), "t", "a", "a"))
        # same header, different successors -> not equivalent (oracle called).
        assert not oracle_equiv(_build_nodes(c, AB)[-1], _build_nodes(c, AA)[-1])
        assert key(c, _A("t", "a", "a"), AB) != key(c, _A("t", "a", "a"), AA)
        # branch reorder -> equivalent.
        assert oracle_equiv(_build_nodes(c, AB)[-1], _build_nodes(c, BA)[-1])
        assert key(c, _A("t", "a", "a"), AB) == key(c, _A("t", "a", "a"), BA)

    def test_joint_body_ref_swap_oracle(self):
        # K3-style two-slot joint: same slot contents, reversed body + matching refs.
        cA = (_fact("p", "a", "b"), _fact("q", "a", "b"),
              Clause((_A("p", "?x", "?y"), _A("q", "?x", "?y")),
                    _A("r", "?x", "?y")))
        pA = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "a", "b"),
              _ps(2, (0, 1), "r", "a", "b"))
        cB = (_fact("q", "a", "b"), _fact("p", "a", "b"),
              Clause((_A("q", "?x", "?y"), _A("p", "?x", "?y")),
                    _A("r", "?x", "?y")))
        pB = (_ps(0, (), "q", "a", "b"), _ps(1, (), "p", "a", "b"),
              _ps(2, (0, 1), "r", "a", "b"))
        assert verify_proof(cA, _A("r", "a", "b"), pA) is True
        assert verify_proof(cB, _A("r", "a", "b"), pB) is True
        assert oracle_equiv(_build_nodes(cA, pA)[-1], _build_nodes(cB, pB)[-1])
        assert key(cA, _A("r", "a", "b"), pA) == key(cB, _A("r", "a", "b"), pB)

    def test_t0009_k5_per_tree_full_keyset(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?x")))
        q = _A("q", "a", "a")
        ck_q = ("clause_key_v1", ("q", ("v", 0), ("v", 0)),
                (("p", ("v", 0), ("v", 1)), ("p", ("v", 2), ("v", 0))))
        ck_pf = ("clause_key_v1", ("p", ("c", "a"), ("c", "a")), ())
        ck_ps = ("clause_key_v1", ("p", ("v", 0), ("v", 1)),
                 (("s", ("v", 0), ("v", 1)),))
        ck_sf = ("clause_key_v1", ("s", ("c", "a"), ("c", "a")), ())
        expected = {
            ("proof_key_v1", (
                (("q", "a", "a"), ck_q),
                (("p", "a", "a"), ck_pf),
                (("p", "a", "a"), ck_pf),
            )),
            ("proof_key_v1", (
                (("q", "a", "a"), ck_q),
                (("p", "a", "a"), ck_ps),
                (("s", "a", "a"), ck_sf),
                (("p", "a", "a"), ck_pf),
            )),
            ("proof_key_v1", (
                (("q", "a", "a"), ck_q),
                (("p", "a", "a"), ck_pf),
                (("p", "a", "a"), ck_ps),
                (("s", "a", "a"), ck_sf),
            )),
            ("proof_key_v1", (
                (("q", "a", "a"), ck_q),
                (("p", "a", "a"), ck_ps),
                (("s", "a", "a"), ck_sf),
                (("p", "a", "a"), ck_ps),
                (("s", "a", "a"), ck_sf),
            )),
        }
        trees = enumerate_proofs(c, q,
                                 max_fact_checks=3, max_derivations=4,
                                 max_proof_steps=20)
        assert len(trees) == 4
        got = set()
        for t in trees:
            assert verify_proof(c, q, t) is True
            got.add(key(c, q, t))
        assert got == expected
        assert len(got) == 4

    def test_t0009_k6_per_tree_full_keyset(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?y")))
        q = _A("q", "a", "a")
        ck_q = ("clause_key_v1", ("q", ("v", 0), ("v", 1)),
                 (("p", ("v", 0), ("v", 1)), ("p", ("v", 0), ("v", 1))))
        ck_pf = ("clause_key_v1", ("p", ("c", "a"), ("c", "a")), ())
        ck_ps = ("clause_key_v1", ("p", ("v", 0), ("v", 1)),
                 (("s", ("v", 0), ("v", 1)),))
        ck_sf = ("clause_key_v1", ("s", ("c", "a"), ("c", "a")), ())
        expected = {
            ("proof_key_v1", (
                (("q", "a", "a"), ck_q),
                (("p", "a", "a"), ck_pf),
                (("p", "a", "a"), ck_pf),
            )),
            ("proof_key_v1", (
                (("q", "a", "a"), ck_q),
                (("p", "a", "a"), ck_pf),
                (("p", "a", "a"), ck_ps),
                (("s", "a", "a"), ck_sf),
            )),
            ("proof_key_v1", (
                (("q", "a", "a"), ck_q),
                (("p", "a", "a"), ck_ps),
                (("s", "a", "a"), ck_sf),
                (("p", "a", "a"), ck_ps),
                (("s", "a", "a"), ck_sf),
            )),
        }
        trees = enumerate_proofs(c, q,
                                 max_fact_checks=3, max_derivations=4,
                                 max_proof_steps=20)
        assert len(trees) == 4
        got = set()
        for t in trees:
            assert verify_proof(c, q, t) is True
            got.add(key(c, q, t))
        assert got == expected
        assert len(got) == 3


# ---------------------------------------------------------------------------
# Group D: errors, priority, and call boundary
# ---------------------------------------------------------------------------

class TestDErrors:
    # ---- product-raised messages: exact class + full text ----
    def test_empty_proof_valid_message(self):
        c = (_fact("p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), ())
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "proof_key.proof must be a valid proof of query"

    def test_wrong_query_valid_message(self):
        c = (_fact("q", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("q", "a", "b"), p)
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "proof_key.proof must be a valid proof of query"

    def test_invalid_derivation_valid_message(self):
        c = (_fact("p", "a", "b"), _fact("q", "a", "b"))
        p = (_ps(0, (), "p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("q", "a", "b"), p)
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "proof_key.proof must be a valid proof of query"

    # ---- single-occurrence tree: real verifier True first, then reject ----
    def test_shared_tree_verifier_true_then_reject(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")), _A("q", "?x", "?y")))
        shared = (_ps(0, (), "p", "a", "a"), _ps(3, (0, 0), "q", "a", "a"))
        assert verify_proof(c, _A("q", "a", "a"), shared) is True
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("q", "a", "a"), shared)
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "proof_key.proof must be a single occurrence tree"

    def test_unused_legal_step_rejected(self):
        # legal but unreferenced (ref 0) and non-final must be rejected
        c = (_fact("p", "a", "b"), _fact("p", "a", "b"))
        query = _A("p", "a", "b")
        proof = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "b"))
        assert verify_proof(c, query, proof) is True
        with pytest.raises(LogicValidationError) as e:
            key(c, query, proof)
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "proof_key.proof must be a single occurrence tree"

    # ---- world illegal inputs via the NEW API, exact class + full message ----
    def test_clauses_list_rejected_by_product(self):
        # the product must not coerce clauses to a tuple
        c = [_fact("p", "a", "b")]
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), (_ps(0, (), "p", "a", "b"),))
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "verify.clauses must be a tuple of Clause, got list"

    def test_clauses_member_rejected(self):
        c = (5,)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), ())
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "verify.clauses[0] must be a Clause, got int"

    def test_query_type_rejected(self):
        c = (_fact("p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, "p", ())
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "verify.query must be an Atom, got str"

    def test_query_nonground_rejected(self):
        c = (_fact("p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "?x", "?y"), ())
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "verify.query must be a ground Atom"

    def test_proof_outer_rejected(self):
        # proof outer must be a tuple; a single ProofStep and a generator both
        # fail.  The generator carries a marker set only inside its body, so a
        # pre-scan (nexting it before the type check) would flip it; after a
        # rejected call the marker must still be empty.
        c = (_fact("p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), _ps(0, (), "p", "a", "b"))
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "verify.proof must be a tuple of ProofStep, got ProofStep"
        consumed = []
        def gen():
            consumed.append(True)
            yield _ps(0, (), "p", "a", "b")
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), gen())
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "verify.proof must be a tuple of ProofStep, got generator"
        assert consumed == [], "generator was nexted before rejection (pre-scan)"

    def test_proof_member_rejected(self):
        c = (_fact("p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), (("p", "a", "b"),))
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "verify.proof[0] must be a ProofStep, got tuple"

    def test_max_steps_rejected_exact(self):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        for bad, got in ((True, "bool"), (0, "int"), (-1, "int"), (1.5, "float")):
            with pytest.raises(LogicValidationError) as e:
                key(c, _A("p", "a", "b"), p, max_steps=bad)
            assert type(e.value) is LogicValidationError
            assert str(e.value) == (f"verify.max_steps must be a non-bool positive "
                                     f"integer, got {got}")

    # ---- budget: huge int accepted under a low int->str digit limit ----
    @pytest.fixture
    def _int_str_limit_4300(self):
        old = None
        if hasattr(sys, "set_int_max_str_digits"):
            old = sys.get_int_max_str_digits()
            sys.set_int_max_str_digits(4300)
        try:
            yield
        finally:
            if old is not None:
                sys.set_int_max_str_digits(old)

    def test_huge_int_budget_boundary(self, _int_str_limit_4300):
        # 10**5000 has ~5001 digits (> 4300); short ids keep any message free
        # of the value.  A buggy int->str on the budget would raise ValueError
        # instead of the precise verifier errors below.
        large = 10 ** 5000
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        # illegal proof outer: a bare int (exact error, short ids)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), large)
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "verify.proof must be a tuple of ProofStep, got int"
        # negative budget
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), p, max_steps=-large)
        assert type(e.value) is LogicValidationError
        assert str(e.value) == ("verify.max_steps must be a non-bool positive "
                                 "integer, got int")
        # huge positive budget is accepted
        assert key(c, _A("p", "a", "b"), p, max_steps=large) is not None

    # ---- original signature regression (missing / extra / unknown) ----
    def test_missing_proof_typeerror(self):
        c = (_fact("p", "a", "b"),)
        with pytest.raises(TypeError):
            canonical_proof_key(c, _A("p", "a", "b"))

    def test_extra_positional_typeerror(self):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        with pytest.raises(TypeError):
            canonical_proof_key(c, _A("p", "a", "b"), p, "extra")

    def test_unknown_keyword_typeerror(self):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        with pytest.raises(TypeError):
            canonical_proof_key(c, _A("p", "a", "b"), p, maxstep=5)

    # ---- clauses outer illegal reported before a bad proof member ----
    def test_clauses_before_bad_proof_member(self):
        # an illegal clauses outer must be raised before any per-layer proof scan
        c = [_fact("p", "a", "b")]  # illegal: clauses is a list
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), ("not-a-step",))
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "verify.clauses must be a tuple of Clause, got list"

    def test_proof_limit_priority(self):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "p", "a", "b"))
        with pytest.raises(ProofLimitError) as e:
            key(c, _A("p", "a", "b"), p, max_steps=1)
        assert type(e.value) is ProofLimitError
        assert str(e.value) == "verify.proof length exceeds verify.max_steps"

    def test_semantic_before_single_occurrence(self):
        # semantic-invalid (final != query) raises before the single-occurrence check;
        # a bad ref_count must not mask the invalid-proof message.
        c = (_fact("p", "a", "b"), _fact("p", "a", "b"))
        query = _A("q", "a", "b")
        proof = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "b"))
        assert not verify_proof(c, query, proof)
        with pytest.raises(LogicValidationError) as e:
            key(c, query, proof)
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "proof_key.proof must be a valid proof of query"
        assert "single occurrence tree" not in str(e.value)

    def test_length_before_bad_member(self):
        # length check runs before per-member type checks: over-limit with a bad
        # member yields ProofLimitError, not the member type error.
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"), "not-a-step", _ps(2, (), "p", "a", "b"))
        with pytest.raises(ProofLimitError) as e:
            key(c, _A("p", "a", "b"), p, max_steps=2)
        assert type(e.value) is ProofLimitError
        assert str(e.value) == "verify.proof length exceeds verify.max_steps"

    # ---- named sentinels: exc.value is sentinel (identity), not __suppress_context__
    def test_prooflimit_sentinel_is(self, monkeypatch):
        import kmesh.logic.proof_key as pk_mod
        c = (_fact("p", "a", "b"),)
        q = _A("p", "a", "b")
        p = (_ps(0, (), "p", "a", "b"),)
        sentinel = ProofLimitError("verify.proof length exceeds verify.max_steps")
        calls = []
        def spy(*args, **kw):
            calls.append((args, kw))
            raise sentinel
        monkeypatch.setattr(pk_mod, "verify_proof", spy)
        with pytest.raises(ProofLimitError) as e:
            canonical_proof_key(c, q, p, max_steps=7)
        assert e.value is sentinel
        assert str(e.value) == "verify.proof length exceeds verify.max_steps"
        assert len(calls) == 1
        args, kw = calls[0]
        assert args[0] is c and args[1] is q and args[2] is p
        assert kw["max_steps"] == 7

    def test_verify_logic_sentinel_is(self, monkeypatch):
        import kmesh.logic.proof_key as pk_mod
        c = [_fact("p", "a", "b")]
        sentinel = LogicValidationError("verify.clauses must be a tuple of Clause, got list")
        calls = []
        def spy(*args, **kw):
            calls.append((args, kw))
            raise sentinel
        monkeypatch.setattr(pk_mod, "verify_proof", spy)
        with pytest.raises(LogicValidationError) as e:
            canonical_proof_key(c, _A("p", "a", "b"),
                                (_ps(0, (), "p", "a", "b"),), max_steps=7)
        assert e.value is sentinel
        assert str(e.value) == "verify.clauses must be a tuple of Clause, got list"
        assert len(calls) == 1
        assert calls[0][0][0] is c
        assert calls[0][1]["max_steps"] == 7

    def test_false_message(self, monkeypatch):
        # verify_proof returns False (no raise): the product raises its own
        # LogicValidationError; check class + exact message, checked separately.
        import kmesh.logic.proof_key as pk_mod
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        calls = []
        def spy(*args, **kw):
            calls.append((args, kw))
            return False
        monkeypatch.setattr(pk_mod, "verify_proof", spy)
        with pytest.raises(LogicValidationError) as e:
            canonical_proof_key(c, _A("p", "a", "b"), p, max_steps=7)
        assert type(e.value) is LogicValidationError
        assert str(e.value) == "proof_key.proof must be a valid proof of query"
        assert len(calls) == 1
        assert calls[0][0][0] is c
        assert calls[0][1]["max_steps"] == 7

    def test_module_all(self):
        import kmesh.logic.proof_key as _pk
        assert _pk.__all__ == ["canonical_proof_key"]

# ---------------------------------------------------------------------------
# Group E: long chain, output shape, import isolation
# ---------------------------------------------------------------------------

class TestELongAndIsolation:
    def test_long_chain_1201(self):
        # A 1201-node chain of DISTINCT relations: a0 (fact) -> a1 -> a2 ->
        # ... -> a1200.  Unlike a self-loop rule repeated, every node has a
        # different predicate, and every header (not just the last) is checked
        # against the hand-derived clause-key form.
        n = 1200
        clauses = [_fact("a0", "a", "b")]
        for k in range(1, n + 1):
            clauses.append(Clause((_A(f"a{k-1}", "?x", "?y"),),
                                   _A(f"a{k}", "?x", "?y")))
        clauses = tuple(clauses)
        proof = [_ps(0, (), "a0", "a", "b")]
        for k in range(1, n + 1):
            proof.append(_ps(k, (k - 1,), f"a{k}", "a", "b"))
        proof = tuple(proof)
        q = _A(f"a{n}", "a", "b")
        kkey = key(clauses, q, proof, max_steps=n + 1)
        assert len(kkey[1]) == n + 1

        def exp_ck(i):
            if i == 0:
                return ("clause_key_v1", ("a0", ("c", "a"), ("c", "b")), ())
            return ("clause_key_v1", (f"a{i}", ("v", 0), ("v", 1)),
                    ((f"a{i-1}", ("v", 0), ("v", 1)),))

        for pos in range(n + 1):
            i = n - pos  # relation index, from n down to 0
            g, ck = kkey[1][pos]
            exp_gk = ("a0", "a", "b") if i == 0 else (f"a{i}", "a", "b")
            assert g == exp_gk, f"node {pos}: gk {g!r} != {exp_gk!r}"
            assert ck == exp_ck(i), f"node {pos}: ck mismatch"

        # stable, hashable, distinct from a strict 2-step prefix chain
        kkey2 = key(clauses, q, proof, max_steps=n + 1)
        assert kkey == kkey2
        assert {kkey: "x"}[kkey] == "x"
        short = key(clauses[:2], _A("a1", "a", "b"),
                    (_ps(0, (), "a0", "a", "b"),
                     _ps(1, (0,), "a1", "a", "b")), max_steps=2)
        assert kkey != short
        assert len(sorted([kkey, short])) == 2
        with pytest.raises(ProofLimitError):
            key(clauses, q, proof, max_steps=n)

    def test_import_isolation_hard_block(self):
        """Hard import isolation via a sys.meta_path finder (not try/except or
        direct ``find_spec`` impersonation).

        For each of the eight original forbidden roots (``torch``, ``yaml`` and
        the six ``kmesh.logic`` submodules ``engine``, ``reference_engine``,
        ``dependency``, ``derivations``, ``proof_enumeration``, ``depth``) a
        fresh subprocess installs the finder and:
        - imports the whitelisted product, asserts the submitted ``src`` file
          path exactly, and runs the K0 / K3 / real-K5(AB,BA) exercises with
          the real verifier;
        - scans ``sys.modules`` for any forbidden root or root-prefixed entry;
        - imports the root itself, asserting the full ``isolated-blocked:
          <name>`` message; and
        - imports a probe ``<root>._t0012_probe`` through a placeholder package
          (with ``__path__``), asserting the full message, then cleans up.
        The block is checked by the real import machinery, never by hand-calling
        ``find_spec``.
        """
        import subprocess, sys, os
        from pathlib import Path as _Path
        repo_root = _Path(__file__).resolve().parents[1]
        src = (repo_root / "src").resolve()
        product_file = (src / "kmesh" / "logic" / "proof_key.py").resolve()
        roots = (
            "torch",
            "yaml",
            "kmesh.logic.engine",
            "kmesh.logic.reference_engine",
            "kmesh.logic.dependency",
            "kmesh.logic.derivations",
            "kmesh.logic.proof_enumeration",
            "kmesh.logic.depth",
        )
        exercise = [
            'from kmesh.logic.proof_key import canonical_proof_key',
            'from kmesh.logic.types import Atom, Clause',
            'from kmesh.logic.proof import ProofStep, verify_proof',
            'assert os.path.realpath(sys.modules["kmesh.logic.proof_key"].__file__) == os.path.realpath(os.environ["KMESH_SRC"] + "/kmesh/logic/proof_key.py"), sys.modules["kmesh.logic.proof_key"].__file__'  ,
            'def fact(p, a, b):',
            '    return Clause((), Atom(p, (a, b)))',
            'def atom(p, x, y):',
            '    return Atom(p, (x, y))',
            'k0 = canonical_proof_key((fact("p","a","b"),), atom("p","a","b"), (ProofStep(0, (), atom("p","a","b")),))',
            'assert type(k0) is tuple and k0[0] == "proof_key_v1" and k0[1][0][0] == ("p","a","b"), k0',
            'c3a = (fact("p","a","b"), fact("q","b","c"), Clause((atom("p","?x","?y"), atom("q","?y","?z")), atom("r","?x","?z")))',
            'p3a = (ProofStep(0, (), atom("p","a","b")), ProofStep(1, (), atom("q","b","c")), ProofStep(2, (0, 1), atom("r","a","c")))',
            'assert verify_proof(c3a, atom("r","a","c"), p3a) is True',
            'k3a = canonical_proof_key(c3a, atom("r","a","c"), p3a)',
            'c3b = (fact("q","b","c"), fact("p","a","b"), Clause((atom("p","?x","?y"), atom("q","?y","?z")), atom("r","?x","?z")))',
            'p3b = (ProofStep(0, (), atom("q","b","c")), ProofStep(1, (), atom("p","a","b")), ProofStep(2, (1, 0), atom("r","a","c")))',
            'assert verify_proof(c3b, atom("r","a","c"), p3b) is True',
            'k3b = canonical_proof_key(c3b, atom("r","a","c"), p3b)',
            'assert k3a == k3b',
            'c5 = (fact("p","a","a"), fact("s","a","a"), Clause((atom("s","?x","?y"),), atom("p","?x","?y")), Clause((atom("p","?z","?x"), atom("p","?x","?y")), atom("q","?x","?x")))',
            'p5ab = (ProofStep(0, (), atom("p","a","a")), ProofStep(1, (), atom("s","a","a")), ProofStep(2, (1,), atom("p","a","a")), ProofStep(3, (0, 2), atom("q","a","a")))',
            'p5ba = (ProofStep(1, (), atom("s","a","a")), ProofStep(2, (0,), atom("p","a","a")), ProofStep(0, (), atom("p","a","a")), ProofStep(3, (1, 2), atom("q","a","a")))',
            'assert verify_proof(c5, atom("q","a","a"), p5ab) is True',
            'assert verify_proof(c5, atom("q","a","a"), p5ba) is True',
            'k5a = canonical_proof_key(c5, atom("q","a","a"), p5ab)',
            'k5b = canonical_proof_key(c5, atom("q","a","a"), p5ba)',
            'assert k5a != k5b',
            'for _fr in %r:' % list(roots),
            '    assert _fr not in sys.modules, "forbidden already loaded: " + repr(_fr)',
            '    for _k in list(sys.modules):',
            '        if _k == _fr or _k.startswith(_fr + "."):',
            '            raise SystemExit("forbidden prefix in sys.modules: " + repr(_k))',
        ]
        for root in roots:
            code_lines = [
                'import sys, os, importlib, types',
                'WHITELIST = {"kmesh", "kmesh.logic", "kmesh.logic.types",',
                '              "kmesh.logic.proof", "kmesh.logic.proof_key"}',
                'FORBIDDEN_TOP = ("torch", "yaml")',
                'class BlockFinder:',
                '    def find_spec(self, fullname, path=None, target=None):',
                '        if fullname in FORBIDDEN_TOP or any(',
                '            fullname == t or fullname.startswith(t + ".")',
                '            for t in FORBIDDEN_TOP):',
                '            raise ImportError("isolated-blocked: " + fullname)',
                '        if fullname.startswith("kmesh.logic.") and fullname not in WHITELIST:',
                '            raise ImportError("isolated-blocked: " + fullname)',
                '        return None',
                'sys.meta_path.insert(0, BlockFinder())',
                'os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"',
            ]
            code_lines += exercise
            code_lines.append('# --- block the root itself; assert the FULL message ---')
            code_lines.append('try:')
            code_lines.append('    importlib.import_module(%r)' % root)
            code_lines.append('except ImportError as _e:')
            code_lines.append('    assert str(_e) == "isolated-blocked: " + %r, %r' % (root, root))
            code_lines.append('else:')
            code_lines.append('    raise SystemExit("importable: " + repr(%r))' % root)
            code_lines.append('# --- probe a submodule via a placeholder package (has __path__) ---')
            code_lines.append('_ph = types.ModuleType(%r)' % root)
            code_lines.append('_ph.__path__ = []')
            code_lines.append('sys.modules[%r] = _ph' % root)
            code_lines.append('try:')
            code_lines.append('    importlib.import_module(%r)' % (root + '._t0012_probe'))
            code_lines.append('except ImportError as _e:')
            code_lines.append('    assert str(_e) == "isolated-blocked: " + %r, %r' % (root + '._t0012_probe', root + '._t0012_probe'))
            code_lines.append('else:')
            code_lines.append('    raise SystemExit("importable probe: " + repr(%r))' % (root + '._t0012_probe'))
            code_lines.append('finally:')
            code_lines.append('    sys.modules.pop(%r, None)' % root)
            code_lines.append('print("ISOLATION-OK " + repr(%r))' % root)
            code = "\n".join(code_lines)
            env = dict(os.environ)
            env["PYTHONPATH"] = str(src)
            env["KMESH_SRC"] = str(src)
            p = subprocess.run([sys.executable, "-c", code],
                               cwd=repo_root, env=env,
                               capture_output=True, text=True, timeout=45)
            assert p.returncode == 0, "root " + root + ": " + p.stderr
            assert "ISOLATION-OK " + repr(root) in p.stdout, p.stdout

class TestFGuardQuality:
    def test_guard_rejects_index_in_key(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "q", "a", "b"))
        k = key(c, _A("q", "a", "b"), p)
        assert 0 not in k and 1 not in k

    def test_variable_numbers_are_ints(self):
        # float_variable_number guard: every variable number must be a
        # non-bool int (rebuilding to float would change the key type).
        c = (_fact("p", "a", "a"),
             Clause((_A("p", "?x", "?y"),), _A("q", "?x", "?y")))
        p = (_ps(0, (), "p", "a", "a"), _ps(1, (0,), "q", "a", "a"))
        k = key(c, _A("q", "a", "a"), p)
        def _check_term(term):
            assert isinstance(term, tuple) and len(term) == 2
            if term[0] == "v":
                assert type(term[1]) is int and not isinstance(term[1], bool), term
                assert term[1] >= 0
            else:
                assert isinstance(term[1], str), term
        def _check_clause_key(ck):
            assert isinstance(ck, tuple) and len(ck) == 3 and ck[0] == "clause_key_v1", ck
            head = ck[1]
            assert isinstance(head, tuple) and len(head) == 3, head
            assert isinstance(head[0], str), head
            _check_term(head[1]); _check_term(head[2])
            body = ck[2]
            assert isinstance(body, tuple), body
            for atom in body:
                assert isinstance(atom, tuple) and len(atom) == 3, atom
                assert isinstance(atom[0], str), atom
                _check_term(atom[1]); _check_term(atom[2])
        for h in k[1]:
            assert isinstance(h, tuple) and len(h) == 2
            _check_clause_key(h[1])

    def test_module_all(self):
        import kmesh.logic.proof_key as _pk
        assert _pk.__all__ == ["canonical_proof_key"]








