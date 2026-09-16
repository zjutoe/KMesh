"""Tests for the indexed main closure solver (T0005).

Every expected closure is hand-computed for a small synthetic world;
hand-computed expectations never call either solver or a solver private.
Budget accounting is validated against the exact per-candidate check
definition in the handoff budget table and D20. The 64 deterministically
generated small worlds exist only here: they cross-validate the indexed
closure against the accepted reference closure and are not research data.
"""

import random
import subprocess
import sys
import textwrap

import pytest

import kmesh.logic.engine as engine
from kmesh.logic.engine import IndexedLimitError
from kmesh.logic.engine import indexed_closure
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


def _limit_exhausted(world, budget):
    with pytest.raises(IndexedLimitError) as ei:
        indexed_closure(world, max_fact_checks=budget)
    assert "indexed.max_fact_checks" in str(ei.value)


# ---------------------------------------------------------------------------
# 1. Exact budget table (handoff section 4): succeed exactly, fail short by 1
# ---------------------------------------------------------------------------

def test_exact_budget_single_copy_two_succeeds_one_fails():
    world = (
        _fact("p", ("a", "a")),
        _rule((Atom("p", ("?x", "?x")),), Atom("q", ("?x", "?x"))),
    )
    expected = frozenset({Atom("p", ("a", "a")), Atom("q", ("a", "a"))})
    assert indexed_closure(world, max_fact_checks=2) == expected
    _limit_exhausted(world, 1)


def test_exact_budget_duplicated_copy_four_succeeds_three_fails():
    copy = _copy_rule("p", "q")
    world = (_fact("p", ("a", "a")), copy, copy)
    expected = frozenset({Atom("p", ("a", "a")), Atom("q", ("a", "a"))})
    assert indexed_closure(world, max_fact_checks=4) == expected
    _limit_exhausted(world, 3)


def test_exact_budget_chained_rules_no_intra_round_propagation():
    world = (
        _fact("p", ("a", "a")),
        _rule((Atom("p", ("?x", "?x")),), Atom("q", ("?x", "?x"))),
        _rule((Atom("q", ("?x", "?x")),), Atom("r", ("?x", "?x"))),
    )
    expected = frozenset({Atom("p", ("a", "a")), Atom("q", ("a", "a")),
                          Atom("r", ("a", "a"))})
    # Rounds cost 1 + 2 + 2: the q rule's bucket is empty in round one,
    # so r(a,a) can only appear in round three.
    assert indexed_closure(world, max_fact_checks=5) == expected
    _limit_exhausted(world, 4)


def test_exact_budget_failed_premise_matches_are_counted():
    world = (
        _fact("p", ("a", "a")),
        _fact("p", ("b", "b")),
        _rule((Atom("p", ("?x", "a")),), Atom("q", ("?x", "a"))),
    )
    expected = frozenset({Atom("p", ("a", "a")), Atom("p", ("b", "b")),
                          Atom("q", ("a", "a"))})
    # Both p candidates are checked in each round; the (b, b) candidate
    # fails the constant check but still costs one unit.
    assert indexed_closure(world, max_fact_checks=4) == expected
    _limit_exhausted(world, 3)


def test_exact_budget_join_counts_each_branch_twice():
    world = (
        _fact("p", ("a", "b")),
        _fact("p", ("a", "c")),
        _fact("q", ("b", "d")),
        _rule((Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))),
              Atom("r", ("?x", "?z"))),
    )
    expected = frozenset({Atom("p", ("a", "b")), Atom("p", ("a", "c")),
                          Atom("q", ("b", "d")), Atom("r", ("a", "d"))})
    # Per round: 2 p candidates succeed, then each branch checks the one
    # q candidate (one succeeds, one fails on ?y) = 4; the final no-new
    # round costs the same 2 first + 2 second checks, total 8.
    assert indexed_closure(world, max_fact_checks=8) == expected
    _limit_exhausted(world, 7)


