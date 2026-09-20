"""Tests for ``kmesh.logic.depth.minimum_proof_depth`` (T0010, round 2).

Group A  Hand-computed semantics with the contract H-table exact C/D budgets.
Group B  Budget boundaries (H3/H4/H11/H12), cyclic worlds under legal budgets,
         duplicate clauses, limits never masquerading as ``None``.
Group C  Input validation order, exact diagnostics, big-integer safety under a
         locally capped int->str limit (4300), plain Python TypeErrors, and a
         no-call sentinel for every invalid input.
Group D  Single T0008 enumeration per call with original container identity,
         full-record processing, exception propagation and instance identity,
         pure repeat calls, and recovery after failures.
Group E  Scale: 1200-layer chain at exact C=1200/D=1201; 16 layers of
         duplicated identical COPY rules at exact C=32/D=33.
Group F  Frozen 16-world x 4-query matrix cross-checked against T0009 proof
         enumeration + T0006 verification.
Group G  Hard import isolation in a clean subprocess (find_spec blocking,
         self-checks, real depth computations, module scan).
"""

import sys
import subprocess
from pathlib import Path

import pytest

from kmesh.logic import depth as depth_module
from kmesh.logic.depth import minimum_proof_depth
from kmesh.logic.derivations import DerivationLimitError
from kmesh.logic.proof import verify_proof
from kmesh.logic.proof_enumeration import enumerate_proofs
from kmesh.logic.types import Atom, Clause, LogicValidationError

X, Y, Z = "?x", "?y", "?z"

CLE = "enumerate.max_fact_checks exhausted before enumeration completed"
DLE = "enumerate.max_derivations exhausted before enumeration completed"
DCE = "dependency.clauses: cyclic predicate dependency"


def type_name(value) -> str:
    return type(value).__name__


def atom(pred: str, x: str = "a", y: str = "b") -> Atom:
    return Atom(pred, (x, y))


def fact(pred: str, x: str = "a", y: str = "b") -> Clause:
    return Clause((), atom(pred, x, y))


def rule(*body: Atom, head: Atom) -> Clause:
    return Clause(tuple(body), head)


def run(world, query, c=100, d=100):
    return minimum_proof_depth(world, query, max_fact_checks=c, max_derivations=d)


def assert_is_int(value, expected: int):
    assert value == expected and type(value) is int


# Contract H-worlds (exact argument patterns; budgets verified in round 1).

def h3_world():
    return (fact("p"), fact("t"),
            rule(atom("p", X, Y), head=atom("u", X, Y)),
            rule(atom("u", X, Y), head=atom("v", X, Y)),
            rule(atom("t", X, Y), head=atom("w", X, Y)),
            rule(atom("v", X, Y), atom("w", X, Y), head=atom("z", X, Y)))


def h4_world():
    return (fact("p"),
            rule(atom("p", X, Y), head=atom("m", X, Y)),
            rule(atom("m", X, Y), head=atom("q", X, Y)),
            rule(atom("p", X, Y), head=atom("q", X, Y)))


def h5_world():
    return h4_world() + (rule(atom("q", X, Y), head=atom("z", X, Y)),)


def h8_world():
    return (fact("p"), fact("p", "b", "c"),
            rule(atom("p", X, Y), atom("p", Y, Z), head=atom("r", X, Z)))


def h11_world():
    return (fact("q"), fact("p"),
            rule(atom("p", X, Y), head=atom("u", X, Y)),
            rule(atom("u", X, Y), head=atom("v", X, Y)),
            rule(atom("v", X, Y), head=atom("z", X, Y)))


def h12_world():
    return (fact("a"), fact("b"), fact("c"), fact("d"),
            rule(atom("a", X, Y), head=atom("m", X, Y)),
            rule(atom("m", X, Y), head=atom("n", X, Y)),
            rule(atom("n", X, Y), head=atom("z", X, Y)),
            rule(atom("a", X, Y), atom("b", X, Y), head=atom("u", X, Y)),
            rule(atom("c", X, Y), atom("d", X, Y), head=atom("v", X, Y)),
            rule(atom("u", X, Y), atom("v", X, Y), head=atom("z", X, Y)))


def cyclic_pair():
    return (rule(atom("s", X, Y), head=atom("t", X, Y)),
            rule(atom("t", X, Y), head=atom("s", X, Y)))


def self_loop():
    return (rule(atom("s", X, Y), head=atom("s", X, Y)),)


# ---------------------------------------------------------------- Group A

def test_a0_h0_empty_world():
    assert run((), atom("q"), c=1, d=1) is None
    assert run((), atom("p"), c=1, d=1) is None

