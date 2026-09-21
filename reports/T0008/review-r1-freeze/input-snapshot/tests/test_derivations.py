"""Direct-derivation enumeration for acyclic worlds (T0008).

Every expectation below was worked by hand from the contract table; no
expected record is produced by the system under test or its private
functions.  The two old solvers are imported at test level only, solely
for the 64 micro-world closure cross-check.
"""

from collections import Counter
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import re
import pytest

from kmesh.logic.derivations import (
    DerivationLimitError,
    GroundDerivation,
    enumerate_derivations,
)
from kmesh.logic.dependency import relation_topological_order
from kmesh.logic.types import Atom, Clause, LogicValidationError

# Import-order guard, checked before any solver import in this file:
# the product pulls nothing beyond types and dependency.
for _blocked in (
    "kmesh.logic.engine",
    "kmesh.logic.reference_engine",
    "kmesh.logic.proof",
):
    assert _blocked not in sys.modules

from kmesh.logic.engine import indexed_closure  # noqa: E402
from kmesh.logic.reference_engine import reference_closure  # noqa: E402

FACT_CHECKS_MSG = (
    "enumerate.max_fact_checks exhausted before enumeration completed")
DERIVATIONS_MSG = (
    "enumerate.max_derivations exhausted before enumeration completed")
CYCLE_MSG = "dependency.clauses: cyclic predicate dependency"


def A(pred, x, y):
    return Atom(pred, (x, y))


def fact(pred, x, y):
    return Clause((), Atom(pred, (x, y)))


def rule(body, head):
    # body: list of (pred, x, y); head: (pred, x, y)
    return Clause(tuple(Atom(at[0], (at[1], at[2])) for at in body),
                  Atom(head[0], (head[1], head[2])))


def rec(index, premises, conclusion):
    return GroundDerivation(index, tuple(premises), conclusion)


# (name, clauses, exact expected records, total fact checks, total records)
MAIN_CASES = (
    ("E0", (), (), 0, 0),
    ("E1", (fact("z", "c", "d"), fact("p", "a", "b"),
            fact("p", "a", "b")),
     (rec(1, (), A("p", "a", "b")),
      rec(2, (), A("p", "a", "b")),
      rec(0, (), A("z", "c", "d"))),
     0, 3),
    ("E2", (fact("r1", "a", "b"), fact("r2", "b", "c"),
            rule([("r1", "?x", "?y"), ("r2", "?y", "?z")],
                 ("r3", "?x", "?z")),
            rule([("r3", "?x", "?y")], ("r4", "?y", "?x"))),
     (rec(0, (), A("r1", "a", "b")),
      rec(1, (), A("r2", "b", "c")),
      rec(2, (A("r1", "a", "b"), A("r2", "b", "c")), A("r3", "a", "c")),
      rec(3, (A("r3", "a", "c"),), A("r4", "c", "a"))),
     3, 4),
    ("E3", (fact("p", "a", "b"), fact("p", "a", "c"),
            rule([("p", "?x", "?y")], ("q", "?x", "k")),
            rule([("q", "?x", "k")], ("r", "?x", "k"))),
     (rec(0, (), A("p", "a", "b")),
      rec(1, (), A("p", "a", "c")),
      rec(2, (A("p", "a", "b"),), A("q", "a", "k")),
      rec(2, (A("p", "a", "c"),), A("q", "a", "k")),
      rec(3, (A("q", "a", "k"),), A("r", "a", "k"))),
     3, 5),
    ("E4", (fact("p", "a", "b"), fact("p", "c", "d"),
            fact("q", "a", "b"), fact("q", "b", "a"), fact("q", "c", "e"),
            rule([("p", "?x", "?y"), ("q", "?x", "?y")],
                 ("r", "?x", "?y"))),
     (rec(0, (), A("p", "a", "b")),
      rec(1, (), A("p", "c", "d")),
      rec(2, (), A("q", "a", "b")),
      rec(3, (), A("q", "b", "a")),
      rec(4, (), A("q", "c", "e")),
      rec(5, (A("p", "a", "b"), A("q", "a", "b")), A("r", "a", "b"))),
     8, 6),
    ("E5", (fact("p", "a", "b"), fact("p", "c", "c"),
            rule([("p", "?x", "?x")], ("r", "?x", "?x"))),
     (rec(0, (), A("p", "a", "b")),
      rec(1, (), A("p", "c", "c")),
      rec(2, (A("p", "c", "c"),), A("r", "c", "c"))),
     2, 3),
    ("E6", (fact("p", "a", "b"),
            rule([("p", "?x", "?y"), ("p", "?x", "?y")],
                 ("q", "?x", "?y"))),
     (rec(0, (), A("p", "a", "b")),
      rec(1, (A("p", "a", "b"), A("p", "a", "b")), A("q", "a", "b"))),
     2, 2),
    ("E7", (fact("p", "a", "b"),
            rule([("p", "a", "b")], ("q", "c", "d"))),
     (rec(0, (), A("p", "a", "b")),
      rec(1, (A("p", "a", "b"),), A("q", "c", "d"))),
     1, 2),
    ("E8", (fact("p", "a", "b"),
            rule([("p", "c", "d")], ("q", "c", "d"))),
     (rec(0, (), A("p", "a", "b")),),
     1, 1),
    ("E9", (fact("p", "a", "b"), fact("p", "c", "d"),
            rule([("p", "?x", "?y"), ("q", "?x", "?y")],
                 ("r", "?x", "?y"))),
     (rec(0, (), A("p", "a", "b")),
      rec(1, (), A("p", "c", "d"))),
     2, 2),
    ("E10", (fact("q", "a", "b"),
             rule([("p", "?x", "?y"), ("q", "?x", "?y")],
                  ("r", "?x", "?y"))),
     (rec(0, (), A("q", "a", "b")),),
     0, 1),
)


