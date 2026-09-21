"""T0009 contract tests: finite raw proof enumeration for one ground query.

Covers P0-P10 hand-calculated worlds, a 3x3 full-combination grid, exact
budget boundaries, input validation order and diagnostics, T0008 call
contract and exception propagation, long chains, input purity, independent
verifier verification, a tampered-proof control, and interpreter-level
isolation from torch/yaml/solvers/verify_proof.
"""

from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path

import pytest

from kmesh.logic.derivations import (
    DerivationLimitError,
    GroundDerivation,
    enumerate_derivations,
)
from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.proof_enumeration import (
    ProofEnumerationLimitError,
    enumerate_proofs,
)
from kmesh.logic.types import Atom, Clause, LogicValidationError

CLE = "enumerate.max_fact_checks exhausted before enumeration completed"
DLE = "enumerate.max_derivations exhausted before enumeration completed"
PLE = "proofs.max_proof_steps exhausted before enumeration completed"


def atom(pred: str, x: str, y: str) -> Atom:
    return Atom(pred, (x, y))


def fact(pred: str, x: str, y: str) -> Clause:
    return Clause((), atom(pred, x, y))


def rule(*body: Atom, head: Atom) -> Clause:
    return Clause(tuple(body), head)


def step(i: int, refs, pred: str, x: str, y: str) -> ProofStep:
    return ProofStep(i, tuple(refs), atom(pred, x, y))


def run(clauses, query, c, d, s):
    return enumerate_proofs(
        clauses,
        query,
        max_fact_checks=c,
        max_derivations=d,
        max_proof_steps=s,
    )


# --------------------------------------------------------------------------
# Hand-calculated worlds (T0009 planning examples P0-P10).
# Budgets (C, D, S) are the smallest successful values.
# --------------------------------------------------------------------------

_PXY = lambda: atom("p", "?x", "?y")  # noqa: E731
_QXY = lambda: atom("q", "?x", "?y")  # noqa: E731
_RXY = lambda: atom("r", "?x", "?y")  # noqa: E731
_SXY = lambda: atom("s", "?x", "?y")  # noqa: E731


def join_rule() -> Clause:
    # p(?x,?y) ^ q(?y,?z) -> r(?x,?z)
    return rule(atom("p", "?x", "?y"), atom("q", "?y", "?z"), head=atom("r", "?x", "?z"))


P0 = {
    "clauses": (),
    "query": atom("r", "b", "a"),
    "budgets": (1, 1, 1),
    "proofs": (),
}

P1 = {
    "clauses": (fact("p", "a", "b"),),
    "query": atom("p", "a", "b"),
    "budgets": (1, 1, 1),
    "proofs": ((step(0, (), "p", "a", "b"),),),
}

P2 = {
    "clauses": (
        fact("p", "a", "b"),
        rule(_PXY(), head=_QXY()),
        rule(_QXY(), head=atom("r", "?y", "?x")),
    ),
    "query": atom("r", "b", "a"),
    "budgets": (2, 3, 6),
    "proofs": (
        (
            step(0, (), "p", "a", "b"),
            step(1, (0,), "q", "a", "b"),
            step(2, (1,), "r", "b", "a"),
        ),
    ),
}

P3 = {
    "clauses": (
        fact("p", "a", "b"),
        fact("q", "b", "c"),
        join_rule(),
        rule(_RXY(), head=atom("s", "?y", "?x")),
    ),
    "query": atom("s", "c", "a"),
    "budgets": (3, 4, 9),
    "proofs": (
        (
            step(0, (), "p", "a", "b"),
            step(1, (), "q", "b", "c"),
            step(2, (0, 1), "r", "a", "c"),
            step(3, (2,), "s", "c", "a"),
        ),
    ),
}

_RULES_PQ = rule(_PXY(), head=_QXY())
_RULES_PR = rule(_PXY(), head=_RXY())
_RULES_QR = rule(_QXY(), _RXY(), head=_SXY())

P4 = {
    "clauses": (fact("p", "a", "b"), _RULES_PQ, _RULES_PR, _RULES_QR),
    "query": atom("s", "a", "b"),
    "budgets": (4, 4, 10),
    "proofs": (
        (
            step(0, (), "p", "a", "b"),
            step(1, (0,), "q", "a", "b"),
            step(0, (), "p", "a", "b"),
            step(2, (2,), "r", "a", "b"),
            step(3, (1, 3), "s", "a", "b"),
        ),
    ),
}

