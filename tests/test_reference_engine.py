"""Tests for the naive reference closure solver (T0004).

Every expected closure is hand-computed for a small synthetic world; no
second solver and no test helper may be used to generate expected
answers. Budget accounting is validated against the exact per-candidate
check definition in the handoff and D19.
"""

import subprocess
import sys
import textwrap

import pytest

from kmesh.logic.reference_engine import ReferenceLimitError
from kmesh.logic.reference_engine import reference_closure
from kmesh.logic.types import Atom, Clause, LogicValidationError


def _fact(pred, args):
    return Clause((), Atom(pred, args))


def _rule(body, head):
    return Clause(tuple(body), head)


def _copy_rule(source, target):
    return _rule((Atom(source, ("?x", "?y")),),
                 Atom(target, ("?x", "?y")))


@pytest.fixture
def pinned_int_str_limit():
    """Force the platform int-to-str limit so oversized ints stay slow."""
    saved = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
    except (ValueError, RuntimeError) as exc:
        pytest.fail(f"could not pin int max str digits: {exc!r}")
    try:
        yield
    finally:
        sys.set_int_max_str_digits(saved)


def _main_world():
    return (
        _fact("r1", ("a", "b")),
        _fact("r2", ("b", "c")),
        _rule((Atom("r1", ("?x", "?y")), Atom("r2", ("?y", "?z"))),
              Atom("r3", ("?x", "?z"))),
        _rule((Atom("r3", ("?x", "?y")),), Atom("r4", ("?y", "?x"))),
    )


def _main_expected():
    return frozenset({
        Atom("r1", ("a", "b")), Atom("r2", ("b", "c")),
        Atom("r3", ("a", "c")), Atom("r4", ("c", "a")),
    })


# ---------------------------------------------------------------------------
# 1. Hand-processed main example (same meaning as research plan section 4.2)
# ---------------------------------------------------------------------------

def test_main_example_full_closure():
    assert reference_closure(_main_world()) == _main_expected()


def test_main_example_head_argument_order_changes_result():
    world = _main_world()[:3] + (
        _rule((Atom("r3", ("?x", "?y")),), Atom("r4", ("?x", "?y"))),
    )
    expected = (_main_expected()
                - frozenset({Atom("r4", ("c", "a"))})
                | frozenset({Atom("r4", ("a", "c"))}))
    assert reference_closure(world) == expected


def test_main_example_missing_premise_fact_blocks_derivation():
    world = (_main_world()[0], _main_world()[2], _main_world()[3])
    assert reference_closure(world) == frozenset({Atom("r1", ("a", "b"))})


# ---------------------------------------------------------------------------
# 2. Empty world and fact-only inputs
# ---------------------------------------------------------------------------

def test_empty_world_returns_empty_frozenset():
    result = reference_closure(())
    assert type(result) is frozenset
    assert result == frozenset()


def test_duplicate_facts_deduplicate_without_reordering():
    fact = _fact("p", ("a", "b"))
    result = reference_closure((fact, fact))
    assert result == frozenset({Atom("p", ("a", "b"))})
    assert Atom("p", ("b", "a")) not in result


# ---------------------------------------------------------------------------
# 3. COPY / INV / INTER on the same three facts
# ---------------------------------------------------------------------------

def _copy_inv_inter_facts():
    return frozenset({
        _fact("p", ("a", "b")).head,
        _fact("q", ("a", "b")).head,
        _fact("q", ("b", "a")).head,
    })


def test_copy_rule_derives_same_pair():
    facts = (_fact("p", ("a", "b")), _fact("q", ("a", "b")),
             _fact("q", ("b", "a")))
    world = facts + (_copy_rule("p", "c"),)
    assert reference_closure(world) == _copy_inv_inter_facts() | \
        frozenset({Atom("c", ("a", "b"))})