@pytest.mark.parametrize("case", MAIN_CASES, ids=lambda case: case[0])
def test_main_exact_records(case):
    _, clauses, expected, _, _ = case
    assert enumerate_derivations(clauses) == expected


@pytest.mark.parametrize("case", MAIN_CASES, ids=lambda case: case[0])
def test_main_fact_check_boundary(case):
    name, clauses, expected, checks, _ = case
    if checks > 0:
        assert enumerate_derivations(clauses, max_fact_checks=checks) \
            == expected
    if checks >= 2:
        # C - 1 must be a legal budget to exercise the exhaustion error;
        # C in (0, 1) has no legal one-check-smaller budget.
        with pytest.raises(DerivationLimitError,
                           match=FACT_CHECKS_MSG) as excinfo:
            enumerate_derivations(clauses, max_fact_checks=checks - 1)
        assert str(excinfo.value) == FACT_CHECKS_MSG
    else:
        # C in (0, 1): only a legal minimal budget is exercised.
        assert enumerate_derivations(clauses, max_fact_checks=1) \
            == expected


@pytest.mark.parametrize("case", MAIN_CASES, ids=lambda case: case[0])
def test_main_derivation_boundary(case):
    name, clauses, expected, _, total = case
    if total == 0:
        # E0: both budgets at the legal minimum of 1 still return ().
        assert enumerate_derivations(clauses,
                                     max_fact_checks=1,
                                     max_derivations=1) == expected
    if total > 0:
        assert enumerate_derivations(clauses,
                                     max_derivations=total) == expected
    if total > 1:
        with pytest.raises(DerivationLimitError,
                           match=DERIVATIONS_MSG) as excinfo:
            enumerate_derivations(clauses, max_derivations=total - 1)
        assert str(excinfo.value) == DERIVATIONS_MSG


def test_e8_full_derivation_budget_still_succeeds_no_new_output():
    # E8: the single fact fills a budget of 1; the later failed match
    # emits nothing, so the run must complete rather than overrun.
    clauses = (fact("p", "a", "b"), rule([("p", "c", "d")], ("q", "c", "d")))
    assert enumerate_derivations(clauses, max_derivations=1) == (
        rec(0, (), A("p", "a", "b")),)


def test_empty_input_returns_empty_tuple_with_minimal_budgets():
    assert enumerate_derivations((), max_fact_checks=1, max_derivations=1) \
        == ()


