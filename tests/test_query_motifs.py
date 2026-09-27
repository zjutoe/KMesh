"""T0017 tests for ``query_motifs.query_subtree_motif_keys`` (D36).

Union of complete rooted subtree motif keys for one ground query: T0009
enumerates every raw proof, T0016 keys every occurrence position of every
raw proof, and the API returns the union.  Expected keys are the frozen
hand-checked literals of motif_identity_v1 §4 and the handoff (never derived
from the product).  Object-identity spy checks on the two real T0009/T0016
binding sites, delegation/budget propagation, orientation-budget validation,
input errors identical to a direct T0009 call, invariance/purity, and hard
import isolation.

Only the accepted whitelist is imported (stdlib + ``kmesh.logic.types`` /
T0009 ``proof_enumeration`` / T0016 ``subtree_motifs`` / T0014 ``motif`` /
T0009 limit types + the target).  No solver / enumeration-internal / torch /
YAML / file access.  All fixtures are fixed literals.
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
from kmesh.logic.proof_enumeration import enumerate_proofs, ProofEnumerationLimitError
from kmesh.logic.derivations import DerivationLimitError
from kmesh.logic.motif import MotifLimitError
from kmesh.logic.proof import ProofStep, ProofLimitError
import kmesh.logic.query_motifs as qm
from kmesh.logic.query_motifs import query_subtree_motif_keys


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def atom(pred, x, y):
    return Atom(pred, (x, y))


def fact(pred, x, y):
    return Clause((), atom(pred, x, y))


def copy_rule(p, q):
    return Clause((atom(p, "?x", "?y"),), atom(q, "?x", "?y"))


def inv_rule(p, q):
    return Clause((atom(p, "?x", "?y"),), atom(q, "?y", "?x"))


def join_rule(p, r, q):
    return Clause((atom(p, "?x", "?y"), atom(r, "?y", "?z")), atom(q, "?x", "?z"))


# frozen hand-checked literal keys (motif_identity_v1 §4 + handoff §3)
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


def _world(id_):
    return Q_FIXTURES[id_][1], Q_FIXTURES[id_][2]


# ---------------------------------------------------------------------------
# fixture table (handoff §3); index 0..10 == Q0..Q10
# ---------------------------------------------------------------------------

Q_FIXTURES = [
    ("Q0", (), atom("q", "a", "b"), (1, 1, 1, 1), 0, frozenset()),
    ("Q1", (fact("p", "a", "b"),), atom("p", "a", "b"), (1, 1, 1, 1), 1, frozenset((F,))),
    ("Q2", (fact("p", "a", "b"), fact("p", "a", "b")),
     atom("p", "a", "b"), (1, 2, 2, 1), 2, frozenset((F,))),
    ("Q3", (fact("p", "a", "b"), copy_rule("p", "q")), atom("q", "a", "b"),
     (1, 2, 3, 1), 1, frozenset((F, C))),
    ("Q4", (fact("p", "a", "b"), fact("r", "b", "a"), copy_rule("p", "q"), inv_rule("r", "q")),
     atom("q", "a", "b"), (2, 4, 6, 1), 2, frozenset((F, C, I))),
    ("Q5", (fact("q", "a", "b"), fact("p", "a", "b"), fact("r", "a", "b"),
            copy_rule("p", "q"), copy_rule("r", "q")),
     atom("q", "a", "b"), (2, 5, 7, 1), 3, frozenset((F, C))),
    ("Q6", (fact("p", "a", "b"), fact("p", "a", "d"), fact("r", "b", "c"),
            fact("r", "d", "c"), join_rule("p", "r", "q")),
     atom("q", "a", "c"), (6, 6, 10, 2), 2, frozenset((F, J))),
    ("Q7", (fact("q", "a", "c"), fact("p", "a", "b"), fact("r", "b", "c"),
            join_rule("p", "r", "q")),
     atom("q", "a", "c"), (2, 4, 6, 2), 2, frozenset((F, J))),
    ("Q8", (fact("p", "a", "b"), copy_rule("p", "q")), atom("q", "z", "b"),
     (1, 2, 1, 1), 0, frozenset()),
    ("Q9", (fact("p", "a", "b"), fact("r", "b", "c"), inv_rule("r", "s")),
     atom("p", "a", "b"), (1, 3, 1, 1), 1, frozenset((F,))),
    ("Q10", (fact("p", "a", "b"),
             Clause((atom("p", "?x", "?y"), atom("p", "?x", "?y")), atom("q", "?x", "?y"))),
     atom("q", "a", "b"), (2, 2, 4, 2), 1, frozenset((F, R))),
]


def kw_for(id_):
    c, d, s, o = Q_FIXTURES[id_][3]
    return {"max_fact_checks": c, "max_derivations": d,
            "max_proof_steps": s, "max_orientations": o}


# ---------------------------------------------------------------------------
# Group A: hand-checked anchor unions (Q0-Q10)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("id_, world, query, budgets, raw_count, expected",
                         [tuple(f) for f in Q_FIXTURES],
                         ids=[f[0] for f in Q_FIXTURES])
def test_anchor_union(id_, world, query, budgets, raw_count, expected):
    c, d, s, o = budgets
    found = query_subtree_motif_keys(world, query, max_fact_checks=c,
                                     max_derivations=d, max_proof_steps=s,
                                     max_orientations=o)
    # full literal comparison, not just cardinality
    assert found == expected
    assert type(found) is frozenset
    # cross-check against accepted T0009: the union is over ALL raw proofs,
    # and the documented raw-proof count is reached with the same budgets
    raw = enumerate_proofs(world, query, max_fact_checks=c, max_derivations=d,
                           max_proof_steps=s)
    assert len(raw) == raw_count


def test_q4_only_one_tree_or_whole_tree_fails():
    # a mutant that only keys the first raw tree misses I; one that only
    # keys the whole tree misses the F and C positions.
    w, q = _world(4)
    found = query_subtree_motif_keys(w, q, **kw_for(4))
    assert F in found and C in found and I in found
    assert found == frozenset((F, C, I))
    assert len(found) == 3


def test_q5_three_proofs_two_keys():
    w, q = _world(5)
    raw = enumerate_proofs(w, q, **{k: kw_for(5)[k] for k in
                                     ("max_fact_checks", "max_derivations", "max_proof_steps")})
    assert len(raw) == 3  # three distinct canonical proofs
    found = query_subtree_motif_keys(w, q, **kw_for(5))
    # two distinct keys: the fact and the two COPY support positions
    assert found == frozenset((F, C))
    assert len(found) == 2


def test_q6_shared_bridge_key_is_not_uniqueness():
    w, q = _world(6)
    raw = enumerate_proofs(w, q, **{k: kw_for(6)[k] for k in
                                     ("max_fact_checks", "max_derivations", "max_proof_steps")})
    assert len(raw) == 2  # two bridge proofs
    found = query_subtree_motif_keys(w, q, **kw_for(6))
    # both proofs share the same JOIN motif J; motif count != proof count
    assert found == frozenset((F, J))
    assert len(found) == 2


def test_q10_repeated_premise_keeps_duplicate_keys():
    w, q = _world(10)
    raw = enumerate_proofs(w, q, **{k: kw_for(10)[k] for k in
                                     ("max_fact_checks", "max_derivations", "max_proof_steps")})
    assert len(raw) == 1
    found = query_subtree_motif_keys(w, q, **kw_for(10))
    # R is the complete literal key with both identical occurrences kept
    assert found == frozenset((F, R))
    assert R in found
    assert len(found) == 2


def test_q9_unrelated_world_still_enumerated():
    # T0009 must complete the full-world derivation check even when the
    # union is one trivial fact; the r/s derivation consumes the budget.
    w, q = _world(9)
    found = query_subtree_motif_keys(w, q, **kw_for(9))
    assert found == frozenset((F,))
    c, d, s, o = kw_for(9).values()
    with pytest.raises(DerivationLimitError) as exc_info:
        query_subtree_motif_keys(w, q, max_fact_checks=c, max_derivations=d - 1,
                                 max_proof_steps=s, max_orientations=o)
    assert type(exc_info.value) is DerivationLimitError
    assert str(exc_info.value) == (
        "enumerate.max_derivations exhausted before enumeration completed")
    # S-1 = 0 is rejected by T0009's budget validation (before enumeration)
    with pytest.raises(LogicValidationError) as exc_info:
        query_subtree_motif_keys(w, q, max_fact_checks=c, max_derivations=d,
                                 max_proof_steps=s - 1, max_orientations=o)
    assert type(exc_info.value) is LogicValidationError
    assert str(exc_info.value) == (
        "proofs.max_proof_steps must be a non-bool positive integer; got int")


def test_q2_duplicate_sources_union_unaffected():
    w, q = _world(2)
    c, d, s, o = kw_for(2).values()
    raw = enumerate_proofs(w, q, max_fact_checks=c, max_derivations=d,
                           max_proof_steps=s)
    assert len(raw) == 2  # two identical-source raw proofs
    found = query_subtree_motif_keys(w, q, max_fact_checks=c, max_derivations=d,
                                     max_proof_steps=s, max_orientations=o)
    assert found == frozenset((F,))
    assert len(found) == 1


# ---------------------------------------------------------------------------
# Group B: budget and orientation boundaries
# ---------------------------------------------------------------------------

def test_q6_c_d_s_boundaries():
    w, q = _world(6)
    kw = kw_for(6)
    c, d, s, o = kw.values()
    # success at the table budgets
    assert query_subtree_motif_keys(w, q, **kw) == frozenset((F, J))
    for name, budget, exc_type, msg in (
        ("max_fact_checks", c - 1, DerivationLimitError,
         "enumerate.max_fact_checks exhausted before enumeration completed"),
        ("max_derivations", d - 1, DerivationLimitError,
         "enumerate.max_derivations exhausted before enumeration completed"),
        ("max_proof_steps", s - 1, ProofEnumerationLimitError,
         "proofs.max_proof_steps exhausted before enumeration completed"),
    ):
        kw2 = dict(kw)
        kw2[name] = budget
        with pytest.raises(exc_type) as exc_info:
            query_subtree_motif_keys(w, q, **kw2)
        assert type(exc_info.value) is exc_type
        assert str(exc_info.value) == msg


def test_q7_late_orientation_failure():
    w, q = _world(7)
    c, d, s, o = kw_for(7).values()
    # fact proof succeeds first; the JOIN fails under O=1 (late, per-tree)
    with pytest.raises(MotifLimitError) as exc_info:
        query_subtree_motif_keys(w, q, max_fact_checks=c, max_derivations=d,
                                 max_proof_steps=s, max_orientations=1)
    assert type(exc_info.value) is MotifLimitError
    assert str(exc_info.value) == (
        "motif.max_orientations insufficient for complete canonicalization")
    # O=2 succeeds fully (both bridge proofs keyed)
    assert query_subtree_motif_keys(w, q, max_fact_checks=c, max_derivations=d,
                                    max_proof_steps=s, max_orientations=2) == frozenset((F, J))


def test_q8_world_budgets_run_with_empty_query():
    w, q = _world(8)
    with pytest.raises(DerivationLimitError) as exc_info:
        query_subtree_motif_keys(w, q, max_fact_checks=1,
                                 max_derivations=1, max_proof_steps=1,
                                 max_orientations=1)
    assert type(exc_info.value) is DerivationLimitError
    assert str(exc_info.value) == (
        "enumerate.max_derivations exhausted before enumeration completed")
    # with the table budgets the same world yields an empty union (not an
    # error): the enumeration completed and produced zero proofs
    found = query_subtree_motif_keys(w, q, **kw_for(8))
    assert found == frozenset()
    assert type(found) is frozenset
    # O=0 must still fail even for the empty enumeration
    c, d, s, o = kw_for(8).values()
    with pytest.raises(LogicValidationError) as exc_info:
        query_subtree_motif_keys(w, q, max_fact_checks=c, max_derivations=d,
                                 max_proof_steps=s, max_orientations=0)
    assert type(exc_info.value) is LogicValidationError
    assert str(exc_info.value) == (
        "query_motifs.max_orientations must be a non-bool positive integer; "
        "got int")


# ---------------------------------------------------------------------------
# Group C: joint call-order spy (T0009 first, original objects, exact keyword
# budgets, per-tree exactly once)
# ---------------------------------------------------------------------------

# Hostile inputs for the delegation guard: any len/iter/getitem/contains/
# bool/repr access to the object itself is appended to a shared events log
# with a "hostile:" prefix.  The spy adds its own "enum"/"psm" markers to
# the same log, so a correct implementation that forwards the original
# objects unmodified must produce markers only (no hostile events, "enum"
# first) - pre-enumeration len/iteration/copy checks are then detected.


class HostileTuple(tuple):
    """Tuple that logs every inspection dunder call on itself."""

    _events = None

    def __new__(cls, items, events):
        obj = super().__new__(cls, items)
        cls._events = events
        return obj

    def _note(self, what):
        HostileTuple._events.append("hostile:" + what)

    def __len__(self):
        self._note("len")
        return tuple.__len__(self)

    def __iter__(self):
        self._note("iter")
        return tuple.__iter__(self)

    def __getitem__(self, item):
        self._note("getitem")
        return tuple.__getitem__(self, item)

    def __contains__(self, value):
        self._note("contains")
        return tuple.__contains__(self, value)

    def __bool__(self):
        self._note("bool")
        return tuple.__len__(self) > 0

    def __repr__(self):
        self._note("repr")
        return tuple.__repr__(self)


class HostileAtom(Atom):
    """Atom that logs every inspection dunder call on itself."""

    _events = None

    def __init__(self, pred, args, events):
        super().__init__(pred, args)
        HostileAtom._events = events

    def _note(self, what):
        HostileAtom._events.append("hostile:" + what)

    def __len__(self):
        self._note("len")
        return len(self.args)

    def __iter__(self):
        self._note("iter")
        return iter(self.args)

    def __bool__(self):
        self._note("bool")
        return bool(self.args)

    def __repr__(self):
        self._note("repr")
        return Atom.__repr__(self)

    def __str__(self):
        self._note("str")
        return Atom.__repr__(self)
def _anchor_world():
    return (fact("p", "a", "b"),), atom("p", "a", "b")


def test_call_order_identity_nondefault_budgets():
    events = []
    w = HostileTuple((fact("p", "a", "b"),), events)
    q = HostileAtom("p", ("a", "b"), events)
    p0 = (ProofStep(0, (), atom("p", "a", "b")),)
    p1 = (ProofStep(0, (), atom("p", "b", "c")),)
    o_enum = qm.enumerate_proofs
    o_psm = qm.proof_subtree_motif_keys
    calls = []
    fake_dirs = {
        id(p0): (("k", "a"), ("k", "b")),
        id(p1): (("k", "a"), ("k", "c")),
    }

    def fake_enum(*a, **k):
        # accepts the original object without inspecting it
        events.append("enum")
        calls.append(("enum", a, k))
        return (p0, p1, p0)

    def fake_psm(*a, **k):
        # accepts the original objects without inspecting them
        events.append("psm")
        calls.append(("psm", a, k))
        return fake_dirs[id(a[2])]

    qm.enumerate_proofs = fake_enum
    qm.proof_subtree_motif_keys = fake_psm
    try:
        res = query_subtree_motif_keys(
            w, q, max_fact_checks=11, max_derivations=13,
            max_proof_steps=17, max_orientations=19,
        )
    finally:
        qm.enumerate_proofs = o_enum
        qm.proof_subtree_motif_keys = o_psm
    # T0009 is the first business operation; hostile inputs record any len/
    # iter/getitem/contains/bool/repr access, and the fake dependencies
    # themselves never inspect the objects:
    assert events[0] == "enum"
    assert not any(ev.startswith("hostile:") for ev in events)
    # union of ALL three directory calls; no early dedup of proofs
    assert res == frozenset((("k", "a"), ("k", "b"), ("k", "c")))
    kinds = [c[0] for c in calls]
    # T0009 first, then T0016 exactly once per raw tree, in returned order
    assert kinds == ["enum", "psm", "psm", "psm"]
    e_a, e_k = calls[0][1], calls[0][2]
    assert e_a[0] is w and e_a[1] is q
    assert e_k == {"max_fact_checks": 11, "max_derivations": 13,
                   "max_proof_steps": 17}
    for c in calls[1:]:
        a, k = c[1], c[2]
        assert a[0] is w and a[1] is q
        assert k == {"max_steps": 17, "max_orientations": 19}
    proof_order = [c[1][2] for c in calls[1:]]
    assert proof_order == [p0, p1, p0]
    # no identity dedup: p0 appears twice in the log
    assert proof_order.count(p0) == 2


def test_default_budget_passthrough():
    w, q = _anchor_world()
    p0 = (ProofStep(0, (), atom("p", "a", "b")),)
    o_enum = qm.enumerate_proofs
    o_psm = qm.proof_subtree_motif_keys
    calls = []

    def fake_enum(*a, **k):
        calls.append(("enum", a, k))
        return (p0,)

    def fake_psm(*a, **k):
        calls.append(("psm", a, k))
        return (("k", "d"),)

    qm.enumerate_proofs = fake_enum
    qm.proof_subtree_motif_keys = fake_psm
    try:
        res = query_subtree_motif_keys(w, q)
    finally:
        qm.enumerate_proofs = o_enum
        qm.proof_subtree_motif_keys = o_psm
    assert res == frozenset((("k", "d"),))
    e_a, e_k = calls[0][1], calls[0][2]
    assert e_a[0] is w and e_a[1] is q
    assert e_k == {"max_fact_checks": 100000, "max_derivations": 100000,
                   "max_proof_steps": 100000}
    _, p_a, p_k = calls[1]
    assert p_a[0] is w and p_a[1] is q and p_a[2] is p0
    assert p_k == {"max_steps": 100000, "max_orientations": 100000}


def test_empty_enum_o_checked_no_psm():
    w, q = (), atom("q", "a", "b")  # Q0: empty enumeration
    o_enum = qm.enumerate_proofs
    o_psm = qm.proof_subtree_motif_keys
    calls = []
    reached_psm = []

    def fake_enum(*a, **k):
        calls.append(("enum", a, k))
        return ()

    def fake_psm(*a, **k):
        reached_psm.append(a)
        return ("unreachable",)

    qm.enumerate_proofs = fake_enum
    qm.proof_subtree_motif_keys = fake_psm
    try:
        # O=1 valid -> empty frozenset, T0016 never called
        res = query_subtree_motif_keys(w, q, max_fact_checks=1,
                                       max_derivations=1, max_proof_steps=1,
                                       max_orientations=1)
        assert res == frozenset()
        assert type(res) is frozenset
        assert len(calls) == 1 and calls[0][0] == "enum"
        assert not reached_psm
        # O=0 invalid -> LogicValidationError after the single enum call
        calls.clear()
        with pytest.raises(LogicValidationError) as exc_info:
            query_subtree_motif_keys(w, q, max_fact_checks=1,
                                     max_derivations=1, max_proof_steps=1,
                                     max_orientations=0)
        assert str(exc_info.value) == (
            "query_motifs.max_orientations must be a non-bool positive integer; "
            "got int")
        assert len(calls) == 1 and calls[0][0] == "enum"
        assert not reached_psm
    finally:
        qm.enumerate_proofs = o_enum
        qm.proof_subtree_motif_keys = o_psm


def test_enum_failure_precedes_o_check():
    w, q = _anchor_world()
    # (exception class, constructor message or None)
    specs = (
        (LogicValidationError, "t0017-enum-lv-sentinel"),
        (DerivationLimitError, "t0017-enum-der-sentinel"),
        (ProofEnumerationLimitError, None),
    )
    o_enum = qm.enumerate_proofs
    o_psm = qm.proof_subtree_motif_keys
    reached_psm = []

    def fake_psm(*a, **k):
        reached_psm.append(a)
        return ("unreachable",)

    for idx, (cls, sent_msg) in enumerate(specs):
        sent = cls(sent_msg) if sent_msg is not None else cls()
        ctx = LogicValidationError("t0017-enum-fail-context-%d" % idx)
        sent.__context__ = ctx
        expected_message = str(sent)
        calls = []

        def make_fake_enum(_sent=sent):
            def fake(*a, **k):
                calls.append(("enum", a, k))
                raise _sent
            return fake

        qm.enumerate_proofs = make_fake_enum(sent)
        qm.proof_subtree_motif_keys = fake_psm
        try:
            with pytest.raises(type(sent)) as exc_info:
                # O is invalid too: the T0009 failure must precede the O check
                query_subtree_motif_keys(w, q, max_fact_checks=1,
                                         max_derivations=1, max_proof_steps=1,
                                         max_orientations=0)
        finally:
            # both spies restored even if an assertion below fails
            qm.enumerate_proofs = o_enum
            qm.proof_subtree_motif_keys = o_psm
        exc = exc_info.value
        # original class, message, instance and context must propagate
        assert exc is sent
        assert type(exc) is cls
        assert str(exc) == expected_message
        assert exc.__context__ is ctx
        assert exc.__suppress_context__ is False
        assert exc.__cause__ is None
        assert calls == [("enum", (w, q),
                          {"max_fact_checks": 1, "max_derivations": 1,
                           "max_proof_steps": 1})]
        assert not reached_psm
        # no partial result / no retry / no subsequent call

def test_psm_failure_second_tree_stops_third():
    w, q = _anchor_world()
    p0 = (ProofStep(0, (), atom("p", "a", "b")),)
    p1 = (ProofStep(0, (), atom("r", "a", "b")),)
    p2 = (ProofStep(0, (), atom("s", "a", "b")),)
    o_enum = qm.enumerate_proofs
    o_psm = qm.proof_subtree_motif_keys
    # (exception class, constructor message)
    specs = (
        (MotifLimitError, "t0017-psm-motif-sentinel"),
        (ProofLimitError, "t0017-psm-proof-sentinel"),
        (LogicValidationError, "t0017-psm-lv-sentinel"),
    )

    for idx, (cls, sent_msg) in enumerate(specs):
        sent = cls(sent_msg)
        ctx = LogicValidationError("t0017-psm-fail-context-%d" % idx)
        sent.__context__ = ctx
        expected_message = str(sent)
        calls = []

        def fake_enum(*a, **k):
            calls.append(("enum", a, k))
            return (p0, p1, p2)

        def fake_psm(*a, **k):
            calls.append(("psm", a, k))
            if a[2] is p1:
                raise sent
            return o_psm(*a, **k)

        qm.enumerate_proofs = fake_enum
        qm.proof_subtree_motif_keys = fake_psm
        try:
            with pytest.raises(type(sent)) as exc_info:
                query_subtree_motif_keys(w, q, max_fact_checks=1,
                                         max_derivations=1, max_proof_steps=1,
                                         max_orientations=1)
        finally:
            # both spies restored even if an assertion below fails
            qm.enumerate_proofs = o_enum
            qm.proof_subtree_motif_keys = o_psm
        exc = exc_info.value
        # original class, message, instance and context must propagate
        assert exc is sent
        assert type(exc) is cls
        assert str(exc) == expected_message
        assert exc.__context__ is ctx
        assert exc.__suppress_context__ is False
        assert exc.__cause__ is None
        # p0 succeeded (real T0016), p1 raised; p2 must never be called
        n_psm = sum(1 for c in calls if c[0] == "psm")
        assert n_psm == 2
        last = calls[-1]
        assert last[0] == "psm" and last[1][2] is p1
        assert not any(c[1][2] is p2 for c in calls if c[0] == "psm")
    # real Q7 world: the same late-failure behavior end-to-end
    w7, q7 = _world(7)
    with pytest.raises(MotifLimitError) as exc_info:
        query_subtree_motif_keys(w7, q7, **{k: kw_for(7)[k]
                                            for k in ("max_fact_checks",
                                                      "max_derivations",
                                                      "max_proof_steps")},
                                 max_orientations=1)
    assert str(exc_info.value) == (
        "motif.max_orientations insufficient for complete canonicalization")


# ---------------------------------------------------------------------------
# Group D: orientation input validation
# ---------------------------------------------------------------------------

class PosInt(int):
    """Positive int subclass to verify the type-name in the error message."""


_GIGINT = 10 ** 5000  # 5001 digits; never formatted in these tests


@pytest.fixture
def _int_limit_4300():
    """Run the case under the explicit 4300-digit int<->str conversion limit.

    10 ** 5000 has 5001 digits; any formatting of the budget value (str, repr,
    f-string) raises ValueError.  The current limit is saved, set to exactly
    4300 (asserted) and restored in finally."""
    assert hasattr(sys, "set_int_max_str_digits"), (
        "int str-digit limit control must exist in this environment")
    orig_limit = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    assert sys.get_int_max_str_digits() == 4300
    try:
        yield
    finally:
        sys.set_int_max_str_digits(orig_limit)


@pytest.mark.parametrize(
    "oid, o, type_name",
    [
        ("none", None, "NoneType"),
        ("true", True, "bool"),
        ("false", False, "bool"),
        ("zero", 0, "int"),
        ("negative", -1, "int"),
        ("float", 1.5, "float"),
        ("string", "2", "str"),
        ("subint", PosInt(1), "PosInt"),
        ("gigneg", -_GIGINT, "int"),
    ],
    # explicit short ids: the giant int must never be str()-ed by pytest
    ids=["none", "true", "false", "zero", "neg", "float", "str", "subint",
         "gigneg"],
)
def test_invalid_orientation_inputs(oid, o, type_name, _int_limit_4300):
    # Q0: empty enumeration, legal C/D/S.  O is checked after the (empty)
    # enumeration and must raise with the exact class + full message; the
    # spy proves T0016 receives zero calls.
    w, q = (), atom("q", "a", "b")
    o_psm = qm.proof_subtree_motif_keys
    calls = []

    def fake_psm(*a, **k):
        calls.append((a, k))

    try:
        qm.proof_subtree_motif_keys = fake_psm
        query_subtree_motif_keys(w, q, max_fact_checks=1,
                                 max_derivations=1, max_proof_steps=1,
                                 max_orientations=o)
        raise AssertionError("expected LogicValidationError")
    except LogicValidationError as exc:
        assert str(exc) == (
            "query_motifs.max_orientations must be a non-bool positive integer; "
            "got " + type_name)
    finally:
        qm.proof_subtree_motif_keys = o_psm
    assert calls == []  # T0016 zero calls


def test_gigant_orientations_q1(_int_limit_4300):
    # Positive 10**5000 (5001 digits) must succeed under the explicit
    # 4300-digit limit: no code path may format the budget value.  The
    # giant int is passed by reference only and never str/repr/f-stringed
    # (and the short param ids guarantee it is not str()-ed by pytest).
    w, q = _world(1)
    res = query_subtree_motif_keys(w, q, max_fact_checks=1,
                                   max_derivations=1, max_proof_steps=1,
                                   max_orientations=_GIGINT)
    assert res == frozenset((F,))
    assert type(res) is frozenset


# ---------------------------------------------------------------------------
# Group E: delegated input boundaries + signature + __all__
# ---------------------------------------------------------------------------

def _direct_enum(w, q, **kws):
    """Return (type, message) of the error from a direct T0009 call, or
    (None, None) on success.  Only C/D/S go to T0009 (no orientation)."""
    kws = {k: v for k, v in kws.items() if k != "max_orientations"}
    try:
        enumerate_proofs(w, q, **kws)
        return None, None
    except (LogicValidationError, DerivationLimitError,
            ProofEnumerationLimitError) as e:
        return type(e), str(e)
    except Exception as e:  # pragma: no cover
        raise AssertionError("unexpected from direct T0009") from e


def _api_enum(w, q, **kws):
    """Same, but through the T0017 API."""
    try:
        query_subtree_motif_keys(w, q, **kws)
        return None, None
    except (LogicValidationError, DerivationLimitError,
            ProofEnumerationLimitError) as e:
        return type(e), str(e)
    except Exception as e:  # pragma: no cover
        raise AssertionError("unexpected from API") from e


def test_delegation_clauses_list_and_bad_member():
    w, q = _world(1)
    bad = kw_for(1)
    assert _api_enum(list(w), q, **bad) == (LogicValidationError,
                                            "proofs.clauses must be a tuple of Clause; got list")
    assert _api_enum((fact("p", "a", "b"), 1), q, **bad) == (LogicValidationError,
                                                             "proofs.clauses[1] must be a Clause; got int")
    # matches a direct T0009 call
    assert _direct_enum(list(w), q, **bad) == _api_enum(list(w), q, **bad)
    assert _direct_enum((fact("p", "a", "b"), 1), q, **bad) == _api_enum((fact("p", "a", "b"), 1), q, **bad)


def test_delegation_query_type_groundness():
    w, q = _world(1)
    bad = kw_for(1)
    for query in (1, atom("q", "?x", "b")):
        assert _direct_enum(w, query, **bad) == _api_enum(w, query, **bad)
    assert _api_enum(w, 1, **bad) == (LogicValidationError,
                                      "proofs.query must be an Atom; got int")
    assert _api_enum(w, atom("q", "?x", "b"), **bad) == (LogicValidationError,
                                                         "proofs.query must be a ground Atom")


def test_delegation_invalid_c_d_s():
    w, q = _world(1)
    base = dict(kw_for(1))
    for name, value, msg in (
        ("max_fact_checks", 0,
         "proofs.max_fact_checks must be a non-bool positive integer; got int"),
        ("max_derivations", True,
         "proofs.max_derivations must be a non-bool positive integer; got bool"),
        ("max_proof_steps", 0,
         "proofs.max_proof_steps must be a non-bool positive integer; got int"),
    ):
        kw2 = dict(base)
        kw2[name] = value
        assert _direct_enum(w, q, **kw2) == _api_enum(w, q, **kw2)
        assert _api_enum(w, q, **kw2) == (LogicValidationError, msg)


def test_delegation_cyclic_world_o_zero():
    # world p(?x,?y) -> p(?x,?y), no facts; Q0 query; O=0. T0009 must run
    # the full-world dependency check FIRST and raise the exact cycle error
    # before any orientation check.
    w = (Clause((atom("p", "?x", "?y"),), atom("p", "?x", "?y")),)
    q = atom("q", "z", "b")
    kw = dict(max_fact_checks=1, max_derivations=1, max_proof_steps=1,
              max_orientations=0)
    d_t, d_m = _direct_enum(w, q, **kw)
    a_t, a_m = _api_enum(w, q, **kw)
    assert (d_t, d_m) == (a_t, a_m)
    assert (a_t, a_m) == (LogicValidationError,
                          "dependency.clauses: cyclic predicate dependency")


def test_delegation_generator_clauses_not_consumed():
    w, q = _world(1)
    state = {"entered": False}

    def gen_clauses():
        state["entered"] = True
        yield fact("p", "a", "b")

    kw = kw_for(1)
    g = gen_clauses()
    try:
        enumerate_proofs(g, q, max_fact_checks=kw["max_fact_checks"],
                         max_derivations=kw["max_derivations"],
                         max_proof_steps=kw["max_proof_steps"])
        raise AssertionError("expected LogicValidationError")
    except LogicValidationError as e:
        d_t, d_m = type(e), str(e)
    try:
        query_subtree_motif_keys(g, q, **kw)
        raise AssertionError("expected LogicValidationError")
    except LogicValidationError as exc:
        a_t, a_m = type(exc), str(exc)
    assert (d_t, d_m) == (a_t, a_m)
    assert a_m == "proofs.clauses must be a tuple of Clause; got generator"
    assert not state["entered"]  # body never consumed


def test_signature_and_all_public():
    w, q = _world(1)
    # missing query
    try:
        query_subtree_motif_keys(w)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    # extra positional arg
    try:
        query_subtree_motif_keys(w, q, 5)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    # unknown keyword
    try:
        query_subtree_motif_keys(w, q, max_bogus=1)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass
    assert qm.__all__ == ["query_subtree_motif_keys"]


# ---------------------------------------------------------------------------
# Group F: invariance & purity
# ---------------------------------------------------------------------------

def test_q4_global_rel_ent_bijection():
    w, q = _world(4)
    rel = {"p": "P", "r": "R", "q": "Q"}
    ent = {"a": "A", "b": "B"}

    def ren(at):
        return Atom(rel[at.pred], tuple(
            t if t.startswith("?") else ent[t] for t in at.args))

    w_r = tuple(
        Clause(tuple(ren(b) for b in c.body), ren(c.head)) for c in w)
    q_r = ren(q)
    assert (w_r, q_r) != (w, q)  # fields actually changed
    kw = kw_for(4)
    base = query_subtree_motif_keys(w, q, **kw)
    assert query_subtree_motif_keys(w_r, q_r, **kw) == base
    assert base == frozenset((F, C, I))


def test_q4_world_reversed():
    w, q = _world(4)
    kw = kw_for(4)
    base = query_subtree_motif_keys(w, q, **kw)
    assert w[::-1] != w  # actual change
    assert query_subtree_motif_keys(w[::-1], q, **kw) == base
    assert base == frozenset((F, C, I))


def test_q4_rule_var_bijection():
    # rename ?x->?u, ?y->?v only inside the two rule schemata
    w, q = _world(4)
    w_v = (
        w[0],  # fact p(a,b)
        w[1],  # fact r(b,a)
        Clause((atom("p", "?u", "?v"),), atom("q", "?u", "?v")),
        Clause((atom("r", "?u", "?v"),), atom("q", "?v", "?u")),
    )
    assert w_v != w  # actual change in the two rule bodies/heads
    kw = kw_for(4)
    base = query_subtree_motif_keys(w, q, **kw)
    assert query_subtree_motif_keys(w_v, q, **kw) == base
    assert base == frozenset((F, C, I))


def test_q6_body_swap_invariance():
    w, q = _world(6)
    def swapped(c):
        if len(c.body) == 2:
            return Clause(c.body[::-1], c.head)
        return c

    w_s = tuple(swapped(x) for x in w)
    assert w_s != w  # the two-premise JOIN body order actually changed
    kw = kw_for(6)
    base = query_subtree_motif_keys(w, q, **kw)
    assert query_subtree_motif_keys(w_s, q, **kw) == base
    assert base == frozenset((F, J))


def test_q6_global_rel_ent_bijection():
    # global relation/entity bijection, query renamed in sync (Q6)
    w, q = _world(6)
    rel = {"p": "P", "r": "R", "q": "Q"}
    ent = {"a": "A", "b": "B", "c": "C", "d": "D"}

    def ren(at):
        return Atom(rel[at.pred], tuple(
            t if t.startswith("?") else ent[t] for t in at.args))

    w_r = tuple(
        Clause(tuple(ren(b) for b in c.body), ren(c.head)) for c in w)
    q_r = ren(q)
    assert w_r != w and q_r != q  # fields actually changed
    kw = kw_for(6)
    base = query_subtree_motif_keys(w, q, **kw)
    assert query_subtree_motif_keys(w_r, q_r, **kw) == base
    assert base == frozenset((F, J))


def test_q6_rule_var_bijection():
    # rename the rule-local variables in the JOIN schema only (Q6)
    w, q = _world(6)
    w_v = (
        w[0],  # p(a,b)
        w[1],  # p(a,d)
        w[2],  # r(b,c)
        w[3],  # r(d,c)
        Clause((atom("p", "?u", "?v"), atom("r", "?v", "?w")),
               atom("q", "?u", "?w")),
    )
    assert w_v != w  # schema variables actually renamed
    kw = kw_for(6)
    base = query_subtree_motif_keys(w, q, **kw)
    assert query_subtree_motif_keys(w_v, q, **kw) == base
    assert base == frozenset((F, J))


def test_q6_world_reversed():
    # world clause order reversed (Q6)
    w, q = _world(6)
    w_rev = w[::-1]
    assert w_rev != w  # actual input change
    kw = kw_for(6)
    base = query_subtree_motif_keys(w, q, **kw)
    assert query_subtree_motif_keys(w_rev, q, **kw) == base
    assert base == frozenset((F, J))
def test_purity_q4_q0_q4_cycle():
    w, q = _world(4)
    w0, q0 = (), atom("q", "z", "b")
    kw = kw_for(4)
    kw0 = {"max_fact_checks": 1, "max_derivations": 2, "max_proof_steps": 1,
           "max_orientations": 1}

    def snap(world, query):
        def pa(at):
            return (at.pred, at.args)
        def pc(cl):
            return (tuple(pa(b) for b in cl.body), pa(cl.head))
        raw = json.dumps([tuple(pc(x) for x in world), pa(query)],
                         ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    snap_before = snap(w, q)
    r1 = query_subtree_motif_keys(w, q, **kw)
    # interleave the Q0 call (empty world/query), then re-run Q4
    assert query_subtree_motif_keys(w0, q0, **kw0) == frozenset()
    r2 = query_subtree_motif_keys(w, q, **kw)
    assert snap(w, q) == snap_before  # inputs untouched
    assert r1 == r2  # call-stability
    assert r1 == frozenset((F, C, I))
    # the return itself is hashable
    hash(r1)
    # type is exactly frozenset and every element / nested container is a
    # real tuple (no list conversion masking)
    assert type(r1) is frozenset

    def strict(x):
        if type(x) is tuple:
            for y in x:
                strict(y)

    for key in r1:
        assert type(key) is tuple
        strict(key)


def test_q4_q0_order_insensitivity():
    w, q = _world(4)
    w0, q0 = (), atom("q", "z", "b")
    assert query_subtree_motif_keys(w0, q0, max_fact_checks=1,
                                    max_derivations=2, max_proof_steps=1,
                                    max_orientations=1) == frozenset()
    assert query_subtree_motif_keys(w, q, **kw_for(4)) == frozenset((F, C, I))


# ---------------------------------------------------------------------------
# Group G: hard import isolation
# ---------------------------------------------------------------------------

_ISOLATION_SCRIPT = r'''
import sys, importlib, types, os, json
SRC = @SRC_DIR@
sys.path.insert(0, SRC)
BLOCKED = ["torch", "yaml",
            "kmesh.logic.engine", "kmesh.logic.reference_engine"]
MSG = "t0017-blocked: "
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
            importlib.import_module(r + ".t0017_probe")
            print("UNBLOCKED-S:" + r + ".t0017_probe")
            sys.exit(1)
        except ModuleNotFoundError as e:
            assert str(e) == MSG + r + ".t0017_probe", "sub wrong: " + repr(e)
            print("BLOCKED-S:" + r + ".t0017_probe")
        finally:
            sys.modules.pop(r, None)
    import kmesh.logic.query_motifs as qm
    want = os.path.realpath(os.path.join(SRC, "kmesh", "logic", "query_motifs.py"))
    assert os.path.realpath(qm.__file__) == want, "path: " + str(qm.__file__)
    from kmesh.logic.types import Atom, Clause
    def atom(p,x,y): return Atom(p,(x,y))
    def fct(p,x,y): return Clause((),atom(p,x,y))
    # Q0: empty world, no proofs -> frozenset()
    w0 = ()
    q0 = atom("q","a","b")
    assert qm.query_subtree_motif_keys(w0, q0,
            max_fact_checks=1, max_derivations=1, max_proof_steps=1,
            max_orientations=1) == frozenset()
    # Q4: full expected literals under the active finder
    F = ("proof_motif_v1", (((0, 0, 1), (0, ("c", 0), ("c", 1)), ()),))
    C = ("proof_motif_v1", (
        ((0, 0, 1), (0, ("v", 0), ("v", 1)), ((1, ("v", 0), ("v", 1)),)),
        ((1, 0, 1), (1, ("c", 0), ("c", 1)), ()),
    ))
    I = ("proof_motif_v1", (
        ((0, 0, 1), (0, ("v", 0), ("v", 1)), ((1, ("v", 1), ("v", 0)),)),
        ((1, 1, 0), (1, ("c", 1), ("c", 0)), ()),
    ))
    w4 = (
        fct("p","a","b"), fct("r","b","a"),
        Clause((atom("p","?x","?y"),), atom("q","?x","?y")),
        Clause((atom("r","?x","?y"),), atom("q","?y","?x")),
    )
    q4 = atom("q","a","b")
    r4 = qm.query_subtree_motif_keys(w4, q4,
            max_fact_checks=2, max_derivations=4, max_proof_steps=6,
            max_orientations=1)
    want4 = frozenset((F,C,I))
    assert r4 == want4, "Q4 mismatch: " + str(r4)
    # Q7: fact + JOIN, O=2 -> full expected
    w7 = (
        fct("q","a","c"), fct("p","a","b"), fct("r","b","c"),
        Clause((atom("p","?x","?y"), atom("r","?y","?z")), atom("q","?x","?z")),
    )
    q7 = atom("q","a","c")
    r7 = qm.query_subtree_motif_keys(w7, q7,
            max_fact_checks=2, max_derivations=4, max_proof_steps=6,
            max_orientations=2)
    J = ("proof_motif_v1", (
        ((0, 0, 1), (0, ("v", 0), ("v", 1)),
         ((1, ("v", 0), ("v", 2)), (2, ("v", 2), ("v", 1)))),
        ((1, 0, 2), (1, ("c", 0), ("c", 2)), ()),
        ((2, 2, 1), (2, ("c", 2), ("c", 1)), ()),
    ))
    want7 = frozenset((F,J))
    assert r7 == want7, "Q7 mismatch: " + str(r7)
    # final scan: no blocked root (with or without dot prefix) in sys.modules
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
                       capture_output=True, text=True, timeout=180, env=env)
    assert r.returncode == 0, "exit=%d\n%s\n%s" % (r.returncode, r.stdout, r.stderr)
    for tag in ("torch", "yaml", "kmesh.logic.engine", "kmesh.logic.reference_engine"):
        assert "BLOCKED-R:" + tag in r.stdout, "missing " + tag
        assert "BLOCKED-S:" + tag + ".t0017_probe" in r.stdout, "missing sub " + tag
    assert "ISOLATION-OK" in r.stdout
    assert "BAD:" not in r.stdout
    assert "UNBLOCKED" not in r.stdout