def test_inv_rule_derives_swapped_pair_only():
    facts = (_fact("p", ("a", "b")), _fact("q", ("a", "b")),
             _fact("q", ("b", "a")))
    world = facts + (_rule((Atom("p", ("?x", "?y")),),
                           Atom("inv", ("?y", "?x"))),)
    result = reference_closure(world)
    assert result == _copy_inv_inter_facts() | \
        frozenset({Atom("inv", ("b", "a"))})
    assert Atom("inv", ("a", "b")) not in result


def test_inter_rule_accepts_same_pair_same_binding_only():
    facts = (_fact("p", ("a", "b")), _fact("q", ("a", "b")),
             _fact("q", ("b", "a")))
    world = facts + (_rule((Atom("p", ("?x", "?y")),
                            Atom("q", ("?x", "?y"))),
                           Atom("inter", ("?x", "?y"))),)
    result = reference_closure(world)
    assert result == _copy_inv_inter_facts() | \
        frozenset({Atom("inter", ("a", "b"))})
    assert Atom("inter", ("b", "a")) not in result
    assert Atom("inter", ("a", "a")) not in result


# ---------------------------------------------------------------------------
# 4. Repeated variables share one value inside a rule
# ---------------------------------------------------------------------------

def test_repeated_variable_only_matches_equal_pairs():
    world = (
        _fact("p", ("a", "a")),
        _fact("p", ("a", "b")),
        _rule((Atom("p", ("?x", "?x")),), Atom("same", ("?x", "?x"))),
    )
    assert reference_closure(world) == frozenset({
        Atom("p", ("a", "a")), Atom("p", ("a", "b")),
        Atom("same", ("a", "a")),
    })


# ---------------------------------------------------------------------------
# 5. Constants not present in any fact enter the domain via rules
# ---------------------------------------------------------------------------

def test_head_only_constant_enters_domain_and_closures():
    world = (
        _fact("seed", ("a", "a")),
        _rule((Atom("seed", ("?x", "?x")),), Atom("tag", ("?x", "k"))),
        _rule((Atom("tag", ("?x", "?y")),), Atom("out", ("?y", "?x"))),
    )
    assert reference_closure(world) == frozenset({
        Atom("seed", ("a", "a")),
        Atom("tag", ("a", "k")),
        Atom("out", ("k", "a")),
    })


# ---------------------------------------------------------------------------
# 6. Disconnected variables are bound independently (cartesian enumeration)
# ---------------------------------------------------------------------------

def test_disconnected_variables_bind_cartesian_not_shared():
    world = (
        _fact("p", ("a", "a")),
        _fact("q", ("b", "b")),
        _rule((Atom("p", ("?x", "?x")), Atom("q", ("?y", "?y"))),
              Atom("r", ("?x", "?y"))),
    )
    assert reference_closure(world) == frozenset({
        Atom("p", ("a", "a")), Atom("q", ("b", "b")),
        Atom("r", ("a", "b")),
    })


# ---------------------------------------------------------------------------
# 7. Ground premises, repeated premises, ground heads
# ---------------------------------------------------------------------------

def test_ground_body_rule_fires_only_when_premise_present():
    rule = _rule((Atom("p", ("a", "a")),), Atom("g", ("a", "b")))
    world = (_fact("p", ("a", "a")), rule)
    assert reference_closure(world) == frozenset({
        Atom("p", ("a", "a")), Atom("g", ("a", "b")),
    })


def test_repeated_same_premise_is_satisfied_by_one_fact():
    world = (
        _fact("p", ("a", "b")),
        _rule((Atom("p", ("?x", "?y")), Atom("p", ("?x", "?y"))),
              Atom("twice", ("?x", "?y"))),
    )
    assert reference_closure(world) == frozenset({
        Atom("p", ("a", "b")), Atom("twice", ("a", "b")),
    })