def test_all_alternative_sources_and_facts_coexist():
    clauses = (fact("p", "a", "b"), fact("q", "a", "b"),
               rule([("p", "?x", "?y")], ("q", "?x", "?y")),
               rule([("p", "?x", "?y")], ("q", "?x", "?y")),
               rule([("q", "?x", "?y")], ("r", "?x", "?y")))
    expected = (rec(0, (), A("p", "a", "b")),
                rec(1, (), A("q", "a", "b")),
                rec(2, (A("p", "a", "b"),), A("q", "a", "b")),
                rec(3, (A("p", "a", "b"),), A("q", "a", "b")),
                rec(4, (A("q", "a", "b"),), A("r", "a", "b")))
    # C=3 boundary: the duplicated q source must not widen the r bucket.
    assert enumerate_derivations(clauses, max_fact_checks=3) == expected
    with pytest.raises(DerivationLimitError, match=FACT_CHECKS_MSG):
        enumerate_derivations(clauses, max_fact_checks=2)


def test_alternative_sources_fact_after_rule_keeps_index_order():
    # Same world, q fact moved after the rules: original index order
    # inside the q head group (rule 1, rule 2, fact 3).
    clauses = (fact("p", "a", "b"),
               rule([("p", "?x", "?y")], ("q", "?x", "?y")),
               rule([("p", "?x", "?y")], ("q", "?x", "?y")),
               fact("q", "a", "b"),
               rule([("q", "?x", "?y")], ("r", "?x", "?y")))
    expected = (rec(0, (), A("p", "a", "b")),
                rec(1, (A("p", "a", "b"),), A("q", "a", "b")),
                rec(2, (A("p", "a", "b"),), A("q", "a", "b")),
                rec(3, (), A("q", "a", "b")),
                rec(4, (A("q", "a", "b"),), A("r", "a", "b")))
    assert enumerate_derivations(clauses, max_fact_checks=3) == expected


def test_upstream_alternatives_not_expanded_here():
    # r has exactly one direct record although its premise q(a,k) has
    # two upstream full proofs; the direct layer must not expand them.
    clauses = (fact("p", "a", "b"), fact("p", "a", "c"),
               rule([("p", "?x", "?y")], ("q", "?x", "k")),
               rule([("q", "?x", "k"), ("q", "?x", "k")],
                    ("r", "?x", "k")))
    expected = (rec(0, (), A("p", "a", "b")),
                rec(1, (), A("p", "a", "c")),
                rec(2, (A("p", "a", "b"),), A("q", "a", "k")),
                rec(2, (A("p", "a", "c"),), A("q", "a", "k")),
                rec(3, (A("q", "a", "k"), A("q", "a", "k")), A("r", "a", "k")))
    # Total C=4: two q applications, then the two q-q premise checks.
    assert enumerate_derivations(clauses, max_fact_checks=4) == expected
    with pytest.raises(DerivationLimitError, match=FACT_CHECKS_MSG):
        enumerate_derivations(clauses, max_fact_checks=3)
    r_records = [d for d in expected if d.conclusion.pred == "r"]
    assert len(r_records) == 1  # one application, not "unique" evidence


def test_join_matches_each_intermediates_and_rejects_cross_pairs():
    clauses = (fact("p", "a", "b"), fact("p", "a", "c"),
               fact("q", "b", "d"), fact("q", "c", "d"),
               rule([("p", "?x", "?y"), ("q", "?y", "?z")],
                    ("r", "?x", "?z")))
    expected = (rec(0, (), A("p", "a", "b")),
                rec(1, (), A("p", "a", "c")),
                rec(2, (), A("q", "b", "d")),
                rec(3, (), A("q", "c", "d")),
                rec(4, (A("p", "a", "b"), A("q", "b", "d")), A("r", "a", "d")),
                rec(4, (A("p", "a", "c"), A("q", "c", "d")), A("r", "a", "d")))
    # Scans: p(a,b)x{q(b,d),q(c,d)}, p(a,c)x{q(b,d),q(c,d)} -> 6 checks.
    assert enumerate_derivations(clauses, max_fact_checks=6) == expected
    with pytest.raises(DerivationLimitError, match=FACT_CHECKS_MSG):
        enumerate_derivations(clauses, max_fact_checks=5)


