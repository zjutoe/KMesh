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

from kmesh.logic.clause_key import canonical_clause_key
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


def _ground_key(step):
    return (step.conclusion.pred, step.conclusion.args[0], step.conclusion.args[1])


def _node_header(clauses, step):
    """Expected (GroundKey, ClauseKey); clause key via T0011 public API."""
    return (_ground_key(step), canonical_clause_key(clauses[step.clause_index]))


def _expected(clauses, steps, order):
    return ("proof_key_v1", tuple(_node_header(clauses, steps[i]) for i in order))


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
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "c"),
             _ps(2, (0, 1), "q", "a", "a"))
        got = _expected(c, p, (2, 0, 1))
        assert key(c, _A("q", "a", "a"), p) == got
        p_swap = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "c"),
                  _ps(2, (1, 0), "q", "a", "a"))
        assert key(c, _A("q", "a", "a"), p_swap) == got

    def test_k5_nonsymmetric_degenerate(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?x")))
        AB = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        kAB = _expected(c, AB, (3, 2, 1, 0))
        BA = (_ps(1, (), "s", "a", "a"), _ps(2, (0,), "p", "a", "a"),
              _ps(0, (), "p", "a", "a"), _ps(3, (1, 2), "q", "a", "a"))
        kBA = _expected(c, BA, (3, 2, 1, 0))
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
        AA = (_ps(0, (), "p", "a", "a"), _ps(0, (), "p", "a", "a"),
              _ps(3, (0, 1), "q", "a", "a"))
        AB = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        BA = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (2, 0), "q", "a", "a"))
        BB = (_ps(1, (), "s", "a", "a"), _ps(2, (0,), "p", "a", "a"),
              _ps(1, (), "s", "a", "a"), _ps(2, (2,), "p", "a", "a"),
              _ps(3, (1, 3), "q", "a", "a"))
        kAA = key(c, _A("q", "a", "a"), AA)
        kAB = key(c, _A("q", "a", "a"), AB)
        kBA = key(c, _A("q", "a", "a"), BA)
        kBB = key(c, _A("q", "a", "a"), BB)
        assert kAB == kBA
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
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "p", "a", "b"))
        k = key(c, _A("p", "a", "b"), p)
        fact_only = key(c, _A("p", "a", "b"), (_ps(0, (), "p", "a", "b"),))
        _ne(k, fact_only, "K7 rule!=fact")
        assert len(k[1]) == 2
        assert k == _expected(c, p, (1, 0))

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
        kAB = key(c, _A("t", "a", "a"), AB)
        _ne(kAB, key(c, _A("t", "a", "a"), AA), "K8 AB!=AA")
        assert kAB == key(c, _A("t", "a", "a"), BA)
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
        c = (_fact("p", "a", "b"), _fact("q", "b", "c"),
             Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")),
                   _A("r", "?x", "?z")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (), "q", "b", "c"),
             _ps(2, (0, 1), "r", "a", "c"))
        k = key(c, _A("r", "a", "c"), p)
        assert isinstance(k, tuple) and k[0] == "proof_key_v1"
        for h in k[1]:
            assert isinstance(h, tuple) and len(h) == 2
            g, ck = h
            assert len(g) == 3
            for x in g:
                assert isinstance(x, str) and not x.startswith("?")
            assert isinstance(ck, tuple) and ck[0] == "clause_key_v1"
            assert isinstance(ck[2], tuple)
            for b in ck[2]:
                assert isinstance(b, tuple) and len(b) == 3


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
        a = _build_nodes(c, p1)[-1]
        b = _build_nodes(c2, p1)[-1]
        assert oracle_equiv(a, b)
        assert key(c, _A("q", "a", "b"), p1) == key(c2, _A("q", "a", "b"), p1)

    def test_k5_two_supports_oracle(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?x")))
        AB = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        BA = (_ps(1, (), "s", "a", "a"), _ps(2, (0,), "p", "a", "a"),
              _ps(0, (), "p", "a", "a"), _ps(3, (1, 2), "q", "a", "a"))
        a = _build_nodes(c, AB)[-1]
        b = _build_nodes(c, BA)[-1]
        assert not oracle_equiv(a, b)
        assert key(c, _A("q", "a", "a"), AB) != key(c, _A("q", "a", "a"), BA)

    def test_k6_ab_vs_aa_oracle(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?y")))
        AA = (_ps(0, (), "p", "a", "a"), _ps(0, (), "p", "a", "a"),
              _ps(3, (0, 1), "q", "a", "a"))
        AB = (_ps(0, (), "p", "a", "a"), _ps(1, (), "s", "a", "a"),
              _ps(2, (1,), "p", "a", "a"), _ps(3, (0, 2), "q", "a", "a"))
        a = _build_nodes(c, AA)[-1]
        b = _build_nodes(c, AB)[-1]
        assert not oracle_equiv(a, b)
        assert key(c, _A("q", "a", "a"), AA) != key(c, _A("q", "a", "a"), AB)

    def test_k8_same_header_successor_oracle(self):
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
        assert key(c, _A("t", "a", "a"), AB) != key(c, _A("t", "a", "a"), AA)

    def test_t0009_k5_enumeration_4to4(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?x")))
        trees = enumerate_proofs(c, _A("q", "a", "a"),
                                 max_fact_checks=3, max_derivations=4,
                                 max_proof_steps=20)
        assert len(trees) == 4
        assert len({key(c, _A("q", "a", "a"), t) for t in trees}) == 4

    def test_t0009_k6_enumeration_4to3(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")),
                   _A("q", "?x", "?y")))
        trees = enumerate_proofs(c, _A("q", "a", "a"),
                                 max_fact_checks=3, max_derivations=4,
                                 max_proof_steps=20)
        assert len(trees) == 4
        assert len({key(c, _A("q", "a", "a"), t) for t in trees}) == 3


# ---------------------------------------------------------------------------
# Group D: errors, priority, and call boundary
# ---------------------------------------------------------------------------

class TestDErrors:
    def test_empty_proof_valid_message(self):
        c = (_fact("p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), ())
        assert str(e.value) == "proof_key.proof must be a valid proof of query"
        assert e.value.__suppress_context__ is False

    def test_wrong_query_valid_message(self):
        c = (_fact("q", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("q", "a", "b"), p)
        assert str(e.value) == "proof_key.proof must be a valid proof of query"
        assert e.value.__suppress_context__ is False

    def test_invalid_derivation_valid_message(self):
        c = (_fact("p", "a", "b"), _fact("q", "a", "b"))
        p = (_ps(0, (), "p", "a", "b"),)
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("q", "a", "b"), p)
        assert str(e.value) == "proof_key.proof must be a valid proof of query"
        assert e.value.__suppress_context__ is False

    def test_bad_clauses_outer(self):
        with pytest.raises(LogicValidationError) as e:
            verify_proof(["p"], _A("p", "a", "b"), ())
        assert str(e.value) == "verify.clauses must be a tuple of Clause, got list"

    def test_bad_clauses_member(self):
        with pytest.raises(ValueError,
                           match="verify.clauses\\[0\\] must be a Clause"):
            verify_proof((5,), _A("p", "a", "b"), ())

    def test_bad_query_nonground(self):
        c = (_fact("p", "a", "b"),)
        with pytest.raises(ValueError, match="verify.query must be a ground Atom"):
            verify_proof(c, _A("p", "?x", "?y"), ())

    def test_bad_query_type(self):
        c = (_fact("p", "a", "b"),)
        with pytest.raises(ValueError, match="verify.query must be an Atom"):
            verify_proof(c, "p", ())

    def test_bad_proof_member(self):
        c = (_fact("p", "a", "b"),)
        with pytest.raises(ValueError,
                           match="verify.proof\\[0\\] must be a ProofStep"):
            verify_proof(c, _A("p", "a", "b"), (("p", "a", "b"),))

    def test_bad_max_steps_types(self):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        for bad, got in ((True, "bool"), (0, "int"), (-1, "int"), (1.5, "float")):
            with pytest.raises(LogicValidationError) as e:
                verify_proof(c, _A("p", "a", "b"), p, max_steps=bad)
            assert str(e.value) == (f"verify.max_steps must be a non-bool positive "
                                     f"integer, got {got}")
            assert e.value.__suppress_context__ is False

    def test_generator_unconsumed_marker(self):
        c = (_fact("p", "a", "b"),)
        def gen():
            yield _ps(0, (), "p", "a", "b")
        with pytest.raises(ValueError, match="verify.proof must be a tuple"):
            verify_proof(c, _A("p", "a", "b"), gen())

    def test_proof_limit_priority(self):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "p", "a", "b"))
        with pytest.raises(ProofLimitError) as e:
            key(c, _A("p", "a", "b"), p, max_steps=1)
        assert str(e.value) == "verify.proof length exceeds verify.max_steps"
        assert e.value.__suppress_context__ is False

    def test_single_occurrence_message(self):
        c = (_fact("p", "a", "a"), _fact("s", "a", "a"),
             Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")),
             Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")), _A("q", "?x", "?y")))
        shared = (_ps(0, (), "p", "a", "a"), _ps(3, (0, 0), "q", "a", "a"))
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("q", "a", "a"), shared)
        assert str(e.value) == "proof_key.proof must be a single occurrence tree"
        assert e.value.__suppress_context__ is False

    def test_unused_legal_step_rejected(self):
        # a legal step that is never referenced (ref 0) and is not the final
        # step must be rejected: the single-occurrence tree requires every
        # non-final step to be referenced exactly once.
        c = (_fact("p", "a", "b"), _fact("p", "a", "b"))
        query = _A("p", "a", "b")
        proof = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "b"))
        assert verify_proof(c, query, proof)
        with pytest.raises(LogicValidationError) as e:
            key(c, query, proof)
        assert str(e.value) == "proof_key.proof must be a single occurrence tree"
        assert e.value.__suppress_context__ is False

    def test_clauses_list_rejected_by_product(self):
        # the product must not coerce clauses to a tuple; verify.clauses raises
        c = [_fact("p", "a", "b")]
        with pytest.raises(LogicValidationError) as e:
            key(c, _A("p", "a", "b"), (_ps(0, (), "p", "a", "b"),))
        assert str(e.value) == "verify.clauses must be a tuple of Clause, got list"
        assert e.value.__suppress_context__ is False

    def test_semantic_before_single_occurrence(self):
        # semantic-invalid (final != query) is raised before the single-occurrence
        # check; a bad ref_count must not mask the invalid-proof message.
        c = (_fact("p", "a", "b"), _fact("p", "a", "b"))
        query = _A("q", "a", "b")
        proof = (_ps(0, (), "p", "a", "b"), _ps(1, (), "p", "a", "b"))
        assert not verify_proof(c, query, proof)
        with pytest.raises(LogicValidationError) as e:
            key(c, query, proof)
        assert str(e.value) == "proof_key.proof must be a valid proof of query"
        assert "single occurrence tree" not in str(e.value)

    def test_length_before_bad_member(self):
        # the length check runs before per-member type checks: over-limit with a
        # bad member yields ProofLimitError, not the member type error.
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"), "not-a-step", _ps(2, (), "p", "a", "b"))
        with pytest.raises(ProofLimitError) as e:
            key(c, _A("p", "a", "b"), p, max_steps=2)
        assert str(e.value) == "verify.proof length exceeds verify.max_steps"

    def test_legal_length_boundary(self):
        c = (_fact("p", "a", "b"),
             Clause((_A("p", "?x", "?y"),), _A("p", "?x", "?y")))
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "p", "a", "b"))
        assert key(c, _A("p", "a", "b"), p, max_steps=2)
        with pytest.raises(ProofLimitError):
            key(c, _A("p", "a", "b"), p, max_steps=1)

    def test_superint_max_steps_accept(self):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        assert key(c, _A("p", "a", "b"), p, max_steps=10 ** 5000) == \
             key(c, _A("p", "a", "b"), p)

    def test_missing_extra_unknown_args(self):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        with pytest.raises(TypeError):
            canonical_proof_key(c)
        with pytest.raises(TypeError):
            canonical_proof_key(c, _A("p", "a", "b"), p, "extra")
        with pytest.raises(TypeError):
            canonical_proof_key(c, _A("p", "a", "b"), p, bogus=1)

    def test_exception_instance_propagation(self, monkeypatch):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"),)
        calls = []
        import kmesh.logic.proof_key as pk_mod
        def spy(*args, **kw):
            calls.append((args, kw))
            return False
        monkeypatch.setattr(pk_mod, "verify_proof", spy)
        with pytest.raises(ValueError, match="valid proof of query"):
            canonical_proof_key(c, _A("p", "a", "b"), p)
        assert len(calls) == 1
        args, kw = calls[0]
        assert args[:3] == (c, _A("p", "a", "b"), p)
        assert kw.get("max_steps") == 10_000

    def test_prooflimit_instance_propagation(self, monkeypatch):
        c = (_fact("p", "a", "b"),)
        p = (_ps(0, (), "p", "a", "b"), _ps(1, (0,), "p", "a", "b"))
        import kmesh.logic.proof_key as pk_mod
        def spy(*args, **kw):
            raise ProofLimitError("verify.proof length exceeds verify.max_steps")
        monkeypatch.setattr(pk_mod, "verify_proof", spy)
        with pytest.raises(ProofLimitError, match="verify.proof length"):
            canonical_proof_key(c, _A("p", "a", "b"), p)