def test_a1_h1_fact_zero_absent_none():
    world = (fact("p"),)
    assert_is_int(run(world, atom("p"), c=1, d=1), 0)
    assert run(world, atom("p", "b", "a"), c=1, d=1) is None

def test_a2_h2_copy_depth_one():
    world = (fact("p"), rule(atom("p", X, Y), head=atom("q", X, Y)))
    assert_is_int(run(world, atom("q"), c=1, d=2), 1)

def test_a3_h3_join_uses_max_not_sum_or_min():
    world = h3_world()
    assert_is_int(run(world, atom("z"), c=5, d=6), 3)
    assert_is_int(run(world, atom("v"), c=5, d=6), 2)
    assert_is_int(run(world, atom("w"), c=5, d=6), 1)
    # Premise depths are 2 and 1: max+1 = 3, not sum+1 = 4 nor min+1 = 2.

def test_a3b_h4_later_shortcut_depth_one():
    world = h4_world()
    assert_is_int(run(world, atom("q"), c=3, d=4), 1)
    assert_is_int(run(world, atom("m"), c=3, d=4), 1)
    # The long path p->m->q reaches q at depth 2; the later shortcut p->q
    # keeps the minimum, so the product reports 1.
    early_shortcut = (fact("p"),
                      rule(atom("p", X, Y), head=atom("q", X, Y)),
                      rule(atom("p", X, Y), head=atom("m", X, Y)),
                      rule(atom("m", X, Y), head=atom("q", X, Y)))
    assert_is_int(run(early_shortcut, atom("q"), c=3, d=4), 1)

def test_a3c_long_path_alone_stays_deep():
    long_only = (fact("p"),
                 rule(atom("p", X, Y), head=atom("m", X, Y)),
                 rule(atom("m", X, Y), head=atom("q", X, Y)))
    assert_is_int(run(long_only, atom("q"), c=2, d=3), 2)

def test_a4_h5_shortcut_affects_downstream():
    assert_is_int(run(h5_world(), atom("z"), c=4, d=5), 2)

def test_a5_h6_fact_keeps_zero_regardless_of_position():
    rule_first = (fact("p"), rule(atom("p", X, Y), head=atom("q", X, Y)),
                  fact("q"))
    fact_first = (fact("p"), fact("q"),
                  rule(atom("p", X, Y), head=atom("q", X, Y)))
    for world in (rule_first, fact_first):
        assert_is_int(run(world, atom("q"), c=1, d=3), 0)

def test_a6_h7_repeated_premise_slot_counts_once():
    world = (fact("p"),
             rule(atom("p", X, Y), atom("p", X, Y), head=atom("q", X, Y)))
    assert_is_int(run(world, atom("q"), c=2, d=2), 1)

def test_a7_h8_join_argument_sensitivity():
    world = h8_world()
    assert_is_int(run(world, atom("r", "a", "c"), c=6, d=3), 1)
    assert run(world, atom("r", "c", "a"), c=6, d=3) is None

def test_a8_h9_ground_arguments_distinguish_queries():
    world = (fact("q"), fact("p", "c", "d"),
             rule(atom("p", X, Y), head=atom("q", X, Y)))
    assert_is_int(run(world, atom("q"), c=1, d=3), 0)
    assert_is_int(run(world, atom("q", "c", "d"), c=1, d=3), 1)

def test_a9_h10_rule_only_without_fact():
    assert run((rule(atom("p", X, Y), head=atom("q", X, Y)),),
               atom("q"), c=1, d=1) is None

def test_a10_h11_full_world_budget_without_early_exit():
    world = h11_world()
    assert_is_int(run(world, atom("q"), c=3, d=5), 0)
    assert run(world, atom("missing"), c=3, d=5) is None

def test_a11_h12_short_tree_beats_long_chain():
    world = h12_world()
    assert_is_int(run(world, atom("z"), c=9, d=10), 2)
    assert_is_int(run(world, atom("n"), c=9, d=10), 2)
    assert_is_int(run(world, atom("u"), c=9, d=10), 1)
    # Length-4 chain a->m->n->z gives depth 3 at z; the (u,v) tree gives 2.

# ---------------------------------------------------------------- Group B

@pytest.mark.parametrize("bad", [0, -1, True, False, "3", 3.0, None])
def test_b1_budget_validation(bad):
    for name in ("max_fact_checks", "max_derivations"):
        with pytest.raises(LogicValidationError) as exc:
            minimum_proof_depth((fact("p"),), atom("p"), **{name: bad})
        assert str(exc.value) == (
            f"depth.{name} must be a non-bool positive integer; "
            f"got {type_name(bad)}")

def test_b1b_default_budgets():
    assert run((fact("p"),), atom("p")) == 0
    assert run((fact("p"),), atom("missing")) is None