def test_exact_budget_second_bucket_empty_still_counts_first_premises():
    world = (
        _fact("p", ("a", "a")),
        _fact("p", ("b", "b")),
        _rule((Atom("p", ("?x", "?y")), Atom("q", ("?x", "?y"))),
              Atom("r", ("?x", "?y"))),
    )
    # No q facts: the q bucket is empty (cost 0) and clears the
    # surviving bindings, so no head is ever derived; the two p
    # candidates are checked in this single terminating round, total 2.
    expected = frozenset({Atom("p", ("a", "a")), Atom("p", ("b", "b"))})
    assert indexed_closure(world, max_fact_checks=2) == expected
    _limit_exhausted(world, 1)


def test_exact_budget_irrelevant_predicate_facts_are_not_counted():
    copy = _copy_rule("p", "q")
    world = (
        _fact("p", ("a", "a")),
        _fact("s", ("c", "c")),
        _fact("t", ("d", "d")),
        copy,
    )
    # Only the two p(a,a) candidates are ever checked.
    expected = frozenset({Atom("p", ("a", "a")), Atom("s", ("c", "c")),
                          Atom("t", ("d", "d")), Atom("q", ("a", "a"))})
    assert indexed_closure(world, max_fact_checks=2) == expected
    _limit_exhausted(world, 1)


# ---------------------------------------------------------------------------
# 2. Hand-processed main example (research plan section 4.2 shape)
# ---------------------------------------------------------------------------

def _join_world():
    return (
        _fact("r1", ("a", "b")),
        _fact("r2", ("b", "c")),
        _rule((Atom("r1", ("?x", "?y")), Atom("r2", ("?y", "?z"))),
              Atom("r3", ("?x", "?z"))),
        _rule((Atom("r3", ("?x", "?y")),), Atom("r4", ("?y", "?x"))),
    )


_JOIN_EXPECTED = frozenset({
    Atom("r1", ("a", "b")), Atom("r2", ("b", "c")),
    Atom("r3", ("a", "c")), Atom("r4", ("c", "a")),
})


def test_main_example_full_closure():
    assert indexed_closure(_join_world()) == _JOIN_EXPECTED


def test_main_example_head_argument_order_changes_result():
    world = _join_world()[:3] + (
        _rule((Atom("r3", ("?x", "?y")),), Atom("r4", ("?x", "?y"))),
    )
    assert indexed_closure(world) == \
        _JOIN_EXPECTED - {Atom("r4", ("c", "a"))} | \
        {Atom("r4", ("a", "c"))}


def test_main_example_missing_premise_fact_blocks_derivation():
    world = _join_world()
    assert indexed_closure((world[0], world[2], world[3])) == \
        frozenset({Atom("r1", ("a", "b"))})


# ---------------------------------------------------------------------------
# 3. COPY / INV / INTER and JOIN bindings
# ---------------------------------------------------------------------------

def test_copy_rule_derives_same_pair():
    world = (_fact("p", ("a", "b")), _copy_rule("p", "q"))
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("q", ("a", "b"))})


def test_inv_rule_derives_swapped_pair():
    world = (_fact("p", ("a", "b")),
             _rule((Atom("p", ("?x", "?y")),), Atom("q", ("?y", "?x"))))
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("q", ("b", "a"))})


def test_join_rule_chains_p_predicate_twice():
    world = (
        _fact("p", ("a", "b")),
        _fact("p", ("b", "c")),
        _rule((Atom("p", ("?x", "?y")), Atom("p", ("?y", "?z"))),
              Atom("r", ("?x", "?z"))),
    )
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("p", ("b", "c")),
         Atom("r", ("a", "c"))})


def test_inter_rule_derives_only_exactly_shared_pairs():
    world = (
        _fact("p", ("a", "b")),
        _fact("p", ("c", "d")),
        _fact("q", ("a", "b")),
        _fact("q", ("b", "a")),
        _fact("q", ("c", "e")),
        _rule((Atom("p", ("?x", "?y")), Atom("q", ("?x", "?y"))),
              Atom("r", ("?x", "?y"))),
    )
    # only q(a,b) shares both arguments with a p fact; the reversed
    # q(b,a) and same-first-argument q(c,e) must not derive anything
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("p", ("c", "d")),
         Atom("q", ("a", "b")), Atom("q", ("b", "a")),
         Atom("q", ("c", "e")), Atom("r", ("a", "b"))})