P5 = {
    "clauses": (
        fact("p", "a", "b"),
        fact("p", "a", "c"),
        rule(atom("p", "?x", "?y"), head=atom("q", "?x", "k")),
        rule(atom("q", "?x", "k"), head=atom("r", "?x", "k")),
    ),
    "query": atom("r", "a", "k"),
    "budgets": (3, 5, 12),
    "proofs": (
        (
            step(0, (), "p", "a", "b"),
            step(2, (0,), "q", "a", "k"),
            step(3, (1,), "r", "a", "k"),
        ),
        (
            step(1, (), "p", "a", "c"),
            step(2, (0,), "q", "a", "k"),
            step(3, (1,), "r", "a", "k"),
        ),
    ),
}

P6 = {
    "clauses": (
        fact("p", "a", "b"),
        fact("p", "a", "b"),
        rule(_PXY(), _PXY(), head=_QXY()),
    ),
    "query": atom("q", "a", "b"),
    "budgets": (2, 3, 14),
    "proofs": (
        (step(0, (), "p", "a", "b"), step(0, (), "p", "a", "b"), step(2, (0, 1), "q", "a", "b")),
        (step(0, (), "p", "a", "b"), step(1, (), "p", "a", "b"), step(2, (0, 1), "q", "a", "b")),
        (step(1, (), "p", "a", "b"), step(0, (), "p", "a", "b"), step(2, (0, 1), "q", "a", "b")),
        (step(1, (), "p", "a", "b"), step(1, (), "p", "a", "b"), step(2, (0, 1), "q", "a", "b")),
    ),
}

P7 = {
    "clauses": (fact("p", "a", "b"), fact("p", "a", "b"), _RULES_PQ, _RULES_PR, _RULES_QR),
    "query": atom("s", "a", "b"),
    "budgets": (4, 5, 30),
    "proofs": (
        (
            step(0, (), "p", "a", "b"),
            step(2, (0,), "q", "a", "b"),
            step(0, (), "p", "a", "b"),
            step(3, (2,), "r", "a", "b"),
            step(4, (1, 3), "s", "a", "b"),
        ),
        (
            step(0, (), "p", "a", "b"),
            step(2, (0,), "q", "a", "b"),
            step(1, (), "p", "a", "b"),
            step(3, (2,), "r", "a", "b"),
            step(4, (1, 3), "s", "a", "b"),
        ),
        (
            step(1, (), "p", "a", "b"),
            step(2, (0,), "q", "a", "b"),
            step(0, (), "p", "a", "b"),
            step(3, (2,), "r", "a", "b"),
            step(4, (1, 3), "s", "a", "b"),
        ),
        (
            step(1, (), "p", "a", "b"),
            step(2, (0,), "q", "a", "b"),
            step(1, (), "p", "a", "b"),
            step(3, (2,), "r", "a", "b"),
            step(4, (1, 3), "s", "a", "b"),
        ),
    ),
}

P8 = {
    "clauses": (fact("q", "a", "b"), fact("p", "a", "b"), rule(_PXY(), head=_QXY())),
    "query": atom("q", "a", "b"),
    "budgets": (1, 3, 4),
    "proofs": (
        (step(0, (), "q", "a", "b"),),
        (step(1, (), "p", "a", "b"), step(2, (0,), "q", "a", "b")),
    ),
}

P9 = {
    "clauses": (
        fact("p", "a", "b"),
        fact("q", "c", "d"),
        rule(atom("p", "a", "b"), atom("q", "c", "d"), head=atom("r", "e", "f")),
    ),
    "query": atom("r", "e", "f"),
    "budgets": (2, 3, 5),
    "proofs": (
        (
            step(0, (), "p", "a", "b"),
            step(1, (), "q", "c", "d"),
            step(2, (0, 1), "r", "e", "f"),
        ),
    ),
}