def test_b2_h3_exact_budget_boundaries():
    world = h3_world()
    assert_is_int(run(world, atom("z"), c=5, d=6), 3)
    with pytest.raises(DerivationLimitError) as e_c:
        run(world, atom("z"), c=4, d=6)
    assert str(e_c.value) == CLE
    with pytest.raises(DerivationLimitError) as e_d:
        run(world, atom("z"), c=5, d=5)
    assert str(e_d.value) == DLE

def test_b2b_h4_exact_budget_boundaries():
    world = h4_world()
    assert_is_int(run(world, atom("q"), c=3, d=4), 1)
    with pytest.raises(DerivationLimitError) as e_c:
        run(world, atom("q"), c=2, d=4)
    assert str(e_c.value) == CLE
    with pytest.raises(DerivationLimitError) as e_d:
        run(world, atom("q"), c=3, d=3)
    assert str(e_d.value) == DLE

def test_b2c_h11_exact_budget_boundaries_both_queries():
    world = h11_world()
    for query in (atom("q"), atom("missing")):
        if query.pred == "q":
            assert_is_int(run(world, query, c=3, d=5), 0)
        else:
            assert run(world, query, c=3, d=5) is None
        with pytest.raises(DerivationLimitError) as e_c:
            run(world, query, c=2, d=5)
        assert str(e_c.value) == CLE
        with pytest.raises(DerivationLimitError) as e_d:
            run(world, query, c=3, d=4)
        assert str(e_d.value) == DLE

def test_b2d_h12_exact_budget_boundaries():
    world = h12_world()
    assert_is_int(run(world, atom("z"), c=9, d=10), 2)
    with pytest.raises(DerivationLimitError) as e_c:
        run(world, atom("z"), c=8, d=10)
    assert str(e_c.value) == CLE
    with pytest.raises(DerivationLimitError) as e_d:
        run(world, atom("z"), c=9, d=9)
    assert str(e_d.value) == DLE

def test_b3_cyclic_worlds_under_legal_budget():
    # Fact query with an unrelated predicate self-loop.
    with pytest.raises(LogicValidationError) as e1:
        run((fact("q"), self_loop()[0]), atom("q"), c=100, d=100)
    assert str(e1.value) == DCE
    # Missing query with an unrelated self-loop.
    with pytest.raises(LogicValidationError) as e2:
        run((fact("p"), self_loop()[0]), atom("missing"), c=100, d=100)
    assert str(e2.value) == DCE
    # Cycle with no facts at all.
    with pytest.raises(LogicValidationError) as e3:
        run(cyclic_pair(), atom("s"), c=100, d=100)
    assert str(e3.value) == DCE

def test_b3b_limits_never_none_and_budget_precedes_cycle():
    world = h3_world()
    with pytest.raises(DerivationLimitError) as e1:
        run(world, atom("z"), c=4, d=6)
    assert str(e1.value) == CLE
    with pytest.raises(DerivationLimitError) as e2:
        run(world, atom("z"), c=5, d=5)
    assert str(e2.value) == DLE
    with pytest.raises(LogicValidationError) as e3:
        run(world, atom("z"), c=0, d=100)
    assert str(e3.value) == (
        "depth.max_fact_checks must be a non-bool positive integer; got int")
    with pytest.raises(LogicValidationError) as e4:
        run(world, atom("z"), c=100, d=0)
    assert str(e4.value) == (
        "depth.max_derivations must be a non-bool positive integer; got int")

def test_b5_duplicate_fact_and_rule_do_not_change_depth():
    world = h5_world()
    base = run(world, atom("z"), c=100, d=100)
    assert_is_int(base, 2)
    dup = world + (fact("p"),) + (
        rule(atom("p", X, Y), head=atom("m", X, Y)),)
    assert_is_int(run(dup, atom("z"), c=100, d=100), base)

# ---------------------------------------------------------------- Group C

def test_c1_container_type_and_generator_not_consumed():
    for bad in ([fact("p")], {fact("p")}, "p", 3):
        with pytest.raises(LogicValidationError) as exc:
            run(bad, atom("p"))
        assert str(exc.value) == (
            f"depth.clauses must be a tuple of Clause; got {type_name(bad)}")
    gen = (clause for clause in (fact("p"), fact("q")))
    with pytest.raises(LogicValidationError) as exc:
        run(gen, atom("p"))
    assert str(exc.value) == (
        "depth.clauses must be a tuple of Clause; got generator")
    assert next(gen) == fact("p")
    assert next(gen) == fact("q")