def test_join_keeps_multiple_success_bindings():
    world = (
        _fact("p", ("a", "b")),
        _fact("q", ("b", "d")),
        _fact("q", ("b", "e")),
        _rule((Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))),
              Atom("r", ("?x", "?z"))),
    )
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("q", ("b", "d")),
         Atom("q", ("b", "e")), Atom("r", ("a", "d")),
         Atom("r", ("a", "e"))})


def test_join_disconnected_intermediate_variables_never_splice():
    world = (
        _fact("p", ("a", "b")),
        _fact("q", ("c", "d")),
        _rule((Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))),
              Atom("r", ("?x", "?z"))),
    )
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("q", ("c", "d"))})


# ---------------------------------------------------------------------------
# 3b. Nested per-candidate processing guard (D20 step 3.4, R1 rework)
# ---------------------------------------------------------------------------

def test_nested_matching_instantiates_head_after_second_check(monkeypatch):
    match_calls: list[None] = []
    instantiate_after: list[int] = []
    original_match = engine._match
    original_instantiate = engine._instantiate

    def counted_match(premise, candidate, binding):
        match_calls.append(None)
        return original_match(premise, candidate, binding)

    def counted_instantiate(atom, binding):
        instantiate_after.append(len(match_calls))
        return original_instantiate(atom, binding)

    monkeypatch.setattr(engine, "_match", counted_match)
    monkeypatch.setattr(engine, "_instantiate", counted_instantiate)

    world = (
        _fact("p", ("a", "a")),
        _fact("p", ("b", "b")),
        _fact("q", ("a", "a")),
        _fact("q", ("b", "b")),
        _rule((Atom("p", ("?x", "?x")), Atom("q", ("?y", "?y"))),
              Atom("out", ("k", "k"))),
    )
    closure = indexed_closure(world)
    assert closure == frozenset(
        {Atom("p", ("a", "a")), Atom("p", ("b", "b")),
         Atom("q", ("a", "a")), Atom("q", ("b", "b")),
         Atom("out", ("k", "k"))})
    # nested matching must produce the first head right after the
    # second check (first p fact + first q fact), not after materialising
    # every successful premise binding of the round
    assert instantiate_after, "head was never instantiated"
    assert instantiate_after[0] == 2
    # per-candidate accounting is unchanged: 6 checks per round, and the
    # final no-new round is counted too
    assert len(match_calls) == 12


# ---------------------------------------------------------------------------
# 4. Repeated premises, repeated variables and branch isolation
# ---------------------------------------------------------------------------

def test_repeated_same_premise_is_satisfied_by_one_fact():
    world = (
        _fact("p", ("a", "b")),
        _rule((Atom("p", ("?x", "?y")), Atom("p", ("?x", "?y"))),
              Atom("r", ("?x", "?y"))),
    )
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("r", ("a", "b"))})


def test_repeated_variable_inconsistent_candidate_does_not_pollute_next():
    world = (
        _fact("p", ("a", "b")),
        _fact("p", ("b", "b")),
        _rule((Atom("p", ("?x", "?x")),), Atom("s", ("?x", "?x"))),
    )
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("p", ("b", "b")),
         Atom("s", ("b", "b"))})


def test_branch_variable_conflict_discards_only_that_branch():
    world = (
        _fact("p", ("a", "b")),
        _fact("q", ("d", "c")),
        _fact("q", ("e", "b")),
        _rule((Atom("p", ("?x", "?y")), Atom("q", ("?z", "?y"))),
              Atom("r", ("?x", "?z"))),
    )
    # q(d, c) binds ?z=d then fails on ?y=b; the branch dies and q(e, b)
    # still yields r(a, e).
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("q", ("d", "c")),
         Atom("q", ("e", "b")), Atom("r", ("a", "e"))})


# ---------------------------------------------------------------------------
# 5. Ground premises, ground heads and literal constant chains
# ---------------------------------------------------------------------------

def test_ground_body_rule_fires_only_when_exact_fact_present():
    rule = _rule((Atom("q", ("b", "d")),), Atom("s", ("c", "c")))
    assert indexed_closure((_fact("q", ("b", "d")), rule)) == frozenset(
        {Atom("q", ("b", "d")), Atom("s", ("c", "c"))})
    assert indexed_closure((_fact("q", ("b", "e")), rule)) == frozenset(
        {Atom("q", ("b", "e"))})