def test_join_failed_inner_candidate_does_not_block_next():
    clauses = (fact("p", "a", "b"), fact("p", "b", "c"),
               fact("q", "z", "d"), fact("q", "b", "d"),
               rule([("p", "?x", "?y"), ("q", "?y", "?z")],
                    ("r", "?x", "?z")))
    expected = (rec(0, (), A("p", "a", "b")),
                rec(1, (), A("p", "b", "c")),
                rec(2, (), A("q", "z", "d")),
                rec(3, (), A("q", "b", "d")),
                rec(4, (A("p", "a", "b"), A("q", "b", "d")), A("r", "a", "d")))
    # p(a,b): 1 + 2 inners; p(b,c): 1 + 2 inners -> 6 checks.
    assert enumerate_derivations(clauses, max_fact_checks=6) == expected


def test_variable_names_do_not_leak_across_clauses():
    clauses = (fact("p", "a", "b"),
               rule([("p", "?x", "?y")], ("q", "?x", "k")),
               rule([("p", "?x", "?y")], ("s", "?y", "?x")))
    expected = (rec(0, (), A("p", "a", "b")),
                rec(1, (A("p", "a", "b"),), A("q", "a", "k")),
                rec(2, (A("p", "a", "b"),), A("s", "b", "a")))
    assert enumerate_derivations(clauses, max_fact_checks=2) == expected


def test_inverse_direction_and_constant_head():
    clauses = (fact("p", "a", "b"), fact("q", "b", "c"),
               rule([("p", "?x", "?y")], ("t", "?y", "?x")),
               rule([("p", "?x", "?y"), ("q", "?y", "?z")],
                    ("w", "?x", "k")))
    expected = (rec(0, (), A("p", "a", "b")),
                rec(1, (), A("q", "b", "c")),
                rec(2, (A("p", "a", "b"),), A("t", "b", "a")),
                rec(3, (A("p", "a", "b"), A("q", "b", "c")), A("w", "a", "k")))
    # t: 1 check; w join: outer 1 + inner 1 -> 3 checks total.
    assert enumerate_derivations(clauses, max_fact_checks=3) == expected


def test_repeat_premise_empty_binding_still_records():
    clauses = (fact("p", "a", "b"), fact("q", "c", "d"),
               rule([("p", "?x", "?y"), ("q", "?u", "?v")],
                    ("r", "e", "f")))
    expected = (rec(0, (), A("p", "a", "b")),
                rec(1, (), A("q", "c", "d")),
                rec(2, (A("p", "a", "b"), A("q", "c", "d")), A("r", "e", "f")))
    assert enumerate_derivations(clauses, max_fact_checks=2) == expected
    with pytest.raises(DerivationLimitError, match=DERIVATIONS_MSG):
        enumerate_derivations(clauses, max_derivations=2)


def test_immediate_append_budget_order_two_premise():
    clauses = (fact("p", "a", "b"), fact("p", "a", "c"),
               fact("q", "b", "d"), fact("q", "c", "d"),
               rule([("p", "?x", "?y"), ("q", "?y", "?z")],
                    ("r", "?x", "?z")))
    # Four facts fill 4 derivation slots; after the first successful
    # match (checks 1 and 2) the next append must overrun the OUTPUT
    # budget before any further candidate scan.
    with pytest.raises(DerivationLimitError) as excinfo:
        enumerate_derivations(clauses, max_fact_checks=2,
                              max_derivations=4)
    assert str(excinfo.value) == DERIVATIONS_MSG
    # With only 1 check, the 2nd match attempt overruns the MATCH
    # budget first.
    with pytest.raises(DerivationLimitError) as excinfo:
        enumerate_derivations(clauses, max_fact_checks=1,
                              max_derivations=4)
    assert str(excinfo.value) == FACT_CHECKS_MSG


def test_candidate_buckets_sorted_but_facts_keep_input_order():
    clauses = (fact("p", "c", "d"), fact("p", "a", "b"),
               rule([("p", "?x", "?y")], ("q", "?x", "?y")))
    expected = (rec(0, (), A("p", "c", "d")),
                rec(1, (), A("p", "a", "b")),
                rec(2, (A("p", "a", "b"),), A("q", "a", "b")),
                rec(2, (A("p", "c", "d"),), A("q", "c", "d")))
    assert enumerate_derivations(clauses, max_fact_checks=2) == expected