def test_c2_first_bad_member_position():
    bad = (fact("p"), "not-a-clause", fact("q"), 0)
    with pytest.raises(LogicValidationError) as exc:
        run(bad, atom("p"))
    assert str(exc.value) == "depth.clauses[1] must be a Clause; got str"
    with pytest.raises(LogicValidationError) as exc2:
        run((fact("p"), fact("q"), None), atom("p"))
    assert str(exc2.value) == (
        "depth.clauses[2] must be a Clause; got NoneType")

def test_c3_query_type_and_groundness():
    world = (fact("p"),)
    for bad in ("p", 3, None, fact("p")):
        with pytest.raises(LogicValidationError) as exc:
            run(world, bad)
        assert str(exc.value) == (
            f"depth.query must be an Atom; got {type_name(bad)}")
    with pytest.raises(LogicValidationError) as exc:
        run(world, atom("p", "?x", "?y"))
    assert str(exc.value) == "depth.query must be a ground Atom"

def test_c4_validation_priority(monkeypatch):
    calls = []
    def spy(clauses, *, max_fact_checks, max_derivations):
        calls.append(True)
        raise RuntimeError("spy")
    monkeypatch.setattr(depth_module, "enumerate_derivations", spy)
    cyclic = cyclic_pair()
    # Query type beats a cyclic world.
    with pytest.raises(LogicValidationError) as e1:
        run(cyclic, "not-an-atom")
    assert str(e1.value) == "depth.query must be an Atom; got str"
    # Bad member beats a non-ground query.
    with pytest.raises(LogicValidationError) as e2:
        run((fact("p"), 42), atom("p", "?x", "?y"))
    assert str(e2.value) == "depth.clauses[1] must be a Clause; got int"
    # Non-ground query beats a cyclic world.
    with pytest.raises(LogicValidationError) as e3:
        run(cyclic, atom("p", "?x", "?y"))
    assert str(e3.value) == "depth.query must be a ground Atom"
    # Container type beats a bad budget.
    with pytest.raises(LogicValidationError) as e4:
        run([fact("p")], atom("p"), c=True)
    assert str(e4.value) == "depth.clauses must be a tuple of Clause; got list"
    # Bad max_derivations beats a cyclic world.
    with pytest.raises(LogicValidationError) as e5:
        run(cyclic, atom("q"), d=-1)
    assert str(e5.value) == (
        "depth.max_derivations must be a non-bool positive integer; got int")
    # Non-ground query beats both invalid budgets (overlap).
    with pytest.raises(LogicValidationError) as e6:
        run((fact("p"),), atom("p", "?x", "?y"), c=0, d=-1)
    assert str(e6.value) == "depth.query must be a ground Atom"
    # With both budgets invalid, max_fact_checks is checked before max_derivations.
    with pytest.raises(LogicValidationError) as e7:
        run((fact("p"),), atom("p"), c=0, d=-1)
    assert str(e7.value) == (
        "depth.max_fact_checks must be a non-bool positive integer; got int")
    assert calls == []

@pytest.fixture
def capped_int_str_limit():
    previous = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    try:
        yield 4300
    finally:
        sys.set_int_max_str_digits(0 if previous is None else previous)


@pytest.mark.parametrize("field", [
    "clauses", "member", "query",
    "max_fact_checks", "max_derivations", "both_positive",
])
def test_large_integer_diagnostics(field, capped_int_str_limit):
    big = 10 ** 5000
    world = (fact("p"),)
    if field == "clauses":
        with pytest.raises(LogicValidationError) as exc:
            run(big, atom("p"))
        assert str(exc.value) == (
            "depth.clauses must be a tuple of Clause; got int")
    elif field == "member":
        with pytest.raises(LogicValidationError) as exc:
            run(world + (big,), atom("p"))
        assert str(exc.value) == "depth.clauses[1] must be a Clause; got int"
    elif field == "query":
        with pytest.raises(LogicValidationError) as exc:
            run(world, big)
        assert str(exc.value) == "depth.query must be an Atom; got int"
    elif field == "max_fact_checks":
        with pytest.raises(LogicValidationError) as exc:
            run(world, atom("p"), c=-big)
        assert str(exc.value) == (
            "depth.max_fact_checks must be a non-bool positive integer; "
            "got int")
    elif field == "max_derivations":
        with pytest.raises(LogicValidationError) as exc:
            run(world, atom("p"), d=-big)
        assert str(exc.value) == (
            "depth.max_derivations must be a non-bool positive integer; "
            "got int")
    else:  # both_positive: legal giant budgets keep working.
        h2 = (fact("p"), rule(atom("p", X, Y), head=atom("q", X, Y)))
        assert_is_int(run(h2, atom("q"), c=big, d=big), 1)