def test_variable_body_with_ground_head_derives_once():
    world = (
        _fact("p", ("a", "a")),
        _fact("p", ("b", "b")),
        _rule((Atom("p", ("?x", "?x")),), Atom("s", ("a", "a"))),
    )
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "a")), Atom("p", ("b", "b")),
         Atom("s", ("a", "a"))})


def test_literal_constant_chain():
    world = (
        _fact("p", ("a", "a")),
        _rule((Atom("p", ("?x", "?x")),), Atom("q", ("c", "?x"))),
        _rule((Atom("q", ("?x", "?y")),), Atom("r", ("?x", "?y"))),
    )
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "a")), Atom("q", ("c", "a")),
         Atom("r", ("c", "a"))})


def test_ground_rule_literal_head_constant_not_in_facts():
    world = (
        _fact("p", ("a", "b")),
        _rule((Atom("p", ("a", "b")),), Atom("q", ("z", "w"))),
    )
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("q", ("z", "w"))})


# ---------------------------------------------------------------------------
# 6. Empty, facts-only, cycles and candidate-less rules
# ---------------------------------------------------------------------------

def test_empty_world_returns_empty_frozenset():
    assert indexed_closure(()) == frozenset()


def test_duplicate_facts_deduplicate():
    fact = _fact("p", ("a", "b"))
    assert indexed_closure((fact, fact)) == frozenset(
        {Atom("p", ("a", "b"))})


def test_cycle_without_seed_derives_nothing():
    world = (
        _rule((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
        _rule((Atom("q", ("?x", "?y")),), Atom("p", ("?x", "?y"))),
    )
    assert indexed_closure(world) == frozenset()


def test_cycle_with_seed_terminates_with_both_atoms():
    world = (
        _fact("p", ("a", "b")),
        _rule((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
        _rule((Atom("q", ("?x", "?y")),), Atom("p", ("?x", "?y"))),
    )
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "b")), Atom("q", ("a", "b"))})


def test_candidate_less_rule_returns_original_facts_within_budget_one():
    world = (
        _fact("p", ("a", "b")),
        _rule((Atom("q", ("?x", "?y")),), Atom("r", ("?x", "?y"))),
    )
    assert indexed_closure(world, max_fact_checks=1) == frozenset(
        {Atom("p", ("a", "b"))})


# ---------------------------------------------------------------------------
# 7. Semantic invariance, purity and result types
# ---------------------------------------------------------------------------

def test_rule_reorder_keeps_manual_closure():
    world = _join_world()
    reordered = (world[0], world[1], world[3], world[2])
    assert indexed_closure(reordered) == _JOIN_EXPECTED


def test_join_premise_swap_keeps_manual_closure():
    world = _join_world()
    swapped = (
        world[0], world[1],
        _rule((Atom("r2", ("?y", "?z")), Atom("r1", ("?x", "?y"))),
              Atom("r3", ("?x", "?z"))),
        world[3],
    )
    assert indexed_closure(swapped) == _JOIN_EXPECTED


def test_variable_rename_keeps_manual_closure():
    world = _join_world()
    renamed = (
        world[0], world[1],
        _rule((Atom("r1", ("?w", "?v")), Atom("r2", ("?v", "?u"))),
              Atom("r3", ("?w", "?u"))),
        world[3],
    )
    assert indexed_closure(renamed) == _JOIN_EXPECTED


def test_duplicated_rule_does_not_change_closure():
    world = _join_world()
    assert indexed_closure(world + (world[2],)) == _JOIN_EXPECTED


def test_input_clauses_are_not_mutated_or_reordered():
    world = _join_world()
    heads = [clause.head for clause in world]
    bodies = [clause.body for clause in world]
    clause_ids = [id(clause) for clause in world]
    indexed_closure(world)
    assert [id(clause) for clause in world] == clause_ids
    assert list(world) == list(_join_world())
    for clause, head, body in zip(world, heads, bodies):
        assert type(clause) is Clause
        assert clause.head is head
        assert clause.body is body