def test_body_only_predicate_has_no_group_and_no_error():
    # r depends on nonexistent s; the scan handles the empty bucket.
    clauses = (fact("p", "a", "b"),
               rule([("s", "?x", "?y")], ("r", "?x", "?y")))
    expected = (rec(0, (), A("p", "a", "b")),)
    assert enumerate_derivations(clauses, max_fact_checks=1) == expected


def test_1200_node_linear_chain_purity_and_repeat():
    clauses = [fact("p0000", "a", "b")]
    for i in range(1, 1200):
        clauses.append(rule([(f"p{i-1:04d}", "?x", "?y")],
                            (f"p{i:04d}", "?x", "?y")))
    clauses = tuple(clauses)
    expected = (rec(0, (), A("p0000", "a", "b")),)
    for i in range(1, 1200):
        expected += (rec(i, (A(f"p{i-1:04d}", "a", "b"),),
                         A(f"p{i:04d}", "a", "b")),)
    assert len(expected) == 1200
    # C=1199: verify the full result at the exact boundary first.
    assert enumerate_derivations(clauses, max_fact_checks=1199) == expected
    # Purity: input objects are untouched.
    before = list(clauses)
    assert enumerate_derivations(clauses) == expected
    assert all(c == b for c, b in zip(clauses, before))
    # Repeated, failed, then later calls stay consistent.
    assert enumerate_derivations(clauses) == expected
    with pytest.raises(DerivationLimitError, match=FACT_CHECKS_MSG):
        enumerate_derivations(clauses, max_fact_checks=1198)
    with pytest.raises(LogicValidationError, match=CYCLE_MSG):
        enumerate_derivations((clauses[1],
                               rule([("p0001", "?x", "?y")],
                                    ("p0000", "?x", "?y"))))
    assert enumerate_derivations(clauses, max_fact_checks=1199) == expected


def test_cycle_variants_rejected():
    self_loop = (fact("p", "a", "b"),
                 rule([("p", "?x", "?y")], ("p", "?y", "?x")))
    two_cycle = (rule([("p", "?x", "?y")], ("q", "?x", "?y")),
                 rule([("q", "?x", "?y")], ("p", "?x", "?y")))
    # A fully disjoint, unreachable ground cycle must still be rejected.
    disconnected = (fact("s", "a", "b"),
                    rule([("s", "?x", "?y")], ("t", "?x", "?y")),
                    rule([("u", "a", "b")], ("v", "b", "a")),
                    rule([("v", "b", "a")], ("u", "a", "b")))
    for bad in (self_loop, two_cycle, disconnected):
        with pytest.raises(LogicValidationError, match=CYCLE_MSG):
            enumerate_derivations(bad)


def test_enumerate_input_container_and_members():
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations([fact("p", "a", "b")])
    assert str(excinfo.value) == (
        "enumerate.clauses must be a tuple of Clause; got list")

    gen = (fact("p", "a", "b") for _ in range(1))
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations(gen)
    assert str(excinfo.value) == (
        "enumerate.clauses must be a tuple of Clause; got generator")
    assert next(gen) == fact("p", "a", "b")  # not consumed by validation

    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations((fact("p", "a", "b"), None))
    assert str(excinfo.value) == (
        "enumerate.clauses[1] must be a Clause; got NoneType")

    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations((A("p", "a", "b"),))
    assert str(excinfo.value) == (
        "enumerate.clauses[0] must be a Clause; got Atom")


def test_enumerate_budget_validation():
    clauses = (fact("p", "a", "b"),)
    cases = ((0, "enumerate.max_fact_checks", "got int"),
             (-1, "enumerate.max_fact_checks", "got int"),
             (True, "enumerate.max_fact_checks", "got bool"),
             (1.5, "enumerate.max_fact_checks", "got float"),
             (None, "enumerate.max_fact_checks", "got NoneType"),
             (-1, "enumerate.max_derivations", "got int"),
             (None, "enumerate.max_derivations", "got NoneType"))
    for bad, field, tail in cases:
        with pytest.raises(LogicValidationError) as excinfo:
            if field.endswith("max_fact_checks"):
                enumerate_derivations(clauses, max_fact_checks=bad)
            else:
                enumerate_derivations(clauses, max_derivations=bad)
        assert str(excinfo.value) == (
            f"{field} must be a non-bool positive integer; {tail}")