def test_c6_plain_type_errors_for_argument_mistakes():
    with pytest.raises(TypeError):
        minimum_proof_depth((fact("p"),))
    with pytest.raises(TypeError):
        minimum_proof_depth((fact("p"),), atom("p"), unexpected=1)
    with pytest.raises(TypeError):
        minimum_proof_depth((fact("p"),), atom("p"), 7, 9)

def test_invalid_inputs_do_not_call_enumerator(monkeypatch):
    calls = []
    def spy(clauses, *, max_fact_checks, max_derivations):
        calls.append((clauses, max_fact_checks, max_derivations))
        raise RuntimeError("spy")
    monkeypatch.setattr(depth_module, "enumerate_derivations", spy)
    good = (fact("p"),)
    cyclic = (fact("p"), self_loop()[0])
    cases = (
        ([fact("p")], atom("p"), {},
         "depth.clauses must be a tuple of Clause; got list"),
        (None, atom("p"), {},
         "depth.clauses must be a tuple of Clause; got NoneType"),
        ("p", atom("p"), {},
         "depth.clauses must be a tuple of Clause; got str"),
        (3, atom("p"), {},
         "depth.clauses must be a tuple of Clause; got int"),
        (iter([fact("p")]), atom("p"), {},
         "depth.clauses must be a tuple of Clause; got list_iterator"),
        (good, "p", {}, "depth.query must be an Atom; got str"),
        (good, 3, {}, "depth.query must be an Atom; got int"),
        (good, None, {}, "depth.query must be an Atom; got NoneType"),
        (good, fact("p"), {}, "depth.query must be an Atom; got Clause"),
        (good, atom("p", "?x", "?y"), {},
         "depth.query must be a ground Atom"),
        (good, atom("p"), {"max_fact_checks": True},
         "depth.max_fact_checks must be a non-bool positive integer; "
         "got bool"),
        (good, atom("p"), {"max_fact_checks": 0},
         "depth.max_fact_checks must be a non-bool positive integer; "
         "got int"),
        (good, atom("p"), {"max_fact_checks": -1},
         "depth.max_fact_checks must be a non-bool positive integer; "
         "got int"),
        (good, atom("p"), {"max_fact_checks": "3"},
         "depth.max_fact_checks must be a non-bool positive integer; "
         "got str"),
        (good, atom("p"), {"max_fact_checks": 3.0},
         "depth.max_fact_checks must be a non-bool positive integer; "
         "got float"),
        (good, atom("p"), {"max_fact_checks": None},
         "depth.max_fact_checks must be a non-bool positive integer; "
         "got NoneType"),
        (good, atom("p"), {"max_derivations": True},
         "depth.max_derivations must be a non-bool positive integer; "
         "got bool"),
        (good, atom("p"), {"max_derivations": 0},
         "depth.max_derivations must be a non-bool positive integer; "
         "got int"),
        (good, atom("p"), {"max_derivations": -5},
         "depth.max_derivations must be a non-bool positive integer; "
         "got int"),
        (good, atom("p"), {"max_derivations": "9"},
         "depth.max_derivations must be a non-bool positive integer; "
         "got str"),
        (good, atom("p"), {"max_derivations": 9.0},
         "depth.max_derivations must be a non-bool positive integer; "
         "got float"),
        (good, atom("p"), {"max_derivations": None},
         "depth.max_derivations must be a non-bool positive integer; "
         "got NoneType"),
        (cyclic, atom("q"), {"max_derivations": -1},
         "depth.max_derivations must be a non-bool positive integer; "
         "got int"),
    )
    for clauses, query, kwargs, message in cases:
        with pytest.raises(LogicValidationError) as exc:
            minimum_proof_depth(clauses, query, **kwargs)
        assert str(exc.value) == message
    assert calls == []

# ---------------------------------------------------------------- Group D

def test_d1_single_enumeration_and_original_identity(monkeypatch):
    original = depth_module.enumerate_derivations
    calls = []
    def spy(clauses, *, max_fact_checks, max_derivations):
        calls.append((clauses, max_fact_checks, max_derivations))
        return original(clauses, max_fact_checks=max_fact_checks,
                        max_derivations=max_derivations)
    monkeypatch.setattr(depth_module, "enumerate_derivations", spy)
    fact_world = (fact("q"),)
    absent_world = (fact("p"),)
    chain = (fact("p"), rule(atom("p", X, Y), head=atom("q", X, Y)))
    assert_is_int(
        minimum_proof_depth(fact_world, atom("q"),
                            max_fact_checks=1, max_derivations=1), 0)
    assert minimum_proof_depth(
        absent_world, atom("n"),
        max_fact_checks=1, max_derivations=1) is None
    assert_is_int(
        minimum_proof_depth(chain, atom("q"),
                            max_fact_checks=2, max_derivations=2), 1)
    assert len(calls) == 3
    assert calls[0][0] is fact_world
    assert calls[1][0] is absent_world
    assert calls[2][0] is chain
    assert calls[0][1:] == (1, 1)
    assert calls[1][1:] == (1, 1)
    assert calls[2][1:] == (2, 2)