P10 = {
    "clauses": (
        fact("p", "a", "b"),
        fact("q", "b", "c"),
        fact("q", "b", "d"),
        join_rule(),
    ),
    "query": atom("r", "a", "c"),
    "budgets": (3, 5, 5),
    "proofs": (
        (
            step(0, (), "p", "a", "b"),
            step(1, (), "q", "b", "c"),
            step(3, (0, 1), "r", "a", "c"),
        ),
    ),
}

WORLD_NAMES = ("P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10")
WORLDS = {name: globals()[name] for name in WORLD_NAMES}


@pytest.mark.parametrize("name", WORLD_NAMES)
def test_world_success_and_full_tuple(name: str) -> None:
    world = WORLDS[name]
    c, d, s = world["budgets"]
    out = run(world["clauses"], world["query"], c, d, s)
    assert isinstance(out, tuple)
    assert out == world["proofs"]
    for proof in out:
        assert isinstance(proof, tuple)
        for entry in proof:
            assert isinstance(entry, ProofStep)
        # Independent verifier accepts every returned proof.
        assert verify_proof(world["clauses"], world["query"], proof) is True


@pytest.mark.parametrize("name", WORLD_NAMES)
def test_world_budget_boundaries(name: str) -> None:
    world = WORLDS[name]
    c, d, s = world["budgets"]
    for label, kwargs, exc_cls, msg in (
        ("C", {"max_fact_checks": c - 1}, DerivationLimitError, CLE),
        ("D", {"max_derivations": d - 1}, DerivationLimitError, DLE),
        ("S", {"max_proof_steps": s - 1}, ProofEnumerationLimitError, PLE),
    ):
        value = kwargs[list(kwargs)[0]]
        if world["budgets"][("CDS").index(label)] <= 1:
            continue
        budgeted = {"max_fact_checks": c, "max_derivations": d, "max_proof_steps": s}
        budgeted.update(kwargs)
        with pytest.raises(exc_cls) as exc:
            enumerate_proofs(world["clauses"], world["query"], **budgeted)
        assert str(exc.value) == msg


def test_world_p4_tampered_premise_reference_fails_verifier() -> None:
    world = P4
    valid = world["proofs"][0]
    assert valid == (
        step(0, (), "p", "a", "b"),
        step(1, (0,), "q", "a", "b"),
        step(0, (), "p", "a", "b"),
        step(2, (2,), "r", "a", "b"),
        step(3, (1, 3), "s", "a", "b"),
    )
    tampered = (*valid[:3], step(2, (1,), "r", "a", "b"), valid[4])
    assert verify_proof(world["clauses"], world["query"], valid) is True
    assert verify_proof(world["clauses"], world["query"], tampered) is False


# --------------------------------------------------------------------------
# 3x3 full-combination grid (A2).
# a copies of fact p(a,b), b copies of fact q(b,c), one JOIN rule.
# C = 2, D = a+b+1, S = a+b+3ab, a*b proofs in nested (p, q) order.
# --------------------------------------------------------------------------

def grid_world(a: int, b: int) -> tuple[Clause, ...]:
    return (
        tuple(fact("p", "a", "b") for _ in range(a))
        + tuple(fact("q", "b", "c") for _ in range(b))
        + (join_rule(),)
    )


def grid_expected(a: int, b: int) -> tuple[tuple[ProofStep, ...], ...]:
    out = []
    for i in range(a):
        for j in range(b):
            out.append(
                (
                    step(i, (), "p", "a", "b"),
                    step(a + j, (), "q", "b", "c"),
                    step(a + b, (0, 1), "r", "a", "c"),
                )
            )
    return tuple(out)


def grid_budgets(a: int, b: int) -> tuple[int, int, int]:
    return (2, a + b + 1, a + b + 3 * a * b)


@pytest.mark.parametrize(
    ("a", "b"),
    [(a, b) for a in (1, 2, 3) for b in (1, 2, 3)],
    ids=[f"g{a}x{b}" for a in (1, 2, 3) for b in (1, 2, 3)],
)
def test_grid_full_combination(a: int, b: int) -> None:
    clauses = grid_world(a, b)
    c, d, s = grid_budgets(a, b)
    out = run(clauses, atom("r", "a", "c"), c, d, s)
    assert out == grid_expected(a, b)
    assert len(out) == a * b
    for proof in out:
        assert verify_proof(clauses, atom("r", "a", "c"), proof) is True