def test_enumerate_error_priority():
    # Two illegal budgets -> the match budget (max_fact_checks) first.
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations((fact("p", "a", "b"),),
                              max_fact_checks=0, max_derivations=-1)
    assert "max_fact_checks" in str(excinfo.value)
    # Bad member and bad budget -> member type first.
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations((fact("p", "a", "b"), None),
                              max_fact_checks=0)
    assert "enumerate.clauses[1]" in str(excinfo.value)
    # Cyclic clauses plus bad member -> member error, not the cycle.
    cyclic = (fact("p", "a", "b"), None,
              rule([("p", "?x", "?y")], ("p", "?x", "?y")))
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations(cyclic)
    assert "enumerate.clauses[1]" in str(excinfo.value)
    # Cyclic clauses plus bad budget -> budget error, not the cycle.
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations(
            (fact("p", "a", "b"),
             rule([("p", "?x", "?y")], ("p", "?x", "?y"))),
            max_fact_checks=0)
    assert "max_fact_checks" in str(excinfo.value)


ATOM = A("p", "a", "b")


def test_ground_derivation_field_validation():
    cases = (
        ((True, (), ATOM),
         "derivation.clause_index must be a non-bool non-negative integer; "
         "got bool"),
        ((-3, (), ATOM),
         "derivation.clause_index must be a non-bool non-negative integer; "
         "got int"),
        (("0", (), ATOM),
         "derivation.clause_index must be a non-bool non-negative integer; "
         "got str"),
        ((0, (ATOM, ATOM, ATOM), ATOM),
         "derivation.premises holds at most 2 atoms; got 3"),
        ((0, (None,), ATOM),
         "derivation.premises[0] must be an Atom; got NoneType"),
        ((0, (ATOM, "x"), ATOM),
         "derivation.premises[1] must be an Atom; got str"),
        ((0, (A("t", "?x", "?y"),), ATOM),
         "derivation.premises[0] must be a ground Atom"),
        ((0, tuple(), "not an atom"),
         "derivation.conclusion must be an Atom; got str"),
        ((0, tuple(), A("t", "a", "?y")),
         "derivation.conclusion must be a ground Atom"),
    )
    for args, message in cases:
        with pytest.raises(LogicValidationError, match=re.escape(message)) as excinfo:
            GroundDerivation(*args)
        assert str(excinfo.value) == message


def test_premises_type_check_before_length_checks():
    with pytest.raises(LogicValidationError) as excinfo:
        GroundDerivation(0, [ATOM, ATOM, ATOM], ATOM)
    assert str(excinfo.value) == (
        "derivation.premises must be a tuple of Atom; got list")
    with pytest.raises(LogicValidationError) as excinfo:
        GroundDerivation(0, None, ATOM)
    assert str(excinfo.value) == (
        "derivation.premises must be a tuple of Atom; got NoneType")


def test_ground_derivation_priority():
    # Length violation is reported before inspecting members.
    with pytest.raises(LogicValidationError) as excinfo:
        GroundDerivation(0, (Atom("p", ("?x", "?y")), ATOM, None), ATOM)
    assert str(excinfo.value) == (
        "derivation.premises holds at most 2 atoms; got 3")
    # Index type wins over premises problems.
    with pytest.raises(LogicValidationError) as excinfo:
        GroundDerivation(-1, 5, ATOM)
    assert "clause_index" in str(excinfo.value)