def test_d1b_fact_query_does_not_skip_enumeration(monkeypatch):
    original = depth_module.enumerate_derivations
    seen = []
    def spy(clauses, *, max_fact_checks, max_derivations):
        records = original(clauses, max_fact_checks=max_fact_checks,
                           max_derivations=max_derivations)
        seen.append(len(records))
        return records
    monkeypatch.setattr(depth_module, "enumerate_derivations", spy)
    chain = (fact("p"), rule(atom("p", X, Y), head=atom("q", X, Y)))
    got = run(chain, atom("p"), c=5, d=5)
    assert got == 0 and type(got) is int
    # Both records (fact p, derived q) were enumerated for the fact query.
    assert seen == [2]

def test_d2_exceptions_propagate_unchanged():
    with pytest.raises(LogicValidationError) as e1:
        run(self_loop(), atom("q"), c=3, d=3)
    assert str(e1.value) == DCE
    with pytest.raises(DerivationLimitError) as e2:
        run(h3_world(), atom("z"), c=100, d=3)
    assert str(e2.value) == DLE
    with pytest.raises(LogicValidationError) as e3:
        run(h3_world(), atom("z"), c=True, d=100)
    assert str(e3.value) == (
        "depth.max_fact_checks must be a non-bool positive integer; got bool")

def test_d2b_exception_instance_identity(monkeypatch):
    cycle_error = LogicValidationError(DCE)
    limit_error = DerivationLimitError(DLE)
    errors = (cycle_error, limit_error)
    iterator = iter(errors)
    def spy(clauses, *, max_fact_checks, max_derivations):
        raise next(iterator)
    monkeypatch.setattr(depth_module, "enumerate_derivations", spy)
    with pytest.raises(LogicValidationError) as e1:
        run(cyclic_pair(), atom("q"))
    assert e1.value is cycle_error
    assert str(e1.value) == DCE
    with pytest.raises(DerivationLimitError) as e2:
        run(h3_world(), atom("z"), d=3)
    assert e2.value is limit_error
    assert str(e2.value) == DLE

def test_d3_repeat_calls_and_input_purity():
    world = h5_world()
    before = tuple(world)
    before_hash = hash(world)
    g1 = run(world, atom("z"), c=4, d=5)
    g2 = run(world, atom("z"), c=4, d=5)
    assert g1 == g2 == 2
    assert type(g1) is int and type(g2) is int
    assert world == before
    assert hash(world) == before_hash
    assert all(type(c) is Clause for c in world)

def test_d4_recovery_after_failures():
    world = h3_world()
    with pytest.raises(DerivationLimitError) as e1:
        run(world, atom("z"), c=4, d=6)
    assert str(e1.value) == CLE
    with pytest.raises(LogicValidationError) as e2:
        run([fact("p")], atom("p"))
    assert str(e2.value) == "depth.clauses must be a tuple of Clause; got list"
    assert_is_int(run(world, atom("z"), c=5, d=6), 3)

# ---------------------------------------------------------------- Group E

def test_e1_long_chain_1200_exact_budget():
    length = 1200
    clauses = [fact("c0")]
    for i in range(length):
        clauses.append(rule(atom(f"c{i}"), head=atom(f"c{i + 1}")))
    world = tuple(clauses)
    assert_is_int(run(world, atom("c1200"), c=1200, d=1201), 1200)
    assert_is_int(run(world, atom("c599"), c=1200, d=1201), 599)
    assert run(world, atom("d0"), c=1200, d=1201) is None
    with pytest.raises(DerivationLimitError) as e_c:
        run(world, atom("c1200"), c=1199, d=1201)
    assert str(e_c.value) == CLE
    with pytest.raises(DerivationLimitError) as e_d:
        run(world, atom("c1200"), c=1200, d=1200)
    assert str(e_d.value) == DLE

def test_e2_deep_duplicate_sources_16_layers_exact_budget():
    clauses = [fact("l0")]
    for i in range(16):
        copy = rule(atom(f"l{i}"), head=atom(f"l{i + 1}"))
        clauses.append(copy)
        clauses.append(copy)  # identical duplicate rule, same predicate slot
    world = tuple(clauses)
    assert len(world) == 33  # 1 fact + 32 rule records
    assert_is_int(run(world, atom("l16"), c=32, d=33), 16)
    assert_is_int(run(world, atom("l8"), c=32, d=33), 8)
    assert_is_int(run(world, atom("l0"), c=32, d=33), 0)
    with pytest.raises(DerivationLimitError) as e_c:
        run(world, atom("l16"), c=31, d=33)
    assert str(e_c.value) == CLE
    with pytest.raises(DerivationLimitError) as e_d:
        run(world, atom("l16"), c=32, d=32)
    assert str(e_d.value) == DLE