@pytest.mark.parametrize(
    ("a", "b"),
    [(1, 1), (3, 3), (2, 1)],
    ids=["g-bound-1x1", "g-bound-3x3", "g-bound-2x1"],
)
def test_grid_budget_boundaries(a: int, b: int) -> None:
    clauses = grid_world(a, b)
    c, d, s = grid_budgets(a, b)
    common = dict(max_fact_checks=c, max_derivations=d, max_proof_steps=s)

    with pytest.raises(DerivationLimitError) as exc_c:
        enumerate_proofs(clauses, atom("r", "a", "c"), max_fact_checks=c - 1, max_derivations=d, max_proof_steps=s)
    assert str(exc_c.value) == CLE

    with pytest.raises(DerivationLimitError) as exc_d:
        enumerate_proofs(clauses, atom("r", "a", "c"), max_fact_checks=c, max_derivations=d - 1, max_proof_steps=s)
    assert str(exc_d.value) == DLE

    with pytest.raises(ProofEnumerationLimitError) as exc_s:
        enumerate_proofs(
            clauses,
            atom("r", "a", "c"),
            max_fact_checks=c,
            max_derivations=d,
            max_proof_steps=s - 1,
        )
    assert str(exc_s.value) == PLE


# --------------------------------------------------------------------------
# Entry validation: order, complete diagnostics, no T0008 call.
# --------------------------------------------------------------------------

def test_clauses_container_diagnostics() -> None:
    query = atom("p", "a", "b")
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs([fact("p", "a", "b")], query)
    assert str(exc.value) == "proofs.clauses must be a tuple of Clause; got list"

    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(None, query)
    assert str(exc.value) == "proofs.clauses must be a tuple of Clause; got NoneType"

    consumed = []

    def generator():
        consumed.append(1)
        yield 0
        raise AssertionError("clauses generator must not be consumed")

    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(generator(), query)
    assert str(exc.value) == "proofs.clauses must be a tuple of Clause; got generator"
    # A wrong implementation that consumes the generator once before the
    # container check (next(gen, None)) would hit the yield; the marker must
    # not have fired.
    assert consumed == []


def test_clauses_member_diagnostics_before_cycle_check() -> None:
    cyc_a = rule(_QXY(), head=_RXY())
    cyc_b = rule(_RXY(), head=_QXY())
    member_bad = (cyc_a, cyc_b, None)
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(member_bad, atom("p", "a", "b"))
    assert str(exc.value) == "proofs.clauses[2] must be a Clause; got NoneType"

    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs((None,), atom("p", "a", "b"))
    assert str(exc.value) == "proofs.clauses[0] must be a Clause; got NoneType"


def test_query_diagnostics() -> None:
    clauses = (fact("p", "a", "b"),)
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(clauses, None)
    assert str(exc.value) == "proofs.query must be an Atom; got NoneType"

    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(clauses, Atom("p", ("?x", "b")))
    assert str(exc.value) == "proofs.query must be a ground Atom"

    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(clauses, 7)
    assert str(exc.value) == "proofs.query must be an Atom; got int"


@pytest.mark.parametrize(
    "budget_name",
    ["max_fact_checks", "max_derivations", "max_proof_steps"],
    ids=["C", "D", "S"],
)
@pytest.mark.parametrize(
    ("value", "type_name"),
    [(True, "bool"), (0, "int"), (-1, "int"), (1.5, "float"), ("x", "str")],
    ids=["bool", "zero", "negative", "float", "str"],
)
def test_budget_diagnostics(budget_name: str, value: object, type_name: str) -> None:
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(
            (fact("p", "a", "b"),),
            atom("p", "a", "b"),
            **{budget_name: value},
        )
    assert str(exc.value) == (
        f"proofs.{budget_name} must be a non-bool positive integer; got {type_name}"
    )