def test_body_variables_with_ground_head_derive_once():
    world = (
        _fact("p", ("a", "b")),
        _rule((Atom("p", ("?x", "?y")),), Atom("g2", ("a", "b"))),
    )
    assert reference_closure(world) == frozenset({
        Atom("p", ("a", "b")), Atom("g2", ("a", "b")),
    })


# ---------------------------------------------------------------------------
# 8. No facts and cycles
# ---------------------------------------------------------------------------

def test_variable_rule_without_constants_has_no_candidates():
    # No constant anywhere: the domain is empty, so nothing is derivable.
    world = (_copy_rule("p", "q"),)
    assert reference_closure(world) == frozenset()


def test_ground_rule_without_initial_fact_derives_nothing():
    world = (_rule((Atom("p", ("a", "a")),), Atom("g", ("a", "b"))),)
    assert reference_closure(world) == frozenset()


def test_cycle_without_seed_derives_nothing():
    # Cyclic rules are a termination check only; this is NOT an E0 world.
    world = (_copy_rule("p", "q"), _copy_rule("q", "p"))
    assert reference_closure(world) == frozenset()


def test_cycle_with_seed_terminates_with_both_atoms():
    world = (_fact("p", ("a", "b")),) + (_copy_rule("p", "q"),
                                         _copy_rule("q", "p"))
    assert reference_closure(world) == frozenset({
        Atom("p", ("a", "b")), Atom("q", ("a", "b")),
    })


# ---------------------------------------------------------------------------
# 9. Per-rule variable scope and no cross-call state
# ---------------------------------------------------------------------------

def test_same_variable_names_are_scoped_per_rule():
    world = (
        _fact("p", ("a", "b")),
        _fact("q", ("c", "d")),
        _rule((Atom("p", ("?x", "?y")),), Atom("u", ("?x", "?y"))),
        _rule((Atom("q", ("?x", "?y")),), Atom("v", ("?x", "?y"))),
    )
    assert reference_closure(world) == frozenset({
        Atom("p", ("a", "b")), Atom("q", ("c", "d")),
        Atom("u", ("a", "b")), Atom("v", ("c", "d")),
    })
    # Solving this world leaves no state visible to later calls.
    assert reference_closure(()) == frozenset()


# ---------------------------------------------------------------------------
# 10. Semantic invariance: reorder / rename / duplicate changes nothing
# ---------------------------------------------------------------------------

def test_main_example_rule_order_reversed_same_closure():
    assert reference_closure(_main_world()[::-1]) == _main_expected()


def test_main_example_join_premise_swap_same_closure():
    world = (_main_world()[0], _main_world()[1],
             _rule((Atom("r2", ("?y", "?z")), Atom("r1", ("?x", "?y"))),
                   Atom("r3", ("?x", "?z"))),
             _main_world()[3])
    assert reference_closure(world) == _main_expected()


def test_main_example_consistent_variable_rename_same_closure():
    world = (_main_world()[0], _main_world()[1],
             _rule((Atom("r1", ("?a", "?b")), Atom("r2", ("?b", "?c"))),
                   Atom("r3", ("?a", "?c"))),
             _main_world()[3])
    assert reference_closure(world) == _main_expected()


def test_duplicated_rule_does_not_change_closure():
    world = _main_world()
    assert reference_closure(world + (world[2],)) == _main_expected()


def test_result_type_is_exact_frozenset_of_ground_atoms():
    result = reference_closure(_main_world())
    assert type(result) is frozenset
    assert all(atom.is_ground for atom in result)


def test_input_clauses_are_not_mutated_or_reordered():
    world = _main_world()
    original = ["Clause(body=%r, head=%r)" % (c.body, c.head) for c in world]
    reference_closure(world)
    assert tuple(world) is world
    assert ["Clause(body=%r, head=%r)" % (c.body, c.head) for c in world] \
        == original


def test_closure_used_as_facts_is_fixed_point():
    full = reference_closure(_main_world())
    world = tuple(Clause((), atom) for atom in sorted(full, key=lambda a:
                                                              (a.pred, a.args)))
    assert reference_closure(world + _main_world()) == full