# ---------------------------------------------------------------------------
# Group E: long chain, output shape, import isolation
# ---------------------------------------------------------------------------

class TestELongAndIsolation:
    def test_long_chain_1201(self):
        n = 1200
        clauses = (_fact("p", "a", "b"),
                   Clause((_A("p", "?x", "?y"),), _A("p", "?x", "?y")))
        proof = [_ps(0, (), "p", "a", "b")]
        for i in range(n):
            proof.append(_ps(1, (i,), "p", "a", "b"))
        proof = tuple(proof)
        total = len(proof)
        k = key(clauses, _A("p", "a", "b"), proof, max_steps=total)
        assert len(k[1]) == total
        assert k[1][-1] == (_ground_key(proof[0]),
                            canonical_clause_key(clauses[0]))
        assert key(clauses, _A("p", "a", "b"), proof, max_steps=total) == k
        assert hash(k) == hash(k)
        assert k in {k}
        assert {k: "x"}[k] == "x"
        short = key(clauses, _A("p", "a", "b"),
                    (_ps(0, (), "p", "a", "b"),
                     _ps(1, (0,), "p", "a", "b")), max_steps=2)
        assert k != short
        assert len(sorted([k, short])) == 2
        with pytest.raises(ProofLimitError):
            key(clauses, _A("p", "a", "b"), proof, max_steps=total - 1)

    def test_import_isolation_hard_block(self):
        from pathlib import Path as _Path
        repo_root = _Path(__file__).resolve().parents[3]
        src = repo_root / "src"
        forbidden = ("engine", "reference_engine", "solver", "enumerate",
                     "depth", "model", "data", "training")
        code_lines = [
            "import importlib.util, sys, os",
            "sys.path.insert(0, os.environ['KMESH_SRC'])",
            "forbidden = (%s)" % ', '.join(repr(n) for n in forbidden),
            "for name in forbidden:",
            "    try:",
            "        s = importlib.util.find_spec('kmesh.logic.' + name)",
            "        assert s is None or s.submodule_search_locations is None, name",
            "    except Exception:",
            "        pass",
            "",
            "from kmesh.logic.proof_key import canonical_proof_key",
            "from kmesh.logic.types import Atom, Clause",
            "from kmesh.logic.proof import ProofStep",
            "def fact(p, a, b):",
            "    return Clause((), Atom(p, (a, b)))",
            "def atom(p, x, y):",
            "    return Atom(p, (x, y))",
            "",
            "k0 = canonical_proof_key((fact('p', 'a', 'b'),), atom('p', 'a', 'b'), (ProofStep(0, (), atom('p', 'a', 'b')),))",
            "assert isinstance(k0, tuple) and k0[0] == 'proof_key_v1'",
            "",
            "c3 = (fact('p', 'a', 'b'), fact('q', 'b', 'c'), Clause((atom('p', '?x', '?y'), atom('q', '?y', '?z')), atom('r', '?x', '?z')))" ,
            "p3 = (ProofStep(0, (), atom('p', 'a', 'b')), ProofStep(1, (), atom('q', 'b', 'c')), ProofStep(2, (0, 1), atom('r', 'a', 'c'))) ",
            "k3 = canonical_proof_key(c3, atom('r', 'a', 'c'), p3)",
            "assert k3[1][0][0] == ('r', 'a', 'c')",
            "",
            "bad = []",
            "for n in forbidden:",
            "    for cand in (n, 'kmesh.' + n, 'kmesh.logic.' + n):",
            "        if cand in sys.modules:",
            "            bad.append(cand)",
            "assert not bad, bad",
            "print('has_ck: True')",
        ]
        body = '\n'.join(code_lines) + '\n'
        env = dict(os.environ)
        env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        env['KMESH_SRC'] = str(src)
        p = subprocess.run([sys.executable, '-c', body], cwd=repo_root,
                           env=env, capture_output=True, text=True, timeout=30)
        assert p.returncode == 0, p.stderr
        assert 'has_ck: True' in p.stdout
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