def test_validation_priority_chain() -> None:
    query = atom("p", "a", "b")
    member_bad = (None,)
    bad_query = Atom("p", ("?x", "b"))

    # member before query
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(member_bad, bad_query)
    assert str(exc.value) == "proofs.clauses[0] must be a Clause; got NoneType"

    # query before budgets
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs((fact("p", "a", "b"),), bad_query, max_fact_checks=True)
    assert str(exc.value) == "proofs.query must be a ground Atom"

    # C before D before S
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(
            (fact("p", "a", "b"),), query, max_fact_checks=True, max_derivations=True
        )
    assert str(exc.value) == "proofs.max_fact_checks must be a non-bool positive integer; got bool"

    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(
            (fact("p", "a", "b"),), query, max_derivations=True, max_proof_steps=True
        )
    assert str(exc.value) == "proofs.max_derivations must be a non-bool positive integer; got bool"

    # Local validation precedes the T0008 call: a cycle world must not mask
    # an earlier local error (cycles surface only inside enumerate_derivations).
    cyc_world = (rule(_QXY(), head=_RXY()), rule(_RXY(), head=_QXY()))
    # S budget validation precedes the T0008 call as well: an illegal S on a
    # cyclic world must surface the local S diagnostic, not the cycle error
    # that only enumerate_derivations could raise.
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(cyc_world, atom("q", "a", "b"), max_fact_checks=True)
    assert str(exc.value) == "proofs.max_fact_checks must be a non-bool positive integer; got bool"
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(cyc_world, atom("q", "a", "b"), max_proof_steps=0)
    assert str(exc.value) == "proofs.max_proof_steps must be a non-bool positive integer; got int"
    with pytest.raises(LogicValidationError) as exc:
        enumerate_proofs(cyc_world, atom("q", "a", "b"))
    assert str(exc.value) == "dependency.clauses: cyclic predicate dependency"


def test_cycle_in_unrelated_component_still_rejects() -> None:
    # Even when the query is a plain fact / absent atom, a cycle in another
    # predicate component rejects the call (T0008 validates the whole world).
    cyc = (
        fact("p", "a", "b"),
        rule(_RXY(), head=_SXY()),
        rule(_SXY(), head=_RXY()),
    )
    for query in (atom("p", "a", "b"), atom("w", "x", "y")):
        with pytest.raises(LogicValidationError) as exc:
            enumerate_proofs(cyc, query, max_fact_checks=10, max_derivations=10, max_proof_steps=10)
        assert str(exc.value) == "dependency.clauses: cyclic predicate dependency"


def test_positional_and_unknown_kwargs_rejected() -> None:
    with pytest.raises(TypeError):
        enumerate_proofs((fact("p", "a", "b"),), atom("p", "a", "b"), 5)
    with pytest.raises(TypeError):
        enumerate_proofs(
            (fact("p", "a", "b"),),
            atom("p", "a", "b"),
            max_proof_steps=5,
            max_steps=2,
        )


# --------------------------------------------------------------------------
# Large-integer validation (sys.get_int_max_str_digits boundary).
# Huge values never enter exception messages; huge budgets still run.
# --------------------------------------------------------------------------

BIG = 10**5000 + 42
NEG_BIG = -(10**5000 + 42)


@pytest.fixture()
def small_int_str_limit():
    old = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    try:
        yield
    finally:
        sys.set_int_max_str_digits(old)


def test_large_integer_diagnostic_messages(small_int_str_limit) -> None:
    cases = {}
    try:
        enumerate_proofs(BIG, atom("r", "b", "a"))
    except LogicValidationError as exc:
        cases["clauses"] = str(exc)
    try:
        enumerate_proofs((BIG,), atom("r", "b", "a"))
    except LogicValidationError as exc:
        cases["member"] = str(exc)
    try:
        enumerate_proofs((fact("p", "a", "b"),), BIG)
    except LogicValidationError as exc:
        cases["query"] = str(exc)
    for name in ("max_fact_checks", "max_derivations", "max_proof_steps"):
        try:
            enumerate_proofs(
                (fact("p", "a", "b"),), atom("r", "b", "a"), **{name: NEG_BIG}
            )
        except LogicValidationError as exc:
            cases[name] = str(exc)
    assert len(cases) == 6
    # The exact messages below prove no huge value ever reaches a diagnostic
    # while the int-str limit is 4300 (the fixture would raise ValueError if
    # the product stringified these values).
    assert cases["clauses"] == "proofs.clauses must be a tuple of Clause; got int"
    assert cases["member"] == "proofs.clauses[0] must be a Clause; got int"
    assert cases["query"] == "proofs.query must be an Atom; got int"
    for name in ("max_fact_checks", "max_derivations", "max_proof_steps"):
        assert cases[name] == (
            f"proofs.{name} must be a non-bool positive integer; got int"
        )
    # A huge positive integer is a valid budget: the call executes normally
    # and no diagnostic embeds the huge value.
    out = enumerate_proofs(
        (fact("p", "a", "b"),),
        atom("p", "a", "b"),
        max_fact_checks=BIG,
        max_derivations=BIG,
        max_proof_steps=BIG,
    )
    assert out == ((step(0, (), "p", "a", "b"),),)
    assert verify_proof(
        (fact("p", "a", "b"),), atom("p", "a", "b"), out[0]
    ) is True
    with pytest.raises(LogicValidationError):
        enumerate_proofs(
            (fact("p", "a", "b"),),
            atom("p", "a", "b"),
            max_fact_checks=NEG_BIG,
        )


