"""T0018 tests for ``heldout_motifs.heldout_motif_hits`` (D37).

Match a batch of ground queries against a fixed reference-motif directory:
T0014 ``canonical_motif_key`` keys every reference tree once, in directory
order, and T0017 ``query_subtree_motif_keys`` unions every target query's
complete rooted subtree keys once, in query order; the result is the set of
reference positions whose complete key is in each query's union.  Expected
values are frozen hand-checked literals (handoff §4, confirmed by
``reports/T0018/planning_probe.py``), never derived from the product.

Only the accepted whitelist is imported: stdlib + ``kmesh.logic.types`` /
``kmesh.logic.proof`` limit types + ``proof_enumeration`` + ``motif`` +
``query_motifs`` + the target.  No solver / reference engine / torch / YAML /
file access.  All fixtures are fixed literals.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from kmesh.logic.types import Atom, Clause, LogicValidationError
from kmesh.logic.proof import ProofStep, ProofLimitError
from kmesh.logic.proof_enumeration import ProofEnumerationLimitError
from kmesh.logic.derivations import DerivationLimitError
from kmesh.logic.motif import MotifLimitError
from kmesh.logic.query_motifs import query_subtree_motif_keys
import kmesh.logic.heldout_motifs as hm
from kmesh.logic.heldout_motifs import heldout_motif_hits


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def atom(pred, x, y):
    return Atom(pred, (x, y))


def fact(pred, x, y):
    return Clause((), atom(pred, x, y))


def c_rule(p, q):
    return Clause((atom(p, "?x", "?y"),), atom(q, "?x", "?y"))


def inv_rule(p, q):
    return Clause((atom(p, "?x", "?y"),), atom(q, "?y", "?x"))


def join_rule(p, r, q):
    return Clause(
        (atom(p, "?x", "?y"), atom(r, "?y", "?z")), atom(q, "?x", "?z"))


def hs(*ints):
    return frozenset(ints)


# frozen hand-checked reference directory (handoff §3 table, probe-confirmed):
# ref 0 = F, ref 1 = C, ref 2 = I, ref 3 = J, ref 4 = CJ, ref 5 = C copy;
# keys[1] == keys[5], five distinct keys.
REFERENCES = (
    ((fact("p", "a", "b"),), atom("p", "a", "b"),
     (ProofStep(0, (), atom("p", "a", "b")),)),
    ((fact("p", "a", "b"), c_rule("p", "q")), atom("q", "a", "b"),
     (ProofStep(0, (), atom("p", "a", "b")),
      ProofStep(1, (0,), atom("q", "a", "b")))),
    ((fact("p", "a", "b"), inv_rule("p", "q")), atom("q", "b", "a"),
     (ProofStep(0, (), atom("p", "a", "b")),
      ProofStep(1, (0,), atom("q", "b", "a")))),
    ((fact("p", "a", "b"), fact("r", "b", "c"), join_rule("p", "r", "q")),
     atom("q", "a", "c"),
     (ProofStep(0, (), atom("p", "a", "b")),
      ProofStep(1, (), atom("r", "b", "c")),
      ProofStep(2, (0, 1), atom("q", "a", "c")))),
    ((fact("f", "m", "n"), fact("g", "n", "o"), c_rule("f", "h"),
      join_rule("h", "g", "k")), atom("k", "m", "o"),
     (ProofStep(0, (), atom("f", "m", "n")),
      ProofStep(2, (0,), atom("h", "m", "n")),
      ProofStep(1, (), atom("g", "n", "o")),
      ProofStep(3, (1, 2), atom("k", "m", "o")))),
    ((fact("s", "m", "n"), c_rule("s", "t")), atom("t", "m", "n"),
     (ProofStep(0, (), atom("s", "m", "n")),
      ProofStep(1, (0,), atom("t", "m", "n")))),
)

W_A = (fact("p", "a", "b"), fact("r", "b", "a"), c_rule("p", "q"),
       inv_rule("r", "q"))
W_B = (fact("p", "a", "b"), fact("r", "b", "c"), c_rule("p", "u"),
       join_rule("u", "r", "v"), c_rule("v", "t"))
W_C = (fact("q", "a", "c"), fact("p", "a", "b"), fact("r", "b", "c"),
       join_rule("p", "r", "q"))


def renamed_world(world, rel, ent):
    def ra(at):
        return Atom(rel[at.pred], tuple(
            t if t.startswith("?") else ent[t] for t in at.args))
    return tuple(Clause(tuple(ra(a) for a in cl.body), ra(cl.head))
                 for cl in world)


def renamed_atom(at, rel, ent):
    return Atom(rel[at.pred], tuple(
        t if t.startswith("?") else ent[t] for t in at.args))


# ---------------------------------------------------------------------------
# Group A: hand-checked anchors H0-H3 and CJ/J-only directories
# ---------------------------------------------------------------------------

def test_h0_empty_world_empty_hit():
    res = heldout_motif_hits((), (atom("z", "a", "b"),), REFERENCES)
    assert res == (hs(),)
    assert type(res) is tuple and len(res) == 1
    assert type(res[0]) is frozenset
    assert hash(res) is not None


def test_h1_world_a_four_queries():
    qs = (atom("q", "a", "b"), atom("p", "a", "b"),
          atom("z", "a", "b"), atom("q", "a", "b"))
    res = heldout_motif_hits(W_A, qs, REFERENCES)
    # ref 3 (J) and ref 4 (CJ) absent: W_A has no JOIN/CJ support
    assert res == (hs(0, 1, 2, 5), hs(0), hs(), hs(0, 1, 2, 5))
    assert type(res[0]) is frozenset and type(res[2]) is frozenset


def test_h2_world_b_four_queries():
    qs = (atom("t", "a", "c"), atom("v", "a", "c"),
          atom("u", "a", "b"), atom("p", "a", "b"))
    res = heldout_motif_hits(W_B, qs, REFERENCES)
    # J (ref 3) does NOT hit t/v: one JOIN support contains COPY (u) and
    # cannot be trimmed to a boundary fact; CJ (ref 4) is present at depth 3.
    assert res == (hs(0, 1, 4, 5), hs(0, 1, 4, 5), hs(0, 1, 5), hs(0))


def test_h3_world_c_fact_and_join():
    qs = (atom("q", "a", "c"), atom("p", "a", "b"))
    res = heldout_motif_hits(W_C, qs, REFERENCES)
    # q(a,c) has a fact proof AND a JOIN proof; the JOIN motif (ref 3) must
    # still be checked and hit, even though a fact already proves the query.
    assert res == (hs(0, 3), hs(0))


def test_cj_ref_only_misses_p_query():
    # only original ref 4 (CJ, new index 0) against W_B's p(a,b): the CJ
    # reference's internal facts are not automatically retained.
    res = heldout_motif_hits(W_B, (atom("p", "a", "b"),), (REFERENCES[4],))
    assert res == (hs(),)


def test_j_ref_only_misses_qab_query():
    # only original ref 3 (J, new index 0) against W_A's q(a,b): W_A has
    # COPY/INV supports only, no JOIN subtree.
    res = heldout_motif_hits(W_A, (atom("q", "a", "b"),), (REFERENCES[3],))
    assert res == (hs(),)


# ---------------------------------------------------------------------------
# Group B: invariance, reference rename, reference reversal
# ---------------------------------------------------------------------------

def test_h1_world_rel_ent_bijection_and_reverse():
    rel = {"p": "P", "r": "R", "q": "Q", "z": "Z"}
    ent = {"a": "A", "b": "B"}
    qs = (atom("q", "a", "b"), atom("p", "a", "b"),
          atom("z", "a", "b"), atom("q", "a", "b"))
    base = heldout_motif_hits(W_A, qs, REFERENCES)
    assert base == (hs(0, 1, 2, 5), hs(0), hs(), hs(0, 1, 2, 5))

    w_r = renamed_world(W_A, rel, ent)
    assert w_r != W_A  # fields actually changed
    qs_r = tuple(renamed_atom(q, rel, ent) for q in qs)
    assert qs_r != qs
    assert heldout_motif_hits(w_r, qs_r, REFERENCES) == base

    w_rev = W_A[::-1]
    assert w_rev != W_A  # world actually reversed
    assert heldout_motif_hits(w_rev, qs, REFERENCES) == base


def test_h2_rule_var_bijection_and_body_swap():
    qs = (atom("t", "a", "c"), atom("v", "a", "c"),
          atom("u", "a", "b"), atom("p", "a", "b"))
    base = heldout_motif_hits(W_B, qs, REFERENCES)
    assert base == (hs(0, 1, 4, 5), hs(0, 1, 4, 5), hs(0, 1, 5), hs(0))

    # local schema variable bijection ?x->?u, ?y->?v, ?z->?w in rule bodies
    w_v = (
        W_B[0], W_B[1],  # ground facts untouched
        Clause((atom("p", "?u", "?v"),), atom("u", "?u", "?v")),
        Clause((atom("u", "?u", "?v"), atom("r", "?v", "?w")),
               atom("v", "?u", "?w")),
        Clause((atom("v", "?u", "?v"),), atom("t", "?u", "?v")),
    )
    assert w_v != W_B
    assert heldout_motif_hits(w_v, qs, REFERENCES) == base

    # JOIN body swap
    def swap_body(c):
        return Clause(c.body[::-1], c.head) if len(c.body) == 2 else c
    w_s = tuple(swap_body(cl) for cl in W_B)
    assert w_s != W_B  # the two-premise body order actually changed
    assert heldout_motif_hits(w_s, qs, REFERENCES) == base


def test_reference_rename_preserves_hit():
    # rename ref 3 (J over p/r/q, a/b/c) to P/R/Q over A/B/C: fields changed,
    # structure unchanged, hit index unchanged (W_C's q(a,c) hits J).
    rel = {"p": "P", "r": "R", "q": "Q"}
    ent = {"a": "A", "b": "B", "c": "C"}
    rc, rq, rp = REFERENCES[3]
    rc_r = renamed_world(rc, rel, ent)
    rq_r = renamed_atom(rq, rel, ent)
    rp_r = tuple(ProofStep(s.clause_index, s.premise_steps,
                           renamed_atom(s.conclusion, rel, ent))
                 for s in rp)
    ref3_r = (rc_r, rq_r, rp_r)
    assert ref3_r != REFERENCES[3]  # fields actually changed
    refs_r = (REFERENCES[0], REFERENCES[1], REFERENCES[2], ref3_r,
              REFERENCES[4], REFERENCES[5])
    qs = (atom("q", "a", "c"), atom("p", "a", "b"))
    base = heldout_motif_hits(W_C, qs, REFERENCES)
    assert base == (hs(0, 3), hs(0))
    assert heldout_motif_hits(W_C, qs, refs_r) == base


def test_reference_reversal_remaps_indices():
    qs = (atom("q", "a", "b"), atom("p", "a", "b"),
          atom("z", "a", "b"), atom("q", "a", "b"))
    base = heldout_motif_hits(W_A, qs, REFERENCES)
    assert base == (hs(0, 1, 2, 5), hs(0), hs(), hs(0, 1, 2, 5))
    rev = REFERENCES[::-1]
    assert rev != REFERENCES  # directory actually reordered
    res = heldout_motif_hits(W_A, qs, rev)
    # old index j becomes 5 - j exactly
    expected = tuple(frozenset(5 - j for j in hit) for hit in base)
    assert res == expected
    assert res == (hs(5, 4, 3, 0), hs(5), hs(), hs(5, 4, 3, 0))


# ---------------------------------------------------------------------------
# Group C: delegation spy — order, identity, exact budgets, exactly-once
# ---------------------------------------------------------------------------

def _anchor_dir():
    rc0 = (fact("p", "a", "b"),)
    rc1 = (fact("p", "a", "b"), c_rule("p", "q"))
    rp0 = (ProofStep(0, (), atom("p", "a", "b")),)
    rp1 = (ProofStep(0, (), atom("p", "a", "b")),
           ProofStep(1, (0,), atom("q", "a", "b")))
    # ref0 is the SAME triple object at positions 0 and 2: a dedup mutant
    # would collapse them, but the contract calls canonical_motif_key once
    # per directory position.
    ref0 = (rc0, atom("p", "a", "b"), rp0)
    ref1 = (rc1, atom("q", "a", "b"), rp1)
    refs = (ref0, ref1, ref0)
    clauses = (fact("x", "a", "b"),)
    # the SAME query object at both positions: a dedup mutant that caches
    # identical query positions would skip one of them.
    qx = atom("x", "a", "b")
    qs = (qx, qx)
    return clauses, qs, refs


def test_delegation_order_identity_nondefault():
    clauses, qs, refs = _anchor_dir()
    qx = qs[0]
    # fixture repeats the same query object and the same reference triple
    # object at distinct positions
    assert qs[0] is qs[1] and refs[0] is refs[2]
    real_canon = hm.canonical_motif_key
    real_qsm = hm.query_subtree_motif_keys
    o_c, o_q = hm.canonical_motif_key, hm.query_subtree_motif_keys
    calls = []

    def spy_canon(*a, **k):
        calls.append(("canon", a, k))
        return real_canon(*a, **k)

    def spy_qsm(*a, **k):
        calls.append(("qsm", a, k))
        return real_qsm(*a, **k)

    hm.canonical_motif_key = spy_canon
    hm.query_subtree_motif_keys = spy_qsm
    try:
        res = heldout_motif_hits(
            clauses, qs, refs,
            max_fact_checks=11, max_derivations=13,
            max_proof_steps=17, max_orientations=19)
    finally:
        hm.canonical_motif_key = o_c
        hm.query_subtree_motif_keys = o_q

    kinds = [c[0] for c in calls]
    # every reference position keyed before every target query position
    # (including the repeated triple); one call per position
    assert kinds == ["canon", "canon", "canon", "qsm", "qsm"]
    # both repeated query positions produce the identical hit set
    assert res == (hs(0, 2), hs(0, 2))
    for i in range(3):
        a, k = calls[i][1], calls[i][2]
        assert a[0] is refs[i][0] and a[1] is refs[i][1] and a[2] is refs[i][2]
        assert k == {"max_steps": 17, "max_orientations": 19}
    # ref0 is a single object, invoked at both positions 0 and 2 (no dedup)
    assert calls[0][1][0] is calls[2][1][0]
    assert calls[0][1][1] is calls[2][1][1]
    assert calls[0][1][2] is calls[2][1][2]
    # both query positions invoke the target with the same query object, in
    # order -- a caching mutant that skips the second identical position would
    # leave len(calls) == 4 here
    for i in range(2):
        a, k = calls[3 + i][1], calls[3 + i][2]
        assert a[0] is clauses
        assert a[1] is qx
        assert k == {"max_fact_checks": 11, "max_derivations": 13,
                     "max_proof_steps": 17, "max_orientations": 19}
    assert calls[3][1][1] is calls[4][1][1]


def test_delegation_default_budget_passthrough():
    clauses = (fact("p", "a", "b"),)
    refs = ((clauses, atom("p", "a", "b"),
             (ProofStep(0, (), atom("p", "a", "b")),)),)
    qs = (atom("p", "a", "b"),)
    real_canon = hm.canonical_motif_key
    real_qsm = hm.query_subtree_motif_keys
    o_c, o_q = hm.canonical_motif_key, hm.query_subtree_motif_keys
    calls = []

    def spy_canon(*a, **k):
        calls.append(("canon", a, k))
        return real_canon(*a, **k)

    def spy_qsm(*a, **k):
        calls.append(("qsm", a, k))
        return real_qsm(*a, **k)

    hm.canonical_motif_key = spy_canon
    hm.query_subtree_motif_keys = spy_qsm
    try:
        res = heldout_motif_hits(clauses, qs, refs)
    finally:
        hm.canonical_motif_key = o_c
        hm.query_subtree_motif_keys = o_q
    assert res == (hs(0),)
    assert calls[0] == ("canon", refs[0],
                        {"max_steps": 100_000, "max_orientations": 100_000})
    assert calls[1] == ("qsm", (clauses, qs[0]),
                        {"max_fact_checks": 100_000, "max_derivations": 100_000,
                         "max_proof_steps": 100_000, "max_orientations": 100_000})


def test_w_c_full_result():
    qs = (atom("p", "a", "b"), atom("q", "a", "c"), atom("z", "a", "b"))
    res = heldout_motif_hits(W_C, qs, (REFERENCES[0],),
                             max_fact_checks=2, max_derivations=4,
                             max_proof_steps=6, max_orientations=2)
    assert res == (hs(0), hs(0), hs())


def test_w_c_o1_second_query_fails_third_not_called():
    # W_C derives q(a,c) via fact and via the two-premise JOIN; O=1 cannot
    # canonicalize the JOIN on the second query (q(a,c)) even though q1 hit.
    qs = (atom("p", "a", "b"), atom("q", "a", "c"), atom("z", "a", "b"))
    real_qsm = hm.query_subtree_motif_keys
    o_q = hm.query_subtree_motif_keys
    calls = []

    def spy_qsm(*a, **k):
        calls.append((a, k))
        return real_qsm(*a, **k)

    hm.query_subtree_motif_keys = spy_qsm
    try:
        with pytest.raises(MotifLimitError) as exc_info:
            heldout_motif_hits(W_C, qs, (REFERENCES[0],),
                               max_fact_checks=2, max_derivations=4,
                               max_proof_steps=6, max_orientations=1)
    finally:
        hm.query_subtree_motif_keys = o_q
    assert str(exc_info.value) == (
        "motif.max_orientations insufficient for complete canonicalization")
    # q1 (fact) and q2 (JOIN, O=1) invoked; the first-hit q1 cannot mask the
    # failure and the un-reached third query is never called
    assert len(calls) == 2
    assert [c[0][1].pred for c in calls] == ["p", "q"]
    assert all(c[0][0] is W_C for c in calls)
    assert not any(c[0][1] is qs[2] for c in calls)


def test_w_c_s5_second_query_fails_third_not_called():
    # passthrough spy confirms only the first two queries are reached; the
    # third is never called even though q1 already hit.
    qs = (atom("p", "a", "b"), atom("q", "a", "c"), atom("z", "a", "b"))
    real_qsm = hm.query_subtree_motif_keys
    o_q = hm.query_subtree_motif_keys
    calls = []

    def spy_qsm(*a, **k):
        calls.append(a)
        return real_qsm(*a, **k)

    hm.query_subtree_motif_keys = spy_qsm
    try:
        with pytest.raises(ProofEnumerationLimitError) as exc_info:
            heldout_motif_hits(W_C, qs, (REFERENCES[0],),
                               max_fact_checks=2, max_derivations=4,
                               max_proof_steps=5, max_orientations=2)
    finally:
        hm.query_subtree_motif_keys = o_q
    assert str(exc_info.value) == (
        "proofs.max_proof_steps exhausted before enumeration completed")
    # exactly the first two queries are called; the third (z) is never reached
    assert len(calls) == 2
    assert calls[0][1] is qs[0]
    assert calls[1][1] is qs[1]
    assert not any(c[1] is qs[2] for c in calls)


def test_w_c_c_exhaustion():
    # C exhaustion alone: C=1, D=4. W_C needs C=2 for the two JOIN premise
    # matches; C=1 runs out on the second.
    qs = (atom("p", "a", "b"),)
    with pytest.raises(DerivationLimitError) as exc_info:
        heldout_motif_hits(W_C, qs, (REFERENCES[0],),
                           max_fact_checks=1, max_derivations=4,
                           max_proof_steps=6, max_orientations=2)
    assert type(exc_info.value) is DerivationLimitError
    assert str(exc_info.value) == (
        "enumerate.max_fact_checks exhausted before enumeration completed")


def test_w_c_d_exhaustion():
    # D exhaustion alone: C=2 suffices for the JOIN matches, D=3 is not
    # enough for the JOIN emission. A mutant that falls back to empty hits
    # on D exhaustion would return (hs(),) here instead of raising.
    qs = (atom("p", "a", "b"),)
    with pytest.raises(DerivationLimitError) as exc_info:
        heldout_motif_hits(W_C, qs, (REFERENCES[0],),
                           max_fact_checks=2, max_derivations=3,
                           max_proof_steps=6, max_orientations=2)
    assert type(exc_info.value) is DerivationLimitError
    assert str(exc_info.value) == (
        "enumerate.max_derivations exhausted before enumeration completed")


def test_ref4_s3_proof_limit_zero_targets():
    # ref 4 (CJ) is a 4-step proof; S=3 makes its T0014 call raise
    # ProofLimitError before any target query is touched.
    qs = (atom("p", "a", "b"),)
    real_qsm = hm.query_subtree_motif_keys
    o_q = hm.query_subtree_motif_keys
    calls = []

    def spy_qsm(*a, **k):
        calls.append((a, k))
        return real_qsm(*a, **k)

    hm.query_subtree_motif_keys = spy_qsm
    try:
        with pytest.raises(ProofLimitError) as exc_info:
            heldout_motif_hits(W_B, qs, (REFERENCES[4],),
                               max_fact_checks=2, max_derivations=4,
                               max_proof_steps=3, max_orientations=2)
    finally:
        hm.query_subtree_motif_keys = o_q
    assert str(exc_info.value) == "verify.proof length exceeds verify.max_steps"
    assert not calls  # zero target calls


# ---------------------------------------------------------------------------
# Group D: local validation (shape, generator non-consumption, order)
# ---------------------------------------------------------------------------

def _legal_queries():
    return (atom("q", "a", "b"),)


def test_local_validation_queries():
    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, [atom("q", "a", "b")], (REFERENCES[0],))
    assert str(exc_info.value) == (
        "heldout_motifs.queries must be a tuple of ground Atom; got list")

    entered = []

    def gen():
        entered.append(1)
        yield atom("q", "a", "b")

    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, gen(), (REFERENCES[0],))
    assert str(exc_info.value) == (
        "heldout_motifs.queries must be a tuple of ground Atom; got generator")
    assert not entered  # generator body never consumed

    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, (), (REFERENCES[0],))
    assert str(exc_info.value) == "heldout_motifs.queries must be non-empty"

    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, (1,), (REFERENCES[0],))
    assert str(exc_info.value) == (
        "heldout_motifs.queries[0] must be an Atom; got int")

    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, (atom("q", "?x", "b"),), (REFERENCES[0],))
    assert str(exc_info.value) == (
        "heldout_motifs.queries[0] must be a ground Atom")


def test_local_validation_references():
    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, _legal_queries(), [REFERENCES[0]])
    assert str(exc_info.value) == (
        "heldout_motifs.references must be a tuple of reference triples; got list")

    entered = []

    def gen_refs():
        entered.append(1)
        yield REFERENCES[0]

    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, _legal_queries(), gen_refs())
    assert str(exc_info.value) == (
        "heldout_motifs.references must be a tuple of reference triples; "
        "got generator")
    assert not entered

    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, _legal_queries(), ())
    assert str(exc_info.value) == "heldout_motifs.references must be non-empty"

    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, _legal_queries(), (REFERENCES[0], ("a", "b")))
    assert str(exc_info.value) == (
        "heldout_motifs.references[1] must be a (clauses, query, proof) tuple")

    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, _legal_queries(),
                           (REFERENCES[0], (REFERENCES[0][0], REFERENCES[0][1],
                                            REFERENCES[0][2], "x")))
    assert str(exc_info.value) == (
        "heldout_motifs.references[1] must be a (clauses, query, proof) tuple")

    # a LATER reference entry that is a length-3 list (not a tuple): the shape
    # check must reject it with the exact indexed message even though the
    # preceding reference is valid (a mutant that accepts list triples passes
    # without this entry)
    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(
            W_A, _legal_queries(),
            (REFERENCES[0], [REFERENCES[0][0], REFERENCES[0][1],
                              REFERENCES[0][2]]))
    assert str(exc_info.value) == (
        "heldout_motifs.references[1] must be a (clauses, query, proof) tuple")


def test_reference_list_entry_zero_dependency_calls():
    # a later list reference entry is rejected by the shape check BEFORE any
    # dependency is called: the preceding valid reference is not keyed and no
    # target query is enumerated.
    refs = (REFERENCES[0], [REFERENCES[0][0], REFERENCES[0][1],
                              REFERENCES[0][2]])
    real_canon = hm.canonical_motif_key
    real_qsm = hm.query_subtree_motif_keys
    o_c, o_q = hm.canonical_motif_key, hm.query_subtree_motif_keys
    canon_calls = []
    qsm_calls = []

    def spy_canon(*a, **k):
        canon_calls.append(a)
        return real_canon(*a, **k)

    def spy_qsm(*a, **k):
        qsm_calls.append(a)
        return real_qsm(*a, **k)

    hm.canonical_motif_key = spy_canon
    hm.query_subtree_motif_keys = spy_qsm
    try:
        with pytest.raises(LogicValidationError) as exc_info:
            heldout_motif_hits(W_A, _legal_queries(), refs)
    finally:
        hm.canonical_motif_key = o_c
        hm.query_subtree_motif_keys = o_q
    assert str(exc_info.value) == (
        "heldout_motifs.references[1] must be a (clauses, query, proof) tuple")
    assert not canon_calls  # ref0 (the preceding valid one) never keyed
    assert not qsm_calls    # no target query enumerated


def test_check_order_queries_before_references():
    # bad second query AND bad first reference: queries error wins
    bad_qs = (atom("q", "a", "b"), 1)
    bad_refs = ((REFERENCES[0][0], REFERENCES[0][1], REFERENCES[0][2], "extra"),)
    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, bad_qs, bad_refs)
    assert str(exc_info.value) == (
        "heldout_motifs.queries[1] must be an Atom; got int")
    # bad reference (after valid queries) wins over any later local issue
    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_A, _legal_queries(),
                           (REFERENCES[0], 1, REFERENCES[0]))
    assert str(exc_info.value) == (
        "heldout_motifs.references[1] must be a (clauses, query, proof) tuple")


def test_reference_shape_before_any_dependency():
    calls = []
    real_canon = hm.canonical_motif_key
    real_qsm = hm.query_subtree_motif_keys
    o_c, o_q = hm.canonical_motif_key, hm.query_subtree_motif_keys

    def spy_canon(*a, **k):
        calls.append("canon")
        return real_canon(*a, **k)

    def spy_qsm(*a, **k):
        calls.append("qsm")
        return real_qsm(*a, **k)

    hm.canonical_motif_key = spy_canon
    hm.query_subtree_motif_keys = spy_qsm
    try:
        with pytest.raises(LogicValidationError) as exc_info:
            heldout_motif_hits(W_A, _legal_queries(),
                               (REFERENCES[0], REFERENCES[0][0]))
    finally:
        hm.canonical_motif_key = o_c
        hm.query_subtree_motif_keys = o_q
    assert str(exc_info.value) == (
        "heldout_motifs.references[1] must be a (clauses, query, proof) tuple")
    assert calls == []  # no dependency call reached


def test_signature_and_all_public():
    try:
        heldout_motif_hits(W_A, _legal_queries())
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    try:
        heldout_motif_hits(W_A, _legal_queries(), REFERENCES, 5)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    try:
        heldout_motif_hits(W_A, _legal_queries(), REFERENCES, max_bogus=1)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    assert hm.__all__ == ["heldout_motif_hits"]


# ---------------------------------------------------------------------------
# Group E: delegated input boundaries (same diagnosis as the dependencies)
# ---------------------------------------------------------------------------

def _direct(w, q, **kws):
    try:
        query_subtree_motif_keys(w, q, **kws)
        return None, None
    except Exception as e:
        return type(e).__name__, str(e)


def _api(w, qs, refs, **kws):
    try:
        heldout_motif_hits(w, qs, refs, **kws)
        return None, None
    except Exception as e:
        return type(e).__name__, str(e)


def _base():
    return dict(
        max_fact_checks=6, max_derivations=6, max_proof_steps=10,
        max_orientations=4)


def test_delegation_clauses_list_and_bad_member():
    base = _base()
    assert _api(list(W_C), _legal_queries(), (REFERENCES[0],), **base) == \
        _direct(list(W_C), _legal_queries()[0], **base)
    assert _api(list(W_C), _legal_queries(), (REFERENCES[0],), **base) == (
        "LogicValidationError",
        "proofs.clauses must be a tuple of Clause; got list")
    bad_w = (W_C[0], 1) + W_C[1:]
    assert _api(bad_w, _legal_queries(), (REFERENCES[0],), **base) == \
        _direct(bad_w, _legal_queries()[0], **base)
    assert _api(bad_w, _legal_queries(), (REFERENCES[0],), **base) == (
        "LogicValidationError", "proofs.clauses[1] must be a Clause; got int")


def test_delegation_cyclic_world():
    w_cyc = (Clause((atom("p", "?x", "?y"),), atom("p", "?x", "?y")),)
    base = _base()
    d = _direct(w_cyc, atom("z", "a", "b"), **base)
    a = _api(w_cyc, (atom("z", "a", "b"),), (REFERENCES[0],), **base)
    assert a == d
    assert a == ("LogicValidationError",
                 "dependency.clauses: cyclic predicate dependency")


def test_delegation_query_type_groundness():
    base = _base()
    for bad_q in (1, atom("q", "?x", "b")):
        expect = _api(W_C, (bad_q,), (REFERENCES[0],), **base)
        # heldout validates its own queries first, so its local message is the
        # one carried; the dependency diagnosis for the same query object:
        d = _direct(W_C, bad_q, **base)
        assert expect[0] == d[0] == "LogicValidationError"
    assert _api(W_C, (1,), (REFERENCES[0],), **base) == (
        "LogicValidationError", "heldout_motifs.queries[0] must be an Atom; "
        "got int")
    assert _api(W_C, (atom("q", "?x", "b"),), (REFERENCES[0],), **base) == (
        "LogicValidationError",
        "heldout_motifs.queries[0] must be a ground Atom")


def test_delegation_invalid_c_d_s_o():
    base = dict(_base())
    assert _api(W_C, _legal_queries(), (REFERENCES[0],),
                **{**base, "max_fact_checks": 0}) == (
        "LogicValidationError",
        "proofs.max_fact_checks must be a non-bool positive integer; got int")
    assert _api(W_C, _legal_queries(), (REFERENCES[0],),
                **{**base, "max_derivations": True}) == (
        "LogicValidationError",
        "proofs.max_derivations must be a non-bool positive integer; got bool")
    # max_proof_steps is validated first inside the reference's T0014 key
    # (verify_proof), which runs before any target query
    assert _api(W_C, _legal_queries(), (REFERENCES[0],),
                **{**base, "max_proof_steps": 0}) == (
        "LogicValidationError",
        "verify.max_steps must be a non-bool positive integer, got int")
    # shared orientation budget is checked inside the first reference key
    # before any target query
    calls = []
    real_qsm = hm.query_subtree_motif_keys
    o_q = hm.query_subtree_motif_keys

    def spy_qsm(*a, **k):
        calls.append(a)
        return real_qsm(*a, **k)

    hm.query_subtree_motif_keys = spy_qsm
    try:
        with pytest.raises(LogicValidationError) as exc_info:
            heldout_motif_hits(W_C, _legal_queries(), (REFERENCES[0],),
                               max_fact_checks=6, max_derivations=6,
                               max_proof_steps=10, max_orientations=1.5)
    finally:
        hm.query_subtree_motif_keys = o_q
    assert str(exc_info.value) == (
        "motif.max_orientations must be a non-bool positive integer; got float")
    assert not calls  # no target query called


# ---------------------------------------------------------------------------
# Group F: exception identity (instance, message, cause, context, suppress)
# ---------------------------------------------------------------------------

def _sentinel(cls, msg, ctx):
    try:
        e = cls(msg)
    except TypeError:
        # ProofEnumerationLimitError.__init__(self) carries a fixed message
        e = cls()
    e.__context__ = ctx
    e.__cause__ = None
    e.__suppress_context__ = False
    return e


@pytest.mark.parametrize(
    "sent_cls", [LogicValidationError, ProofLimitError, MotifLimitError])
def test_exception_identity_second_reference(sent_cls):
    refs = (REFERENCES[0], REFERENCES[1], REFERENCES[2])
    real_canon = hm.canonical_motif_key
    o_c, o_q = hm.canonical_motif_key, hm.query_subtree_motif_keys
    calls = []
    sent = _sentinel(
        sent_cls, f"t0018-ref2-{sent_cls.__name__}",
        LogicValidationError("t0018-ref2-context"))
    expected = {
        "msg": str(sent), "ctx": sent.__context__,
        "cause": sent.__cause__, "suppress": sent.__suppress_context__,
    }

    def spy_canon(*a, **k):
        calls.append((a, k))
        if len(calls) == 1:
            return real_canon(*a, **k)
        raise sent

    def spy_qsm(*a, **k):
        raise AssertionError("unexpected target call")

    hm.canonical_motif_key = spy_canon
    hm.query_subtree_motif_keys = spy_qsm
    try:
        with pytest.raises(sent_cls) as exc_info:
            heldout_motif_hits(W_A, _legal_queries(), refs, **_base())
    finally:
        hm.canonical_motif_key = o_c
        hm.query_subtree_motif_keys = o_q
    exc = exc_info.value
    assert exc is sent
    assert type(exc) is sent_cls
    assert str(exc) == expected["msg"]
    assert exc.__cause__ is expected["cause"]
    assert exc.__context__ is expected["ctx"]
    assert exc.__suppress_context__ is expected["suppress"]
    assert len(calls) == 2  # ref0 real, ref1 raised; ref2 never called
    assert calls[0][0] == refs[0] and calls[1][0] == refs[1]


@pytest.mark.parametrize(
    "sent_cls", [LogicValidationError, DerivationLimitError,
                 ProofEnumerationLimitError, MotifLimitError])
def test_exception_identity_second_query(sent_cls):
    qs = (atom("p", "a", "b"), atom("q", "a", "c"), atom("z", "a", "b"))
    ref = REFERENCES[0]
    real_canon = hm.canonical_motif_key
    real_qsm = hm.query_subtree_motif_keys
    o_c, o_q = hm.canonical_motif_key, hm.query_subtree_motif_keys
    calls = []
    sent = _sentinel(
        sent_cls, f"t0018-q2-{sent_cls.__name__}",
        LogicValidationError("t0018-q2-context"))
    expected = {
        "msg": str(sent), "ctx": sent.__context__,
        "cause": sent.__cause__, "suppress": sent.__suppress_context__,
    }

    def spy_canon(*a, **k):
        calls.append(("canon", a[0], a[1], a[2]))
        return real_canon(*a, **k)

    def spy_qsm(*a, **k):
        calls.append(("qsm", a[1], a[0]))
        if a[1] is qs[1]:
            raise sent
        return real_qsm(*a, **k)

    hm.canonical_motif_key = spy_canon
    hm.query_subtree_motif_keys = spy_qsm
    try:
        with pytest.raises(sent_cls) as exc_info:
            heldout_motif_hits(W_C, qs, (ref,), **_base())
    finally:
        hm.canonical_motif_key = o_c
        hm.query_subtree_motif_keys = o_q
    exc = exc_info.value
    assert exc is sent
    assert type(exc) is sent_cls
    assert str(exc) == expected["msg"]
    assert exc.__cause__ is expected["cause"]
    assert exc.__context__ is expected["ctx"]
    assert exc.__suppress_context__ is expected["suppress"]
    # one reference keyed with the original triple; q1 success + q2 raise;
    # q3 never called
    assert calls == [
        ("canon", ref[0], ref[1], ref[2]),
        ("qsm", qs[0], W_C),
        ("qsm", qs[1], W_C),
    ]
    assert not any(c[0] == "qsm" and c[1] is qs[2] for c in calls)


def test_reference_dependency_failure_precedes_target_c0():
    # a real reference-dependency failure (not a local shape error) with C=0
    # must surface the reference error, not a target-side C=0 budget error.
    refs = (REFERENCES[0], REFERENCES[1], REFERENCES[2])
    real_canon = hm.canonical_motif_key
    real_qsm = hm.query_subtree_motif_keys
    o_c, o_q = hm.canonical_motif_key, hm.query_subtree_motif_keys
    canon_calls = []
    qsm_calls = []
    sent = _sentinel(
        ProofLimitError, "t0018-ref2-c0-sentinel",
        LogicValidationError("t0018-ref2-c0-context"))
    expected = {
        "msg": str(sent), "ctx": sent.__context__,
        "cause": sent.__cause__, "suppress": sent.__suppress_context__,
    }

    def spy_canon(*a, **k):
        canon_calls.append(a)
        if len(canon_calls) == 1:
            return real_canon(*a, **k)
        raise sent

    def spy_qsm(*a, **k):
        qsm_calls.append(a)
        return real_qsm(*a, **k)

    hm.canonical_motif_key = spy_canon
    hm.query_subtree_motif_keys = spy_qsm
    try:
        with pytest.raises(ProofLimitError) as exc_info:
            heldout_motif_hits(W_A, _legal_queries(), refs,
                               max_fact_checks=0, max_derivations=6,
                               max_proof_steps=10, max_orientations=4)
    finally:
        hm.canonical_motif_key = o_c
        hm.query_subtree_motif_keys = o_q
    exc = exc_info.value
    assert exc is sent
    assert type(exc) is ProofLimitError
    assert str(exc) == expected["msg"]
    assert exc.__cause__ is expected["cause"]
    assert exc.__context__ is expected["ctx"]
    assert exc.__suppress_context__ is expected["suppress"]
    # not a target-side C=0 validation: the reference error surfaces first
    assert str(exc) != ("heldout_motifs.max_fact_checks must be a non-bool "
                        "positive integer; got int")
    # ref0 keyed, ref1 raised, ref2 and all (C=0) targets never called
    assert len(canon_calls) == 2
    assert canon_calls[0] == refs[0] and canon_calls[1] == refs[1]
    assert not qsm_calls


def test_stack_ref_bad_shape_before_target_c0():
    with pytest.raises(LogicValidationError) as exc_info:
        heldout_motif_hits(W_C, _legal_queries(),
                           (REFERENCES[0], (None,)),
                           max_fact_checks=0, max_derivations=0,
                           max_proof_steps=0, max_orientations=0)
    assert str(exc_info.value) == (
        "heldout_motifs.references[1] must be a (clauses, query, proof) tuple")
    # not a target-side budget error:
    assert str(exc_info.value) != (
        "proofs.max_fact_checks must be a non-bool positive integer; got int")


# ---------------------------------------------------------------------------
# Group G: purity
# ---------------------------------------------------------------------------

def _snapshot(world, queries, references):
    def pa(at):
        return (at.pred, at.args)
    def pc(cl):
        return (tuple(pa(a) for a in cl.body), pa(cl.head))
    def pr(ref):
        rc, rq, rp = ref
        return (tuple(pc(cl) for cl in rc), pa(rq),
                tuple((s.clause_index, s.premise_steps, pa(s.conclusion))
                      for s in rp))
    raw = json.dumps([tuple(pc(cl) for cl in world),
                      tuple(pa(q) for q in queries),
                      tuple(pr(ref) for ref in references)],
                     ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def test_purity_and_stability():
    qs1 = (atom("q", "a", "b"), atom("p", "a", "b"),
           atom("z", "a", "b"), atom("q", "a", "b"))
    qs0 = (atom("z", "a", "b"),)
    snap0 = _snapshot(W_A, qs1, REFERENCES)
    r1 = heldout_motif_hits(W_A, qs1, REFERENCES)
    # interleave the empty-world query, re-run
    assert heldout_motif_hits((), qs0, REFERENCES) == (hs(),)
    r2 = heldout_motif_hits(W_A, qs1, REFERENCES)
    assert _snapshot(W_A, qs1, REFERENCES) == snap0  # inputs untouched
    assert r1 == r2  # call stability
    assert r1 == (hs(0, 1, 2, 5), hs(0), hs(), hs(0, 1, 2, 5))
    # the return itself is a real hashable tuple of frozensets of ints
    hash(r1)
    assert type(r1) is tuple
    for i, hit in enumerate(r1):
        assert type(hit) is frozenset
        for j in hit:
            assert type(j) is int and j >= 0
        # re-run after a failure attempt left no residue
    with pytest.raises(MotifLimitError):
        heldout_motif_hits(W_A, qs1, REFERENCES,
                           max_fact_checks=6, max_derivations=6,
                           max_proof_steps=10, max_orientations=1)
    r3 = heldout_motif_hits(W_A, qs1, REFERENCES)
    assert r3 == r1


# ---------------------------------------------------------------------------
# Group H: hard import isolation (subprocess, new src on sys.path)
# ---------------------------------------------------------------------------

_ISOLATION_SCRIPT = r'''
import sys, importlib, types, os, json
SRC = @SRC_DIR@
sys.path.insert(0, SRC)
BLOCKED = ["torch", "yaml",
            "kmesh.logic.engine", "kmesh.logic.reference_engine"]
MSG = "t0018-blocked: "
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
        mod = types.ModuleType(r); mod.__name__ = r; mod.__path__ = []
        sys.modules[r] = mod
        try:
            importlib.import_module(r + ".t0018_probe")
            print("UNBLOCKED-S:" + r + ".t0018_probe")
            sys.exit(1)
        except ModuleNotFoundError as e:
            assert str(e) == MSG + r + ".t0018_probe", "sub wrong: " + repr(e)
            print("BLOCKED-S:" + r + ".t0018_probe")
        finally:
            sys.modules.pop(r, None)
    import kmesh.logic.heldout_motifs as hm
    want = os.path.realpath(os.path.join(SRC, "kmesh", "logic",
                                          "heldout_motifs.py"))
    assert os.path.realpath(hm.__file__) == want, "path: " + str(hm.__file__)
    from kmesh.logic.types import Atom, Clause
    from kmesh.logic.proof import ProofStep
    def a(p,x,y): return Atom(p,(x,y))
    def fct(p,x,y): return Clause((),a(p,x,y))
    def cop(p,q): return Clause((a(p,"?x","?y"),), a(q,"?x","?y"))
    def inv(p,q): return Clause((a(p,"?x","?y"),), a(q,"?y","?x"))
    def j(p,r,q): return Clause((a(p,"?x","?y"),a(r,"?y","?z")),a(q,"?x","?z"))
    refs = (
        ((fct("p","a","b"),), a("p","a","b"), (ProofStep(0,(),a("p","a","b")),)),
        ((fct("p","a","b"), cop("p","q")), a("q","a","b"),
         (ProofStep(0,(),a("p","a","b")), ProofStep(1,(0,),a("q","a","b")))),
        ((fct("p","a","b"), inv("p","q")), a("q","b","a"),
         (ProofStep(0,(),a("p","a","b")), ProofStep(1,(0,),a("q","b","a")))),
        ((fct("p","a","b"), fct("r","b","c"), j("p","r","q")), a("q","a","c"),
         (ProofStep(0,(),a("p","a","b")), ProofStep(1,(),a("r","b","c")),
          ProofStep(2,(0,1),a("q","a","c")))),
        ((fct("f","m","n"), fct("g","n","o"), cop("f","h"), j("h","g","k")),
          a("k","m","o"),
         (ProofStep(0,(),a("f","m","n")), ProofStep(2,(0,),a("h","m","n")),
          ProofStep(1,(),a("g","n","o")), ProofStep(3,(1,2),a("k","m","o")))),
        ((fct("s","m","n"), cop("s","t")), a("t","m","n"),
         (ProofStep(0,(),a("s","m","n")), ProofStep(1,(0,),a("t","m","n")))),
    )
    w1 = (fct("p","a","b"), fct("r","b","a"), cop("p","q"), inv("r","q"))
    q1 = a("q","a","b")
    qs1 = (a("q","a","b"), a("p","a","b"), a("z","a","b"), a("q","a","b"))
    res1 = hm.heldout_motif_hits(w1, qs1, refs,
           max_fact_checks=2, max_derivations=4, max_proof_steps=6,
           max_orientations=2)
    want1 = (frozenset([0,1,2,5]), frozenset([0]), frozenset(),
             frozenset([0,1,2,5]))
    assert res1 == want1, "H1 mismatch: " + repr(res1)
    assert type(res1) is tuple and all(type(x) is frozenset for x in res1)
    # H2 real call under the active finder
    w2 = (fct("p","a","b"), fct("r","b","c"), cop("p","u"), j("u","r","v"),
          cop("v","t"))
    qs2 = (a("t","a","c"), a("p","a","b"))
    res2 = hm.heldout_motif_hits(w2, qs2, refs,
           max_fact_checks=6, max_derivations=6, max_proof_steps=20,
           max_orientations=4)
    want2 = (frozenset([0,1,4,5]), frozenset([0]))
    assert res2 == want2, "H2 mismatch: " + repr(res2)
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
    # -I (isolated) still emits .pyc into the imported package tree despite
    # PYTHONDONTWRITEBYTECODE=1 in the env; add -B to explicitly suppress
    # bytecode writing so the check does not pollute the worktree.
    r = subprocess.run([sys.executable, "-I", "-B", "-c", script],
                       capture_output=True, text=True, timeout=180, env=env)
    assert r.returncode == 0, "exit=%d\n%s\n%s" % (
        r.returncode, r.stdout, r.stderr)
    for tag in ("torch", "yaml", "kmesh.logic.engine",
                "kmesh.logic.reference_engine"):
        assert "BLOCKED-R:" + tag in r.stdout, "missing " + tag
        assert "BLOCKED-S:" + tag + ".t0018_probe" in r.stdout, "missing sub " + tag
    assert "ISOLATION-OK" in r.stdout
    assert "BAD:" not in r.stdout
    assert "UNBLOCKED" not in r.stdout