# ---------------------------------------------------------------- Group F

BASE = (fact("p"), fact("q", "b", "c"),
        rule(atom("p", "?x", "?y"), atom("q", "?y", "?z"),
             head=atom("r", "?x", "?z")))
QUERIES = (atom("r", "a", "c"), atom("r", "a", "b"),
           atom("t", "c", "a"), atom("t", "a", "a"))


def world_for_mask(mask: int) -> tuple[Clause, ...]:
    clauses = list(BASE)
    if mask & 1:
        clauses.append(fact("p"))
    if mask & 2:
        clauses.append(fact("r", "a", "c"))
    if mask & 4:
        clauses.append(rule(atom("p", "?x", "?y"),
                            head=atom("s", "?x", "?y")))
        clauses.append(rule(atom("s", "?x", "?y"),
                            head=atom("r", "?x", "?y")))
    if mask & 8:
        clauses.append(rule(atom("r", "?x", "?y"),
                            head=atom("t", "?y", "?x")))
    return tuple(clauses)


def test_f_frozen_matrix_against_proofs_and_verifier():
    compared = 0
    for mask in range(16):
        world = world_for_mask(mask)
        for query in QUERIES:
            mine = run(world, query, c=1000, d=100)
            proofs = enumerate_proofs(
                world, query,
                max_fact_checks=1000, max_derivations=100,
                max_proof_steps=100_000)
            for proof in proofs:
                assert verify_proof(world, query, proof)
            if proofs:
                heights = []
                for proof in proofs:
                    proof_heights = []
                    for step in proof:
                        proof_heights.append(
                            0 if not step.premise_steps else
                            1 + max(proof_heights[i]
                                    for i in step.premise_steps))
                    heights.append(proof_heights[-1])
                assert mine == min(heights), (mask, query, mine, heights)
            else:
                assert mine is None, (mask, query, mine)
            compared += 1
    assert compared == 64


def test_f_sanity_anchors():
    assert run(world_for_mask(0), atom("r", "a", "c")) == 1
    assert run(world_for_mask(0), atom("t", "c", "a")) is None
    assert run(world_for_mask(2), atom("r", "a", "c")) == 0
    assert run(world_for_mask(0x0C), atom("t", "c", "a")) == 2
    assert run(world_for_mask(0x0C), atom("t", "a", "a")) is None

# Transformation helpers (Group B contract: semantics preserved under
# clause reordering, twin-premise swapping, entity/predicate bijections and
# per-rule variable renaming; queries renamed in lockstep).

def _map_atom(value, arg_map, pred_map):
    return Atom(pred_map.get(value.pred, value.pred),
                tuple(arg_map.get(arg, arg) for arg in value.args))


def _rename_entities(world, query, entity_map):
    clauses = tuple(
        Clause(tuple(_map_atom(p, entity_map, {}) for p in c.body),
               _map_atom(c.head, entity_map, {}))
        for c in world)
    return clauses, _map_atom(query, entity_map, {})


def _rename_predicates(world, query, pred_map):
    clauses = tuple(
        Clause(tuple(_map_atom(p, {}, pred_map) for p in c.body),
               _map_atom(c.head, {}, pred_map))
        for c in world)
    return clauses, _map_atom(query, {}, pred_map)


def _rename_rule_vars(world):
    out = []
    for index, clause in enumerate(world):
        var_map = {}
        body = []
        for prem in clause.body:
            args = []
            for v in prem.args:
                if v.startswith("?") and v not in var_map:
                    var_map[v] = f"?v{index}_{v[1:]}"
                args.append(var_map.get(v, v))
            body.append(Atom(prem.pred, tuple(args)))
        head_args = tuple(var_map.get(v, v) for v in clause.head.args)
        out.append(Clause(tuple(body), Atom(clause.head.pred, head_args)))
    return tuple(out)


def _swap_twin_premises(world):
    out = []
    for clause in world:
        if len(clause.body) == 2:
            out.append(Clause((clause.body[1], clause.body[0]), clause.head))
        else:
            out.append(clause)
    return tuple(out)