def test_result_type_is_exact_frozenset_of_ground_atoms():
    result = indexed_closure(_join_world())
    assert type(result) is frozenset
    assert all(type(atom) is Atom for atom in result)
    assert all(not atom.variables for atom in result)


def test_budget_exhaustion_leaves_no_partial_results_and_no_state():
    world = (_fact("p", ("a", "a")), _copy_rule("p", "q"))
    with pytest.raises(IndexedLimitError):
        indexed_closure(world, max_fact_checks=1)
    assert indexed_closure(world) == frozenset(
        {Atom("p", ("a", "a")), Atom("q", ("a", "a"))})


# ---------------------------------------------------------------------------
# 8. Input validation: container, members, budget, oversize ints
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
        indexed_closure(bad_clauses)
    message = str(ei.value)
    assert "indexed.clauses must be a tuple of Clause" in message


@pytest.mark.parametrize(
    ("bad_member", "index"),
    [(Atom("p", ("a", "b")), 0), (42, 1)],
    ids=["atom-member", "int-member"],
)
def test_non_clause_member_rejected_with_index(bad_member, index):
    clauses = [_fact("p", ("a", "b"))]
    clauses.insert(index, bad_member)
    with pytest.raises(LogicValidationError) as ei:
        indexed_closure(tuple(clauses))
    message = str(ei.value)
    assert f"indexed.clauses[{index}] must be a Clause" in message


@pytest.mark.parametrize(
    "bad_budget",
    [True, False, 0, -1, 1.5, "2", None],
    ids=["bool-true", "bool-false", "zero", "negative", "float", "str",
         "none"],
)
def test_invalid_budget_rejected_with_field_and_reason(bad_budget):
    # Empty world is legal, so this isolates the budget validation;
    # validation must happen before any empty-input fast-return.
    with pytest.raises(LogicValidationError) as ei:
        indexed_closure((), max_fact_checks=bad_budget)
    message = str(ei.value)
    assert "indexed.max_fact_checks must be a non-bool positive integer" \
        in message


def _big_int():
    return 10 ** 5000