# ---------------------------------------------------------------------------
# 11. Input validation, error contract, exact budget accounting
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_clauses",
    [
        [_fact("p", ("a", "b"))],                      # list
        {_fact("p", ("a", "b"))},                      # set
        {"a": 1},                                      # dict
        _fact("p", ("a", "b")),                        # Clause, not tuple
        (c for c in ()),                               # generator
    ],
    ids=["list", "set", "dict", "clause-instance", "generator"],
)
def test_non_tuple_container_rejected_with_field_and_reason(bad_clauses):
    with pytest.raises(LogicValidationError) as ei:
        reference_closure(bad_clauses)
    message = str(ei.value)
    assert "reference.clauses" in message
    assert "tuple" in message


@pytest.mark.parametrize(
    ("bad_member", "index"),
    [(Atom("p", ("a", "b")), 0), (42, 1)],
    ids=["atom-member", "int-member"],
)
def test_non_clause_member_rejected_with_index(bad_member, index):
    clauses = [_fact("p", ("a", "b"))]
    clauses.insert(index, bad_member)
    with pytest.raises(LogicValidationError) as ei:
        reference_closure(tuple(clauses))
    message = str(ei.value)
    assert f"reference.clauses[{index}]" in message
    assert "Clause" in message


@pytest.mark.parametrize(
    ("bad_budget", "expect"),
    [
        (True, ("bool", "non-bool")),
        (False, ("bool", "non-bool")),
        (0, ("positive",)),
        (-1, ("positive",)),
        (1.5, ("float",)),
        ("2", ("str",)),
        (None, ("NoneType",)),
    ],
    ids=["bool-true", "bool-false", "zero", "negative",
         "float", "str", "none"],
)
def test_invalid_budget_rejected_with_field_and_reason(bad_budget, expect):
    # Empty world is legal, so this isolates the budget validation;
    # validation must happen before any empty-input fast-return.
    with pytest.raises(LogicValidationError) as ei:
        reference_closure((), max_rule_evaluations=bad_budget)
    message = str(ei.value)
    assert "reference.max_rule_evaluations" in message
    for fragment in expect:
        assert fragment in message


def _big_int():
    return 10 ** 5000


@pytest.mark.parametrize(
    ("build", "field", "expect"),
    [
        (lambda: reference_closure(_big_int()), "reference.clauses", "tuple"),
        (lambda: reference_closure((_big_int(),)), "reference.clauses[0]", "Clause"),
        (lambda: reference_closure((),
                                   max_rule_evaluations=-_big_int()),
         "reference.max_rule_evaluations", "positive"),
    ],
    ids=["clauses-oversized-int", "clauses-tuple-oversized-int",
         "budget-negative-oversized-int"],
)
def test_oversized_int_inputs_keep_error_contract(
    pinned_int_str_limit, build, field, expect
):
    # The dedicated exception with the field path and the target reason
    # must be raised; a native ValueError from int-to-str conversion
    # would escape instead.
    with pytest.raises(LogicValidationError) as ei:
        build()
    message = str(ei.value)
    assert field in message
    assert expect in message


def test_wrong_arity_stays_plain_type_error():
    with pytest.raises(TypeError):
        reference_closure()
    with pytest.raises(TypeError):
        reference_closure((), 1)
    with pytest.raises(TypeError):
        reference_closure((), max_rule_evaluation=1)


def _copy_budget_world():
    return (
        _fact("p", ("a", "a")),
        _rule((Atom("p", ("?x", "?x")),), Atom("q", ("?x", "?x"))),
    )


_PQ = frozenset({Atom("p", ("a", "a")), Atom("q", ("a", "a"))})


def test_exact_budget_single_copy_two_succeeds_one_fails():
    world = _copy_budget_world()
    assert reference_closure(world,
                             max_rule_evaluations=2) == _PQ
    with pytest.raises(ReferenceLimitError) as ei:
        reference_closure(world, max_rule_evaluations=1)
    assert "reference.max_rule_evaluations" in str(ei.value)