def test_ground_derivation_structure_equality_hash_immutable():
    a = GroundDerivation(0, (), ATOM)
    b = GroundDerivation(0, (), A("p", "a", "b"))
    assert a == b and hash(a) == hash(b)
    assert a != GroundDerivation(1, (), ATOM)
    assert a != GroundDerivation(0, (), A("q", "a", "b"))
    one = GroundDerivation(0, (ATOM,), A("q", "a", "b"))
    assert one.premises == (ATOM,)
    two = GroundDerivation(0, (ATOM, ATOM), A("q", "a", "b"))
    assert two.premises == (ATOM, ATOM)
    ordered = GroundDerivation(0, (A("q", "b", "a"), ATOM), A("r", "a", "b"))
    shuffled = GroundDerivation(0, (ATOM, A("q", "b", "a")),
                                A("r", "a", "b"))
    assert ordered != shuffled  # premise order is part of equality
    for record in (a, one, two):
        for field, value in (
            ("clause_index", -1), ("premises", (A("q", "a", "b"),)),
            ("conclusion", A("q", "a", "b"))):
            with pytest.raises(FrozenInstanceError):
                setattr(record, field, value)
    assert hash(a) == hash(a)
    assert len({a, b, one, two, ordered, shuffled}) == 5  # a == b


BIG = 10 ** 5000
NEG_BIG = -10 ** 5000


@pytest.fixture()
def large_digit_limit():
    old = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    try:
        yield
    finally:
        sys.set_int_max_str_digits(old)


def test_large_ints_type_validated_not_formatted(large_digit_limit):
    with pytest.raises(LogicValidationError) as excinfo:
        GroundDerivation(NEG_BIG, (), ATOM)
    assert str(excinfo.value) == (
        "derivation.clause_index must be a non-bool non-negative integer; "
        "got int")
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations((BIG, Clause((), ATOM)))
    assert str(excinfo.value) == (
        "enumerate.clauses[0] must be a Clause; got int")
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations((Clause((), ATOM), BIG))
    assert str(excinfo.value) == (
        "enumerate.clauses[1] must be a Clause; got int")
    with pytest.raises(LogicValidationError) as excinfo:
        GroundDerivation(0, (BIG,), ATOM)
    assert str(excinfo.value) == (
        "derivation.premises[0] must be an Atom; got int")
    with pytest.raises(LogicValidationError) as excinfo:
        GroundDerivation(0, (), BIG)
    assert str(excinfo.value) == (
        "derivation.conclusion must be an Atom; got int")
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations(
            (fact("p", "a", "b"),), max_fact_checks=NEG_BIG)
    assert str(excinfo.value) == (
        "enumerate.max_fact_checks must be a non-bool positive integer; "
        "got int")
    with pytest.raises(LogicValidationError) as excinfo:
        enumerate_derivations((fact("p", "a", "b"),), max_derivations=0)
    assert str(excinfo.value) == (
        "enumerate.max_derivations must be a non-bool positive integer; "
        "got int")


def test_large_ints_legitimate_when_types_are_correct(large_digit_limit):
    record = GroundDerivation(BIG, (), ATOM)
    assert record.clause_index == BIG
    clauses = (fact("p", "a", "b"),
               rule([("p", "?x", "?y")], ("q", "?x", "?y")))
    assert enumerate_derivations(clauses, max_fact_checks=BIG,
                                 max_derivations=BIG) == (
        rec(0, (), A("p", "a", "b")),
        rec(1, (A("p", "a", "b"),), A("q", "a", "b")))


def _world(mask):
    # Fixed construction order: the four optional facts, then COPY,
    # then JOIN.
    clauses = []
    if mask & 0b00001:
        clauses.append(fact("p", "a", "b"))
    if mask & 0b00010:
        clauses.append(fact("p", "a", "c"))
    if mask & 0b00100:
        clauses.append(fact("q", "b", "d"))
    if mask & 0b01000:
        clauses.append(fact("q", "c", "d"))
    copy_index = None
    join_index = None
    if mask & 0b10000:
        copy_index = len(clauses)
        clauses.append(rule([("p", "?x", "?y")], ("s", "?x", "?y")))
    if mask & 0b100000:
        join_index = len(clauses)
        clauses.append(rule([("p", "?x", "?y"), ("q", "?y", "?z")],
                            ("r", "?x", "?z")))
    return clauses, copy_index, join_index