# --------------------------------------------------------------------------
# T0008 call contract: exactly one call, exact args, exception pass-through,
# no call on invalid input.
# --------------------------------------------------------------------------

def test_t0008_called_exactly_once_with_exact_args(monkeypatch) -> None:
    import kmesh.logic.proof_enumeration as pe

    calls = []

    def fake(clauses, *, max_fact_checks, max_derivations):
        calls.append((clauses, max_fact_checks, max_derivations))
        return (GroundDerivation(0, (), atom("p", "a", "b")),)

    monkeypatch.setattr(pe, "enumerate_derivations", fake)
    clauses = (fact("p", "a", "b"),)
    out = run(clauses, atom("p", "a", "b"), 7, 9, 100)
    assert calls == [(clauses, 7, 9)]
    assert out == ((step(0, (), "p", "a", "b"),),)
    assert verify_proof(clauses, atom("p", "a", "b"), out[0]) is True


def test_t0008_exception_identity_passes_through(monkeypatch) -> None:
    import kmesh.logic.proof_enumeration as pe

    originals = {
        "cle": DerivationLimitError(CLE),
        "dle": DerivationLimitError(DLE),
        "cycle": LogicValidationError("dependency cycle: q -> r -> q"),
    }

    for key, exc in originals.items():

        def fake(clauses, *, max_fact_checks, max_derivations, _exc=exc):
            raise _exc

        monkeypatch.setattr(pe, "enumerate_derivations", fake)
        with pytest.raises(type(exc)) as result:
            enumerate_proofs(
                (fact("p", "a", "b"),), atom("p", "a", "b")
            )
        assert result.value is exc


def test_t0008_not_called_on_invalid_input(monkeypatch) -> None:
    import kmesh.logic.proof_enumeration as pe

    calls = []

    def fake(clauses, *, max_fact_checks, max_derivations):
        calls.append(None)
        return ()

    monkeypatch.setattr(pe, "enumerate_derivations", fake)
    bad_inputs = (
        lambda: enumerate_proofs([fact("p", "a", "b")], atom("p", "a", "b")),
        lambda: enumerate_proofs((None,), atom("p", "a", "b")),
        lambda: enumerate_proofs((fact("p", "a", "b"),), None),
        lambda: enumerate_proofs((fact("p", "a", "b"),), Atom("p", ("?x", "b"))),
        lambda: enumerate_proofs(
            (fact("p", "a", "b"),), atom("p", "a", "b"), max_fact_checks=0
        ),
        lambda: enumerate_proofs(
            (fact("p", "a", "b"),), atom("p", "a", "b"), max_derivations=True
        ),
        lambda: enumerate_proofs(
            (fact("p", "a", "b"),), atom("p", "a", "b"), max_proof_steps=-1
        ),
    )
    for bad in bad_inputs:
        with pytest.raises((LogicValidationError,)):
            bad()
    assert calls == []


# --------------------------------------------------------------------------
# Long chain: non-recursive expansion, exact step count, determinism,
# prior-fail-then-success, input purity.
# --------------------------------------------------------------------------