def test_depth_invariant_under_transformations():
    entity_map = {"a": "E1", "b": "E2", "c": "E3", "d": "E4"}
    pred_map = {p: f"P_{p}" for p in
                ("p", "q", "z", "r", "m", "a", "b", "c", "d", "n", "u", "v")}

    def checks(world, query, expected):
        def apply(name):
            if name == "reversed":
                w, q = world[::-1], query
            elif name == "twin_swap":
                w, q = _swap_twin_premises(world), query
            elif name == "entities":
                w, q = _rename_entities(world, query, entity_map)
            elif name == "predicates":
                w, q = _rename_predicates(world, query, pred_map)
            elif name == "rule_vars":
                w, q = _rename_rule_vars(world), query
            got = run(w, q, c=100, d=100)
            if expected is None:
                assert got is None, (name, got)
            else:
                assert_is_int(got, expected)
            return w, q

        for name in ("reversed", "twin_swap", "entities", "predicates",
                     "rule_vars"):
            apply(name)

    checks(h5_world(), atom("z"), 2)
    h8 = h8_world()
    swapped_h8 = _swap_twin_premises(h8)
    assert swapped_h8[-1].body == (h8[-1].body[1], h8[-1].body[0])
    assert swapped_h8[-1].body != h8[-1].body
    checks(h8, atom("r", "a", "c"), 1)
    checks(h8_world(), atom("r", "c", "a"), None)
    checks(h12_world(), atom("z"), 2)

# ---------------------------------------------------------------- Group G

def test_g_depth_import_pulls_no_forbidden_modules():
    code = (
        "import importlib\n"
        "import sys\n"
        "\n"
        "FORBIDDEN = ('torch', 'yaml', 'kmesh.logic.engine',\n"
        "             'kmesh.logic.reference_engine', 'kmesh.logic.proof',\n"
        "             'kmesh.logic.proof_enumeration')\n"
        "\n"
        "class BlockFinder:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if any(name == r or name.startswith(r + '.')\n"
        "               for r in FORBIDDEN):\n"
        "            raise ImportError('blocked import: ' + name)\n"
        "        return None\n"
        "\n"
        "sys.meta_path.insert(0, BlockFinder())\n"
        "for root in FORBIDDEN:\n"
        "    for name in (root, root + '.submodule'):\n"
        "        try:\n"
        "            importlib.import_module(name)\n"
        "        except ImportError:\n"
        "            pass\n"
        "        else:\n"
        "            raise SystemExit('self-check failed: ' + name)\n"
        "\n"
        "from kmesh.logic.depth import minimum_proof_depth\n"
        "from kmesh.logic.types import Atom, Clause\n"
        "\n"
        "def atom(pred, x, y):\n"
        "    return Atom(pred, (x, y))\n"
        "\n"
        "def fact(pred, x='a', y='b'):\n"
        "    return Clause((), atom(pred, x, y))\n"
        "\n"
        "def rule(body, head):\n"
        "    return Clause(tuple(body), head)\n"
        "\n"
        "def depth(clauses, query):\n"
        "    return minimum_proof_depth(clauses, query,\n"
        "                               max_fact_checks=100,\n"
        "                               max_derivations=100)\n"
        "\n"
        "got = depth((fact('p'),), atom('p', 'a', 'b'))\n"
        "assert got == 0 and type(got) is int, got\n"
        "\n"
        "copy = rule((atom('p', '?x', '?y'),), atom('c', '?x', '?y'))\n"
        "got = depth((fact('p'), copy), atom('c', 'a', 'b'))\n"
        "assert got == 1 and type(got) is int, got\n"
        "\n"
        "join = rule((atom('s', '?x', '?y'), atom('s', '?y', '?z')),\n"
        "            atom('t', '?x', '?z'))\n"
        "got = depth((fact('s'), fact('s', 'b', 'c'), join),\n"
        "            atom('t', 'a', 'c'))\n"
        "assert got == 1 and type(got) is int, got\n"
        "\n"
        "try:\n"
        "    minimum_proof_depth('s', atom('p', 'a', 'b'))\n"
        "except ValueError as exc:\n"
        "    message = str(exc)\n"
        "    assert message == ('depth.clauses must be a tuple of Clause; '\n"
        "                       'got str'), message\n"
        "else:\n"
        "    raise SystemExit('invalid call did not raise')\n"
        "\n"
        "loaded = sorted(name for name in sys.modules\n"
        "                if any(name == r or name.startswith(r + '.')\n"
        "                       for r in FORBIDDEN))\n"
        "assert not loaded, loaded\n"
        "print('ISOLATION-PASS')\n"
    )
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        capture_output=True, text=True, timeout=120,
        env={"PATH": "/usr/bin:/bin",
             "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
             "PYTHONPATH": "src"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "ISOLATION-PASS" in proc.stdout