def _expected_world(clauses, copy_index, join_index):
    fact_records = [rec(index, (), clause.head)
                    for index, clause in enumerate(clauses)
                    if not clause.body]
    group_records = {}
    heads = {c.head for c in clauses}
    if copy_index is not None:
        group_records["s"] = [rec(copy_index, (p_atom,),
                                  A("s", *p_atom.args))
                              for p_atom in (A("p", "a", "b"),
                                             A("p", "a", "c"))
                              if p_atom in heads]
    if join_index is not None:
        pairs = ((A("p", "a", "b"), A("q", "b", "d")),
                 (A("p", "a", "c"), A("q", "c", "d")))
        group_records["r"] = [rec(join_index, premise, A("r", "a", "d"))
                              for premise in pairs
                              if all(atom in heads for atom in premise)]
    expected = []
    # Head-group order follows the accepted T0007 deterministic
    # topological order (lexicographic Kahn), e.g. r before s.
    for head in relation_topological_order(clauses):
        if head in group_records:
            expected.extend(group_records[head])
        else:
            expected.extend(record for record in fact_records
                            if record.conclusion.pred == head)
    return tuple(expected)


@pytest.mark.parametrize("mask", range(64), ids=lambda m: m)
def test_micro_worlds_match_hand_model_and_both_closures(mask):
    clauses, copy_index, join_index = _world(mask)
    clauses = tuple(clauses)
    expected = _expected_world(clauses, copy_index, join_index)
    assert enumerate_derivations(clauses) == expected
    actual_set = frozenset(
        d.conclusion for d in enumerate_derivations(clauses))
    reference = reference_closure(clauses, max_rule_evaluations=10_000)
    indexed = indexed_closure(clauses, max_fact_checks=10_000)
    assert actual_set == reference == indexed
    # The two-premise rule emits at most one record per (outer, inner)
    # candidate pair, one per binding, no Cartesian reordering.
    if join_index is not None:
        joins = [d for d in expected if d.clause_index == join_index]
        assert len(joins) <= 2


ISOLATION_SCRIPT = r'''
import sys

BLOCKED = ("torch", "yaml", "kmesh.logic.engine",
           "kmesh.logic.reference_engine", "kmesh.logic.proof")

for blocked in BLOCKED:
    assert blocked not in sys.modules, f"{blocked} preloaded"
    sys.modules[blocked] = None

from kmesh.logic.derivations import (  # noqa: E402
    DerivationLimitError,
    GroundDerivation,
    enumerate_derivations,
)
from kmesh.logic.types import Atom  # noqa: E402


def atom(pred, x, y):
    return Atom(pred, (x, y))


def clause(body, head):
    from kmesh.logic.types import Clause
    return Clause(tuple(body), head)


record = GroundDerivation(0, (atom("p", "a", "b"),), atom("q", "c", "d"))
assert record.clause_index == 0
assert record.premises == (atom("p", "a", "b"),)
assert record.conclusion == atom("q", "c", "d")

assert enumerate_derivations(()) == ()

clauses = (
    clause((), atom("r1", "a", "b")),
    clause((), atom("r2", "b", "c")),
    clause((atom("r1", "?x", "?y"), atom("r2", "?y", "?z")),
           atom("r3", "?x", "?z")),
)

expected = (
    GroundDerivation(0, (), atom("r1", "a", "b")),
    GroundDerivation(1, (), atom("r2", "b", "c")),
    GroundDerivation(2, (atom("r1", "a", "b"), atom("r2", "b", "c")),
                     atom("r3", "a", "c")),
)
assert enumerate_derivations(clauses) == expected

try:
    enumerate_derivations(clauses, max_fact_checks=1)
except DerivationLimitError as exc:
    assert "max_fact_checks" in str(exc)
else:
    raise SystemExit("expected DerivationLimitError")

for blocked in BLOCKED:
    assert sys.modules.get(blocked) is None, f"imported: {blocked}"
print("ISOLATION_OK")
'''


def test_import_isolation_in_subprocess():
    script = Path(__file__).with_name("_isolation_t0008.py")
    script.write_text(ISOLATION_SCRIPT, encoding="utf-8")
    try:
        proc = subprocess.run([sys.executable, str(script)],
                              capture_output=True, text=True, timeout=120)
    finally:
        script.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    assert "ISOLATION_OK" in proc.stdout
    assert "torch" not in proc.stderr.lower()