def chain_world(n: int) -> tuple[tuple[Clause, ...], Atom]:
    clauses = [fact("k0", "a", "b")]
    for j in range(1, n + 1):
        clauses.append(
            rule(Atom(f"k{j-1}", ("?x", "?y")), head=Atom(f"k{j}", ("?x", "?y")))
        )
    return tuple(clauses), atom(f"k{n}", "a", "b")


def chain_proof(n: int) -> tuple[ProofStep, ...]:
    return (
        (step(0, (), "k0", "a", "b"),)
        + tuple(step(j, (j - 1,), f"k{j}", "a", "b") for j in range(1, n + 1))
    )


def test_ancestor_collection_uses_bounded_record_reads(monkeypatch) -> None:
    import kmesh.logic.proof_enumeration as pe

    # 64 COPY rules + 1 fact = 65 records. C=64, D=65, S=1: derivation
    # enumeration succeeds, then the proof budget exhausts on the first rule
    # combination. After the real T0008 returns, each record's conclusion is
    # read only through the indexed work-list traversal: a per-round full
    # re-scan of all 65 records reads 4229 times, the bound is 8 * 65.
    n = 64
    clauses, query = chain_world(n)
    stats = {"active": False, "reads": 0}
    original_getattribute = GroundDerivation.__getattribute__
    original_enumerate = pe.enumerate_derivations

    def counted_getattribute(self, name):
        if stats["active"] and name == "conclusion":
            stats["reads"] += 1
        return original_getattribute(self, name)

    def enumerate_then_count(*args, **kwargs):
        result = original_enumerate(*args, **kwargs)
        stats["active"] = True
        return result

    monkeypatch.setattr(GroundDerivation, "__getattribute__", counted_getattribute)
    monkeypatch.setattr(pe, "enumerate_derivations", enumerate_then_count)
    with pytest.raises(ProofEnumerationLimitError) as exc:
        pe.enumerate_proofs(
            clauses, query, max_fact_checks=n, max_derivations=n + 1, max_proof_steps=1
        )
    assert str(exc.value) == "proofs.max_proof_steps exhausted before enumeration completed"
    assert stats["reads"] <= 8 * (n + 1)


def test_long_chain_1200_steps_success() -> None:
    n = 1200
    clauses, query = chain_world(n)
    snapshot = [dataclasses.asdict(c) for c in clauses]
    before_query = query
    out = run(clauses, query, 1200, 1201, 721801)
    assert list(out) == [chain_proof(n)]
    assert len(out) == 1
    proof = out[0]
    assert len(proof) == 1201
    # Structure: step j cites only step j-1 via clause j.
    assert proof[0] == step(0, (), "k0", "a", "b")
    assert proof[600] == step(600, (599,), "k600", "a", "b")
    assert proof[1200] == step(1200, (1199,), "k1200", "a", "b")
    assert verify_proof(clauses, query, proof, max_steps=1201) is True
    # Determinism: a second call gives identical output.
    again = run(clauses, query, 1200, 1201, 721801)
    assert again == out
    # Input purity: values unchanged after two full calls.
    assert [dataclasses.asdict(c) for c in clauses] == snapshot
    assert query is before_query
    assert query == atom("k1200", "a", "b")


def test_long_chain_budget_boundaries() -> None:
    n = 1200
    clauses, query = chain_world(n)
    with pytest.raises(DerivationLimitError) as exc_c:
        run(clauses, query, 1200 - 1, 1201, 721801)
    assert str(exc_c.value) == CLE
    with pytest.raises(DerivationLimitError) as exc_d:
        run(clauses, query, 1200, 1201 - 1, 721801)
    assert str(exc_d.value) == DLE
    with pytest.raises(ProofEnumerationLimitError) as exc_s:
        run(clauses, query, 1200, 1201, 721801 - 1)
    assert str(exc_s.value) == PLE


def test_prior_budget_failure_does_not_poison_later_call() -> None:
    n = 1200
    clauses, query = chain_world(n)
    try:
        run(clauses, query, 1200, 1201, 721801 - 1)
    except ProofEnumerationLimitError:
        pass
    else:
        raise AssertionError("expected ProofEnumerationLimitError")
    out = run(clauses, query, 1200, 1201, 721801)
    assert list(out) == [chain_proof(n)]
    assert verify_proof(clauses, query, out[0], max_steps=1201) is True