@pytest.mark.parametrize(
    ("build", "field", "expect"),
    [
        (lambda: indexed_closure(_big_int()), "indexed.clauses", "tuple"),
        (lambda: indexed_closure((_big_int(),)),
         "indexed.clauses[0]", "Clause"),
        (lambda: indexed_closure((), max_fact_checks=-_big_int()),
         "indexed.max_fact_checks", "positive"),
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
        indexed_closure()
    with pytest.raises(TypeError):
        indexed_closure((), 1)
    with pytest.raises(TypeError):
        indexed_closure((), max_fact_check=1)


# ---------------------------------------------------------------------------
# 9. Import isolation: new subprocess blocks torch, yaml and reference engine
# ---------------------------------------------------------------------------

def test_import_isolation_blocks_torch_yaml_and_reference_engine():
    code = textwrap.dedent("""
        import sys

        class _BlocklistFinder:
            BLOCKED = ("torch", "yaml", "kmesh.logic.reference_engine")

            def find_spec(self, fullname, path=None, target=None):
                root = fullname.split(".")[0]
                for blocked in self.BLOCKED:
                    if root == blocked or fullname == blocked or \\
                            fullname.startswith(blocked + "."):
                        raise ImportError(
                            f"import of {fullname!r} is blocked in this test")
                return None

        sys.meta_path.insert(0, _BlocklistFinder())
        import kmesh.logic

        assert "kmesh.logic.engine" not in sys.modules, (
            "the package must not import any solver automatically")
        assert "kmesh.logic.reference_engine" not in sys.modules

        from kmesh.logic.engine import indexed_closure
        from kmesh.logic.types import Atom, Clause

        result = indexed_closure(
            (
                Clause((), Atom("p", ("a", "b"))),
                Clause((Atom("p", ("?x", "?y")),),
                       Atom("q", ("?x", "?y"))),
            )
        )
        expected = frozenset({Atom("p", ("a", "b")),
                              Atom("q", ("a", "b"))})
        assert result == expected, f"unexpected closure: {result!r}"
        leaked = [name for name in _BlocklistFinder.BLOCKED
                  if name in sys.modules
                  or any(mod == name or mod.startswith(name + ".")
                         for mod in sys.modules)]
        assert not leaked, f"blocked modules leaked into sys.modules: {leaked}"
        print("ISOLATION-OK")
    """)
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert "ISOLATION-OK" in proc.stdout


# ---------------------------------------------------------------------------
# 10. 64 deterministic small worlds: indexed closure vs reference closure
# ---------------------------------------------------------------------------

WORLD_SEED = 20260915
_CONSTANTS = ("a", "b", "c")
_PREDICATES = ("p", "q", "r", "s")
_VARIABLES = ("?x", "?y", "?z", "?w")


def _all_ground_atoms():
    return tuple(
        sorted((Atom(pred, (first, second))
                for pred in _PREDICATES
                for first in _CONSTANTS
                for second in _CONSTANTS),
               key=lambda atom: (atom.pred, atom.args)))


def _reserved_chain():
    return (
        _fact("seed", ("a", "b")),
        _rule((Atom("seed", ("?x", "?y")),), Atom("mid", ("?y", "?x"))),
        _rule((Atom("mid", ("?x", "?y")),), Atom("out", ("?x", "?y"))),
    )


def _random_worlds():
    """Number 0-63 worlds from the shared seed in that exact order."""
    rng = random.Random(WORLD_SEED)
    universe = _all_ground_atoms()
    for number in range(64):
        facts = rng.sample(universe, rng.randint(0, 6))
        rules = []
        for _ in range(rng.randint(1, 4)):
            body = [
                Atom(rng.choice(_PREDICATES),
                     (rng.choice(_CONSTANTS + _VARIABLES),
                      rng.choice(_CONSTANTS + _VARIABLES)))
                for _ in range(rng.randint(1, 2))
            ]
            body_variables = tuple(sorted(
                {arg for atom in body for arg in atom.args
                 if arg.startswith("?")}))
            head_pool = _CONSTANTS + body_variables
            rules.append(Clause(
                tuple(body),
                Atom(rng.choice(_PREDICATES),
                     (rng.choice(head_pool), rng.choice(head_pool)))))
        if number % 2 == 0:
            facts = tuple(facts) + (Atom("seed", ("a", "b")),)
            rules = tuple(rules) + _reserved_chain()[1:]
        yield number, tuple(Clause((), atom) for atom in facts) + \
            tuple(rules)


_WORLDS = list(_random_worlds())


def _atom_text(atom):
    return f"{atom.pred}({', '.join(atom.args)})"


def _describe(world):
    parts = []
    for clause in world:
        if not clause.body:
            parts.append(f"fact {_atom_text(clause.head)}")
        else:
            parts.append("rule " +
                         ", ".join(_atom_text(p) for p in clause.body) +
                         " -> " + _atom_text(clause.head))
    return "; ".join(parts)


def _sorted_text(atoms):
    return ", ".join(_atom_text(atom) for atom in
                     sorted(atoms, key=lambda a: (a.pred, a.args)))


@pytest.mark.parametrize(
    ("number", "world"),
    _WORLDS,
    ids=[f"world-{number:02d}" for number, _ in _WORLDS],
)
def test_random_world_matches_reference_closure(number, world):
    indexed = indexed_closure(world)
    reference = reference_closure(world)
    detail = (f"world {number} (seed {WORLD_SEED}); "
              f"{_describe(world)}; indexed=[{_sorted_text(indexed)}]; "
              f"reference=[{_sorted_text(reference)}]")
    assert indexed == reference, f"closures diverge: {detail}"
    assert all(not atom.variables for atom in indexed)
    if number % 2 == 0:
        # Even worlds carry the reserved two-step chain; both solvers
        # must derive it rather than only return the initial facts.
        derived = (Atom("mid", ("b", "a")), Atom("out", ("b", "a")))
        missing = tuple(a for a in derived if a not in indexed)
        assert not missing, f"chain atoms missing: {detail}"
        missing = tuple(a for a in derived if a not in reference)
        assert not missing, f"chain atoms missing from reference: {detail}"