def test_exact_budget_duplicated_copy_four_succeeds_three_fails():
    rule = _copy_budget_world()[1]
    world = (_copy_budget_world()[0], rule, rule)
    assert reference_closure(world,
                             max_rule_evaluations=4) == _PQ
    with pytest.raises(ReferenceLimitError):
        reference_closure(world, max_rule_evaluations=3)


def test_exact_budget_failing_premise_counts_from_first_round():
    world = (
        _fact("p", ("a", "a")),
        _rule((Atom("p", ("?x", "?x")),), Atom("q", ("?x", "?x"))),
        _rule((Atom("q", ("?x", "?x")),), Atom("r", ("?x", "?x"))),
    )
    expected = frozenset({Atom("p", ("a", "a")), Atom("q", ("a", "a")),
                          Atom("r", ("a", "a"))})
    assert reference_closure(world, max_rule_evaluations=6) == expected
    with pytest.raises(ReferenceLimitError):
        reference_closure(world, max_rule_evaluations=5)


def test_exact_budget_failed_bindings_are_counted_too():
    # q(?x, k) puts k in the domain, so each round tries candidates
    # x=a and x=k; the x=k check fails but still counts.
    world = (
        _fact("p", ("a", "a")),
        _rule((Atom("p", ("?x", "?x")),), Atom("q", ("?x", "k"))),
    )
    expected = frozenset({Atom("p", ("a", "a")), Atom("q", ("a", "k"))})
    assert reference_closure(world, max_rule_evaluations=4) == expected
    with pytest.raises(ReferenceLimitError):
        reference_closure(world, max_rule_evaluations=3)


def test_facts_only_worlds_do_not_consume_budget():
    assert reference_closure((), max_rule_evaluations=1) == frozenset()
    fact = _fact("s", ("a", "b"))
    assert reference_closure((fact, fact),
                             max_rule_evaluations=1) == \
        frozenset({fact.head})


def test_budget_exhaustion_leaves_no_partial_results_and_no_state():
    world = _copy_budget_world()
    with pytest.raises(ReferenceLimitError):
        reference_closure(world, max_rule_evaluations=1)
    # A later well-budgeted call on the same world is unaffected.
    assert reference_closure(world) == _PQ


# ---------------------------------------------------------------------------
# 12. Import isolation: new subprocess blocks torch and yaml
# ---------------------------------------------------------------------------

def test_import_isolation_blocks_torch_and_yaml():
    code = textwrap.dedent("""
        import sys

        class _BlocklistFinder:
            BLOCKED = ("torch", "yaml")

            def find_spec(self, fullname, path=None, target=None):
                root = fullname.split(".")[0]
                if root in self.BLOCKED:
                    raise ImportError(
                        f"import of {fullname!r} is blocked in this test")
                return None

        sys.meta_path.insert(0, _BlocklistFinder())
        import kmesh.logic

        assert "kmesh.logic.reference_engine" not in sys.modules, (
            "the package must not import the solver automatically")

        from kmesh.logic.reference_engine import reference_closure
        from kmesh.logic.types import Atom, Clause

        result = reference_closure(
            (
                Clause((), Atom("p", ("a", "b"))),
                Clause((Atom("p", ("?x", "?y")),),
                       Atom("q", ("?x", "?y"))),
            )
        )
        expected = frozenset({Atom("p", ("a", "b")),
                              Atom("q", ("a", "b"))})
        assert result == expected, f"unexpected closure: {result!r}"
        leaked = [name for name in list(_BlocklistFinder.BLOCKED)
                  if name in sys.modules]
        assert not leaked, f"blocked modules leaked into sys.modules: {leaked}"
        print("ISOLATION-OK")
    """)
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert "ISOLATION-OK" in proc.stdout