# --------------------------------------------------------------------------
# Relevance: needed sets, unrelated atoms, empty results are not verdicts.
# --------------------------------------------------------------------------

def test_p10_other_q_fact_yields_second_query() -> None:
    clauses = P10["clauses"]
    out = run(clauses, atom("r", "a", "d"), 3, 5, 5)
    assert out == (
        (
            step(0, (), "p", "a", "b"),
            step(2, (), "q", "b", "d"),
            step(3, (0, 1), "r", "a", "d"),
        ),
    )
    assert verify_proof(clauses, atom("r", "a", "d"), out[0]) is True


def test_p7z_fact_query_ignores_unrelated_records() -> None:
    clauses = P7["clauses"] + (fact("z", "e", "f"),)
    out = run(clauses, atom("z", "e", "f"), 4, 6, 1)
    assert out == ((step(5, (), "z", "e", "f"),),)
    assert verify_proof(clauses, atom("z", "e", "f"), out[0]) is True


def test_nonexistent_query_returns_empty_tuple() -> None:
    out = run(P2["clauses"], atom("w", "x", "y"), 2, 3, 1)
    assert out == ()


def test_query_only_in_bodies_without_facts_returns_empty() -> None:
    clauses = (rule(_PXY(), head=_QXY()), rule(_QXY(), head=_RXY()))
    out = run(clauses, atom("p", "a", "b"), 1, 1, 1)
    assert out == ()


def test_t0008_overrun_is_error_not_empty_result() -> None:
    with pytest.raises(DerivationLimitError) as exc:
        run(P2["clauses"], P2["query"], 1, 3, 6)
    assert str(exc.value) == CLE


# --------------------------------------------------------------------------
# Immutability of the returned structure.
# --------------------------------------------------------------------------

def test_returned_containers_and_steps_are_immutable() -> None:
    out = run(P4["clauses"], P4["query"], *P4["budgets"])
    assert type(out) is tuple
    proof = out[0]
    assert type(proof) is tuple
    assert verify_proof(P4["clauses"], P4["query"], proof) is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        proof[0].clause_index = 1
    with pytest.raises(dataclasses.FrozenInstanceError):
        proof[0].premise_steps = (0,)


# --------------------------------------------------------------------------
# README example world: budgets C=2, D=3, S=6, one proof.
# --------------------------------------------------------------------------

def test_readme_example_world() -> None:
    # Exactly the README T0009 example world (P2 from the planning table):
    # p(a,b); p(x,y)->q(x,y); q(x,y)->r(y,x); query r(b,a); C=2, D=3, S=6.
    clauses = P2["clauses"]
    query = Atom("r", ("b", "a"))
    proofs = enumerate_proofs(
        clauses, query, max_fact_checks=2, max_derivations=3, max_proof_steps=6
    )
    assert len(proofs) == 1
    assert proofs[0] == (
        ProofStep(0, (), Atom("p", ("a", "b"))),
        ProofStep(1, (0,), Atom("q", ("a", "b"))),
        ProofStep(2, (1,), Atom("r", ("b", "a"))),
    )
    assert verify_proof(clauses, query, proofs[0]) is True
    with pytest.raises(DerivationLimitError) as exc:
        enumerate_proofs(clauses, query, max_fact_checks=1, max_derivations=3, max_proof_steps=6)
    assert str(exc.value) == CLE
    with pytest.raises(DerivationLimitError) as exc:
        enumerate_proofs(clauses, query, max_fact_checks=2, max_derivations=2, max_proof_steps=6)
    assert str(exc.value) == DLE
    with pytest.raises(ProofEnumerationLimitError) as exc:
        enumerate_proofs(clauses, query, max_fact_checks=2, max_derivations=3, max_proof_steps=5)
    assert str(exc.value) == PLE


# --------------------------------------------------------------------------
# Isolation: clean subprocess, 4 blocked import roots, verify_proof sentinel.
# --------------------------------------------------------------------------

def test_isolation_blocked_imports_in_clean_subprocess() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "reports/T0009/pi-r1-scripts/isolation_guard.py"
    proc = subprocess.run(
        [sys.executable, "-c", script.read_text(encoding="utf-8")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ISOLATION PASS" in proc.stdout
