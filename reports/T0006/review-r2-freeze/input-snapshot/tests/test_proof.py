"""Tests for the independent given-proof verifier (T0006).

All expected results are hand-computed from the fixtures below; no closure
solver is imported here, and assertions target the documented behaviour of
``ProofStep`` and ``verify_proof`` (field paths, reason fragments, and the
True/False/ProofLimitError boundary), not solver output.
"""

from __future__ import annotations

import dataclasses
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

from kmesh.logic.proof import ProofLimitError, ProofStep, verify_proof
from kmesh.logic.types import Atom, Clause, LogicValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]


_BLOCKED_ROOTS = (
    "torch",
    "yaml",
    "kmesh.logic.engine",
    "kmesh.logic.reference_engine",
)


def _is_blocked(fullname):
    """True for a blocked root and any child module below it."""
    return any(
        fullname == root or fullname.startswith(root + ".")
        for root in _BLOCKED_ROOTS
    )


class _Guard:
    """Meta path finder that hard-blocks blocked roots and children."""

    def find_spec(self, fullname, path=None, target=None):
        if _is_blocked(fullname):
            raise ImportError(f"test forbids importing {fullname}")
        return None


@pytest.fixture(autouse=True)
def _forbid_solver_and_blocked_imports():
    """Keep every test free of torch/yaml/solver modules.

    The guard raises from ``find_spec`` for a blocked root *and any
    child module*.  The fixture also removes any blocked module already
    imported earlier in the process (e.g. by another test file) so an
    ``importlib.import_module`` call inside a test must re-enter the
    guard; both the import block and the saved module state are restored
    afterwards.
    """
    saved = {name: sys.modules.pop(name)
             for name in list(sys.modules) if _is_blocked(name)}
    old_meta_path = sys.meta_path
    sys.meta_path = [_Guard()] + list(old_meta_path)
    try:
        yield
    finally:
        sys.meta_path = old_meta_path
        for name in list(sys.modules):
            if _is_blocked(name):
                del sys.modules[name]
        sys.modules.update(saved)


def _atom(pred, *args):
    return Atom(pred, tuple(args))


def _fact(pred, *args):
    return Clause((), _atom(pred, *args))


def _rule(premises, pred, *args):
    return Clause(tuple(premises), _atom(pred, *args))


def _main_example():
    """Research plan S4.2 main example (hand-computed fixture)."""
    clauses = (
        Clause((), Atom("r1", ("a", "b"))),
        Clause((), Atom("r2", ("b", "c"))),
        Clause(
            (Atom("r1", ("?x", "?y")), Atom("r2", ("?y", "?z"))),
            Atom("r3", ("?x", "?z")),
        ),
        Clause((Atom("r3", ("?x", "?y")),), Atom("r4", ("?y", "?x"))),
    )
    proof = (
        ProofStep(0, (), Atom("r1", ("a", "b"))),
        ProofStep(1, (), Atom("r2", ("b", "c"))),
        ProofStep(2, (0, 1), Atom("r3", ("a", "c"))),
        ProofStep(3, (2,), Atom("r4", ("c", "a"))),
    )
    query = Atom("r4", ("c", "a"))
    return clauses, proof, query


class TestValidGivenEvidence:
    def test_original_fact(self):
        world = (_fact("r1", "a", "b"),)
        proof = (ProofStep(0, (), _atom("r1", "a", "b")),)
        assert verify_proof(world, _atom("r1", "a", "b"), proof) is True

    def test_one_step_copy(self):
        world = (_fact("p", "a", "a"),
                 _rule((_atom("p", "?x", "?x"),), "q", "?x", "?x"))
        proof = (ProofStep(0, (), _atom("p", "a", "a")),
                 ProofStep(1, (0,), _atom("q", "a", "a")))
        assert verify_proof(world, _atom("q", "a", "a"), proof) is True

    def test_one_step_inversion(self):
        world = (_fact("p", "a", "b"),
                 _rule((_atom("p", "?x", "?y"),), "q", "?y", "?x"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (0,), _atom("q", "b", "a")))
        assert verify_proof(world, _atom("q", "b", "a"), proof) is True

    def test_main_example_join_then_inversion(self):
        clauses, proof, query = _main_example()
        assert verify_proof(clauses, query, proof, max_steps=4) is True

    def test_true_inter_two_distinct_predicates(self):
        world = (_fact("p", "a", "b"), _fact("q", "a", "b"),
                 _rule((_atom("p", "?x", "?y"), _atom("q", "?x", "?y")),
                       "r", "?x", "?y"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("q", "a", "b")),
                 ProofStep(2, (0, 1), _atom("r", "a", "b")))
        assert verify_proof(world, _atom("r", "a", "b"), proof) is True

    def test_join_rule(self):
        world = (_fact("p", "a", "b"), _fact("p", "b", "c"),
                 _rule((_atom("p", "?x", "?y"), _atom("p", "?y", "?z")),
                       "r", "?x", "?z"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("p", "b", "c")),
                 ProofStep(2, (0, 1), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is True

    def test_repeated_variable_in_premise(self):
        world = (_fact("p", "a", "a"),
                 _rule((_atom("p", "?x", "?x"),), "s", "?x", "?x"))
        proof = (ProofStep(0, (), _atom("p", "a", "a")),
                 ProofStep(1, (0,), _atom("s", "a", "a")))
        assert verify_proof(world, _atom("s", "a", "a"), proof) is True

    def test_duplicate_reference_satisfies_repeated_body(self):
        world = (_fact("p", "a", "a"),
                 _rule((_atom("p", "?x", "?y"), _atom("p", "?y", "?x")),
                       "r", "?x", "?y"))
        proof = (ProofStep(0, (), _atom("p", "a", "a")),
                 ProofStep(1, (0, 0), _atom("r", "a", "a")))
        assert verify_proof(world, _atom("r", "a", "a"), proof) is True

    def test_ground_rule(self):
        world = (_fact("p", "a", "b"),
                 _rule((_atom("p", "a", "b"),), "q", "c", "d"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (0,), _atom("q", "c", "d")))
        assert verify_proof(world, _atom("q", "c", "d"), proof) is True

    def test_mixed_constants(self):
        world = (_fact("p", "a", "b"),
                 _rule((_atom("p", "?x", "b"),), "q", "b", "?x"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (0,), _atom("q", "b", "a")))
        assert verify_proof(world, _atom("q", "b", "a"), proof) is True

    def test_body_only_variables_with_ground_head(self):
        world = (_fact("p", "a", "b"),
                 _rule((_atom("p", "?x", "?y"),), "q", "c", "c"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (0,), _atom("q", "c", "c")))
        assert verify_proof(world, _atom("q", "c", "c"), proof) is True

    def test_same_variable_name_different_values_across_steps(self):
        world = (_fact("p", "a", "a"), _fact("p", "b", "b"),
                 _rule((_atom("p", "?x", "?x"),), "s", "?x", "?x"))
        proof = (ProofStep(0, (), _atom("p", "a", "a")),
                 ProofStep(1, (), _atom("p", "b", "b")),
                 ProofStep(2, (0,), _atom("s", "a", "a")),
                 ProofStep(2, (1,), _atom("s", "b", "b")))
        assert verify_proof(world, _atom("s", "b", "b"), proof) is True

    def test_irrelevant_and_repeated_steps_allowed(self):
        world = (_fact("r1", "a", "b"), _fact("r2", "b", "c"),
                 _rule((_atom("r1", "?x", "?y"), _atom("r2", "?y", "?z")),
                       "r3", "?x", "?z"),
                 _rule((_atom("r3", "?x", "?y"),), "r4", "?y", "?x"),
                 _fact("s", "a", "a"))
        proof = (ProofStep(0, (), _atom("r1", "a", "b")),
                 ProofStep(1, (), _atom("r2", "b", "c")),
                 ProofStep(4, (), _atom("s", "a", "a")),
                 ProofStep(2, (0, 1), _atom("r3", "a", "c")),
                 ProofStep(2, (0, 1), _atom("r3", "a", "c")),
                 ProofStep(3, (3,), _atom("r4", "c", "a")))
        assert verify_proof(world, _atom("r4", "c", "a"), proof, max_steps=6) \
            is True

    def test_fact_supported_cyclic_rule_expansion(self):
        world = (_fact("p", "a", "a"),
                 _rule((_atom("p", "?x", "?x"),), "q", "?x", "?x"),
                 _rule((_atom("q", "?x", "?x"),), "p", "?x", "?x"))
        proof = (ProofStep(0, (), _atom("p", "a", "a")),
                 ProofStep(1, (0,), _atom("q", "a", "a")),
                 ProofStep(2, (1,), _atom("p", "a", "a")),
                 ProofStep(1, (2,), _atom("q", "a", "a")))
        assert verify_proof(world, _atom("q", "a", "a"), proof) is True


class TestLogicalCounterexamples:
    def test_empty_proof_is_false(self):
        world = (_fact("p", "a", "b"),)
        assert verify_proof(world, _atom("p", "a", "b"), ()) is False

    def test_empty_world_empty_proof_is_false(self):
        assert verify_proof((), _atom("p", "a", "b"), ()) is False

    def test_out_of_range_clause_index_is_false(self):
        world = (_fact("p", "a", "b"),)
        proof = (ProofStep(1, (), _atom("p", "a", "b")),)
        assert verify_proof(world, _atom("p", "a", "b"), proof) is False

    def test_large_positive_clause_index_is_false(self, int_limit_4300):
        large = 10 ** 5000
        world = (_fact("p", "a", "b"),)
        step = ProofStep(large, (), _atom("p", "a", "b"))
        assert verify_proof(world, _atom("p", "a", "b"), (step,)) is False

    def test_forged_fact_is_false(self):
        world = (_fact("p", "a", "b"),)
        proof = (ProofStep(0, (), _atom("p", "a", "c")),)
        assert verify_proof(world, _atom("p", "a", "c"), proof) is False

    def test_fact_with_premises_is_false(self):
        world = (_fact("p", "a", "b"), _fact("q", "a", "b"))
        proof = (ProofStep(1, (), _atom("q", "a", "b")),
                 ProofStep(0, (0,), _atom("p", "a", "b")))
        assert verify_proof(world, _atom("p", "a", "b"), proof) is False

    def test_rule_with_too_few_premise_references_is_false(self):
        # Two-premise rule, only one reference submitted.  The query is
        # set equal to the step's conclusion so the insufficient
        # reference count is the sole violation.
        world = (_fact("p", "a", "b"), _fact("p", "b", "c"),
                 _rule((_atom("p", "?x", "?y"), _atom("p", "?y", "?z")),
                       "r", "?x", "?z"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(2, (0,), _atom("r", "a", "b")))
        assert verify_proof(world, _atom("r", "a", "b"), proof) is False

    def test_rule_with_too_many_premise_references_is_false(self):
        # Single-premise rule: exactly one prior step may be cited.
        # Both cited steps are legal prior references; the violation is
        # the extra reference alone.
        world = (_fact("p", "a", "b"), _fact("p", "b", "c"),
                 _rule((_atom("p", "?x", "?y"),), "q", "?x", "?y"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("p", "b", "c")),
                 ProofStep(2, (0, 1), _atom("q", "a", "b")))
        assert verify_proof(world, _atom("q", "a", "b"), proof) is False

    def test_self_reference_is_false(self):
        world = (_fact("p", "a", "b"),
                 _rule((_atom("p", "?x", "?y"),), "r", "?x", "c"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (1,), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is False

    def test_forward_reference_is_false(self):
        world = (_fact("p", "a", "b"),
                 _rule((_atom("p", "?x", "?y"),), "r", "?x", "c"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (2,), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is False

    def test_premise_predicate_mismatch_is_false(self):
        world = (_fact("p", "a", "b"), _fact("q", "a", "b"),
                 _rule((_atom("p", "?x", "?y"),), "r", "?x", "?y"))
        proof = (ProofStep(1, (), _atom("q", "a", "b")),
                 ProofStep(2, (0,), _atom("r", "a", "b")))
        assert verify_proof(world, _atom("r", "a", "b"), proof) is False

    def test_premise_constant_mismatch_is_false(self):
        world = (_fact("p", "a", "c"),
                 _rule((_atom("p", "?x", "b"),), "q", "?x", "?x"))
        proof = (ProofStep(0, (), _atom("p", "a", "c")),
                 ProofStep(1, (0,), _atom("q", "a", "a")))
        assert verify_proof(world, _atom("q", "a", "a"), proof) is False

    def test_repeated_variable_conflict_is_false(self):
        world = (_fact("p", "a", "b"),
                 _rule((_atom("p", "?x", "?x"),), "q", "?x", "?x"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (0,), _atom("q", "a", "a")))
        assert verify_proof(world, _atom("q", "a", "a"), proof) is False

    def test_cross_premise_variable_conflict_is_false(self):
        world = (_fact("p", "a", "b"), _fact("q", "b", "c"),
                 _rule((_atom("p", "?x", "?y"), _atom("q", "?x", "?z")),
                       "r", "?y", "?z"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("q", "b", "c")),
                 ProofStep(2, (0, 1), _atom("r", "b", "c")))
        assert verify_proof(world, _atom("r", "b", "c"), proof) is False

    @pytest.mark.parametrize(
        ("mutated_conclusion",),
        [(_atom("s", "a", "c"),),
         (_atom("r", "c", "a"),),
         (_atom("r", "a", "b"),)],
        ids=["predicate", "direction", "entity"],
    )
    def test_tampered_conclusion_is_false(self, mutated_conclusion):
        world = (_fact("p", "a", "b"), _fact("p", "b", "c"),
                 _rule((_atom("p", "?x", "?y"), _atom("p", "?y", "?z")),
                       "r", "?x", "?z"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("p", "b", "c")),
                 ProofStep(2, (0, 1), mutated_conclusion))
        assert verify_proof(world, mutated_conclusion, proof) is False

    def test_final_conclusion_differs_from_query_is_false(self):
        world = (_fact("p", "a", "b"), _fact("p", "b", "c"),
                 _rule((_atom("p", "?x", "?y"), _atom("p", "?y", "?z")),
                       "r", "?x", "?z"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("p", "b", "c")),
                 ProofStep(2, (0, 1), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "b"), proof) is False

    def test_factless_self_sustaining_cycle_is_false(self):
        world = (_rule((_atom("p", "?x", "?x"),), "q", "?x", "?x"),
                 _rule((_atom("q", "?x", "?x"),), "p", "?x", "?x"))
        proof = (ProofStep(1, (), _atom("p", "a", "a")),
                 ProofStep(0, (0,), _atom("q", "a", "a")))
        assert verify_proof(world, _atom("q", "a", "a"), proof) is False

    def test_invalid_irrelevant_step_before_valid_part_is_false(self):
        world = (_fact("p", "a", "b"), _fact("q", "a", "b"))
        proof = (ProofStep(0, (), _atom("p", "a", "c")),
                 ProofStep(1, (), _atom("q", "a", "b")))
        assert verify_proof(world, _atom("q", "a", "b"), proof) is False


class TestNoAnswerPeeking:
    """The verifier must follow the submitted premise references exactly.

    World (T0006 §4 C group): fact 0 p(a,b) and two alternative q
    facts, q(b,c) (1) and q(d,c) (2); rule 3 joins them through the
    shared variable ?y.  Citing fact 1 yields r(a,c) with binding
    ?y=b.  The wrong proof cites 0 and 2: both fact citations are
    individually valid, but no single binding of the join unifies
    p(a,b), q(d,c) with head r(a,c) (?y=b vs ?y=d).  Failing on the
    rule binding — not on a forged fact or a wrong clause type — pins
    the submitted-referent contract.
    """

    def _world(self):
        return (_fact("p", "a", "b"),
                _fact("q", "b", "c"),
                _fact("q", "d", "c"),
                _rule((_atom("p", "?x", "?y"), _atom("q", "?y", "?z")),
                      "r", "?x", "?z"))

    def test_alternative_premise_path_is_true(self):
        world = self._world()
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("q", "b", "c")),
                 ProofStep(3, (0, 1), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is True

    def test_wrong_alternative_path_is_false(self):
        # Both fact citations are individually valid; the join shared
        # variable binds ?y=b (from p(a,b)) and ?y=d (from q(d,c)).
        # The verifier must not re-derive the answer from the other
        # legal fact; the submitted referent is final.
        world = self._world()
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(2, (), _atom("q", "d", "c")),
                 ProofStep(3, (0, 1), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is False

    def test_guard_probe_lazy_fact_checker_is_insufficient(self):
        # A verifier that checks fact steps against the world and rule
        # steps only structurally (reference count, referent range)
        # accepts the wrong-binding proof above.  The real verifier
        # discriminates it through the join binding; an outright forged
        # fact is caught even by the lazy probe.
        world = self._world()
        query = _atom("r", "a", "c")
        correct = (ProofStep(0, (), _atom("p", "a", "b")),
                   ProofStep(1, (), _atom("q", "b", "c")),
                   ProofStep(3, (0, 1), query))
        wrong = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(2, (), _atom("q", "d", "c")),
                 ProofStep(3, (0, 1), query))
        forged = (ProofStep(0, (), _atom("p", "a", "c")),
                  ProofStep(1, (), _atom("q", "b", "c")),
                  ProofStep(3, (0, 1), query))

        def lazy_clause_checker(clauses, steps, goal):
            """Fact steps checked against the world; rule steps
            structural only (reference count, referent range)."""
            if not steps:
                return False
            for i, step in enumerate(steps):
                clause = clauses[step.clause_index]
                if len(clause.body) == 0:
                    if (step.premise_steps
                            or step.conclusion != clause.head):
                        return False
                elif (len(step.premise_steps) != len(clause.body)
                      or any(not (0 <= r < i)
                             for r in step.premise_steps)):
                    return False
            return steps[-1].conclusion == goal

        assert lazy_clause_checker(world, correct, query) is True
        assert lazy_clause_checker(world, wrong, query) is True
        assert lazy_clause_checker(world, forged, query) is False
        assert verify_proof(world, query, correct) is True
        assert verify_proof(world, query, wrong) is False
        assert verify_proof(world, query, forged) is False


class TestStructuralInvariance:
    def test_clause_reordering_with_remapped_indices_is_true(self):
        # Same clauses as the main example, order (JOIN, r1-fact, r2-fact, INV).
        join = _rule((_atom("r1", "?x", "?y"), _atom("r2", "?y", "?z")),
                     "r3", "?x", "?z")
        inv = _rule((_atom("r3", "?x", "?y"),), "r4", "?y", "?x")
        world = (join, _fact("r1", "a", "b"), _fact("r2", "b", "c"), inv)
        proof = (ProofStep(1, (), _atom("r1", "a", "b")),
                 ProofStep(2, (), _atom("r2", "b", "c")),
                 ProofStep(0, (0, 1), _atom("r3", "a", "c")),
                 ProofStep(3, (2,), _atom("r4", "c", "a")))
        assert verify_proof(world, _atom("r4", "c", "a"), proof) is True

    def _join_world(self, rule):
        return (_fact("p", "a", "b"), _fact("q", "b", "c"), rule)

    def test_body_swap_synced_with_reference_swap_is_true(self):
        rule_body_first = _rule((_atom("q", "?y", "?z"),
                                 _atom("p", "?x", "?y")), "r", "?x", "?z")
        world = self._join_world(rule_body_first)
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("q", "b", "c")),
                 ProofStep(2, (1, 0), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is True

    def test_reference_swap_without_body_swap_is_false(self):
        rule_p_first = _rule((_atom("p", "?x", "?y"),
                              _atom("q", "?y", "?z")), "r", "?x", "?z")
        world = self._join_world(rule_p_first)
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("q", "b", "c")),
                 ProofStep(2, (1, 0), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is False

    def test_renamed_predicates_entities_and_variables_is_true(self):
        # Bijective rename of a world+proof+query is still valid: every
        # predicate, entity and variable of the S4.2 main example is
        # replaced consistently everywhere (facts, rule bodies and
        # heads, proof steps, query).  Shared variables (?y in r1/r2 ->
        # ?v in s1/s2) and head argument positions are preserved, so
        # the renamed proof must still verify.
        clauses, proof, query = _main_example()

        def rename(token):
            for old, new in (("r1", "s1"), ("r2", "s2"), ("r3", "s3"),
                             ("r4", "s4"), ("a", "alpha"),
                             ("b", "beta"), ("c", "gamma"),
                             ("?x", "?u"), ("?y", "?v"), ("?z", "?w")):
                if token == old:
                    return new
            raise AssertionError(
                f"unexpected token in main example: {token!r}"
            )

        def rename_atom(atom):
            return Atom(rename(atom.pred),
                        tuple(rename(a) for a in atom.args))

        renamed_clauses = tuple(
            Clause(tuple(rename_atom(a) for a in c.body),
                   rename_atom(c.head))
            for c in clauses
        )
        renamed_proof = tuple(
            ProofStep(s.clause_index, s.premise_steps,
                      rename_atom(s.conclusion))
            for s in proof
        )
        renamed_query = rename_atom(query)

        # Sanity: the rename changed the query tokens and did not
        # collide with the original names.
        assert renamed_query.pred == "s4"
        assert all(t not in ("a", "b", "c", "?x", "?y", "?z")
                   for t in renamed_query.args)
        assert verify_proof(renamed_clauses, renamed_query,
                            renamed_proof) is True

    def test_inputs_frozen_and_stateless_across_calls(self):
        clauses, proof, query = _main_example()
        before = [hash(c) for c in clauses] + [hash(s) for s in proof]
        assert verify_proof(clauses, query, proof, max_steps=4) is True

        # A False proof in between must not leak any binding state.
        bad = (ProofStep(0, (), _atom("r1", "a", "c")),
               ProofStep(1, (), _atom("r2", "b", "c")))
        assert verify_proof(clauses, _atom("r2", "b", "c"), bad) is False

        assert verify_proof(clauses, query, proof, max_steps=4) is True
        after = [hash(c) for c in clauses] + [hash(s) for s in proof]
        assert before == after
        for clause in clauses:
            with pytest.raises(dataclasses.FrozenInstanceError):
                clause.body = ()
        for step in proof:
            with pytest.raises(dataclasses.FrozenInstanceError):
                step.clause_index = 0
        assert ProofStep(0, (), _atom("r1", "a", "b")) == proof[0]
        assert hash(ProofStep(0, (), _atom("r1", "a", "b"))) == hash(proof[0])
        assert type(verify_proof(clauses, query, proof)) is bool


STEP_CASES = (
    "clause-index-bool", "clause-index-negative",
    "clause-index-huge-negative", "clause-index-float",
    "clause-index-str", "clause-index-none",
    "premise-steps-list", "premise-steps-set", "premise-steps-too-many",
    "premise-ref-bool", "premise-ref-negative",
    "premise-ref-huge-negative", "premise-ref-float",
    "premise-ref-str", "premise-ref-none",
    "conclusion-str", "conclusion-int", "conclusion-none",
    "conclusion-non-ground",
)


def _make_bad_step(kind):
    large = 10 ** 5000
    kwargs = dict(clause_index=0, premise_steps=(),
                  conclusion=_atom("q", "a", "a"))
    if kind.startswith("clause-index-"):
        value = {"bool": True, "negative": -1, "huge-negative": -large,
                 "float": 1.5, "str": "0", "none": None}
        kwargs["clause_index"] = value[kind[len("clause-index-"):]]
    elif kind == "premise-steps-list":
        kwargs["premise_steps"] = [0]
    elif kind == "premise-steps-set":
        kwargs["premise_steps"] = {0, 1}
    elif kind == "premise-steps-too-many":
        kwargs["premise_steps"] = (0, 0, 0)
    elif kind.startswith("premise-ref-"):
        value = {"bool": True, "negative": -1, "huge-negative": -large,
                 "float": 2.5, "str": "0", "none": None}
        kwargs["premise_steps"] = (value[kind[len("premise-ref-"):]],)
    elif kind == "conclusion-str":
        kwargs["conclusion"] = "atom"
    elif kind == "conclusion-int":
        kwargs["conclusion"] = 42
    elif kind == "conclusion-none":
        kwargs["conclusion"] = None
    elif kind == "conclusion-non-ground":
        kwargs["conclusion"] = _atom("q", "?x", "a")
    return kwargs


def _step_error_expectation(kind):
    """Return (field_path, reason_fragment, got_fragment_or_None)."""
    prefixes = (
        ("clause-index-", "proof_step.clause_index"),
        ("premise-ref-", "proof_step.premise_steps[0]"),
        ("premise-steps-", "proof_step.premise_steps"),
        ("conclusion-", "proof_step.conclusion"),
    )
    for prefix, field in prefixes:
        if kind.startswith(prefix):
            sub = kind[len(prefix):]
            break
    else:
        raise AssertionError(kind)
    got = {"bool": "bool", "negative": "int", "huge-negative": "int",
           "float": "float", "str": "str", "int": "int",
           "none": "NoneType"}
    if field == "proof_step.premise_steps":
        if sub == "list":
            return field, "tuple", "got list"
        if sub == "set":
            return field, "tuple", "got set"
        if sub == "too-many":
            return field, "at most 2", None
        raise AssertionError(kind)
    if field == "proof_step.conclusion":
        if sub in got:
            return field, "Atom", "got " + got[sub]
        if sub == "non-ground":
            return field, "ground Atom", None
        raise AssertionError(kind)
    return field, "non-bool non-negative integer", "got " + got[sub]


class TestDiagnosticsAndTypes:
    @pytest.mark.parametrize("kind", STEP_CASES)
    def test_proof_step_field_validation(self, int_limit_4300, kind):
        with pytest.raises(LogicValidationError) as exc:
            ProofStep(**_make_bad_step(kind))
        field, reason, got = _step_error_expectation(kind)
        message = str(exc.value)
        assert field in message
        assert reason in message
        if got is not None:
            assert got in message

    def _verify_base(self):
        clauses = (_fact("p", "a", "a"),)
        proof = (ProofStep(0, (), _atom("p", "a", "a")),)
        query = _atom("p", "a", "a")
        return clauses, proof, query

    def test_clauses_must_be_tuple(self):
        clauses, proof, query = self._verify_base()
        with pytest.raises(LogicValidationError) as exc:
            verify_proof([clauses[0]], query, proof)
        message = str(exc.value)
        assert "verify.clauses" in message
        assert "tuple" in message
        assert "got list" in message

    def test_clause_member_must_be_clause(self):
        clauses, proof, query = self._verify_base()
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(clauses + ("bogus",), query, proof)
        message = str(exc.value)
        assert "verify.clauses[1]" in message
        assert "Clause" in message
        assert "got str" in message

    @pytest.mark.parametrize(
        "bad_query", (42, "q"), ids=["int", "str"])
    def test_query_must_be_atom(self, bad_query):
        clauses, proof, _ = self._verify_base()
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(clauses, bad_query, proof)
        message = str(exc.value)
        assert "verify.query" in message
        assert "Atom" in message

    def test_query_huge_int_reports_type_name_only(self, int_limit_4300):
        large = 10 ** 5000
        clauses, proof, _ = self._verify_base()
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(clauses, large, proof)
        message = str(exc.value)
        assert "verify.query" in message
        assert "Atom" in message
        assert "got int" in message

    def test_query_must_be_ground(self):
        clauses, proof, _ = self._verify_base()
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(clauses, _atom("p", "?x", "b"), proof)
        message = str(exc.value)
        assert "verify.query" in message
        assert "ground" in message

    def test_proof_must_be_tuple(self):
        clauses, proof, query = self._verify_base()
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(clauses, query, list(proof))
        message = str(exc.value)
        assert "verify.proof" in message
        assert "tuple" in message
        assert "got list" in message

    def test_proof_member_must_be_proof_step(self):
        clauses, proof, query = self._verify_base()
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(clauses, query, proof + ("bogus",))
        message = str(exc.value)
        assert "verify.proof[1]" in message
        assert "ProofStep" in message
        assert "got str" in message

    MAX_STEPS_KINDS = ("zero", "negative", "huge-negative", "bool", "float",
                       "str", "none")

    @pytest.mark.parametrize("kind", MAX_STEPS_KINDS)
    def test_max_steps_validation(self, int_limit_4300, kind):
        large = 10 ** 5000
        value = {"zero": 0, "negative": -1, "huge-negative": -large,
                 "bool": True, "float": 1.5, "str": "10", "none": None}
        clauses, proof, query = self._verify_base()
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(clauses, query, proof, max_steps=value[kind])
        message = str(exc.value)
        assert "verify.max_steps" in message
        assert "non-bool positive integer" in message
        expected_type = {"zero": "int", "negative": "int",
                         "huge-negative": "int", "bool": "bool",
                         "float": "float", "str": "str",
                         "none": "NoneType"}[kind]
        assert "got " + expected_type in message

    def test_invalid_arguments_not_skipped_on_empty_inputs(self):
        with pytest.raises(LogicValidationError) as exc1:
            verify_proof("not-a-tuple", _atom("p", "a", "a"), (),
                         max_steps=10)
        assert "verify.clauses" in str(exc1.value)
        with pytest.raises(LogicValidationError) as exc2:
            verify_proof((), _atom("p", "a", "a"), (), max_steps="10")
        assert "verify.max_steps" in str(exc2.value)

    def test_later_bad_member_reported_despite_invalid_earlier_semantics(self):
        clauses = (_fact("p", "a", "b"),)
        proof = (ProofStep(0, (), _atom("p", "a", "c")), "bogus")
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(clauses, _atom("p", "a", "c"), proof)
        message = str(exc.value)
        assert "verify.proof[1]" in message
        assert "ProofStep" in message


class TestStepLimit:
    def test_exact_limit_passes(self):
        clauses, proof, query = _main_example()
        assert verify_proof(clauses, query, proof, max_steps=4) is True

    def test_one_below_limit_raises_not_false(self):
        clauses, proof, query = _main_example()
        with pytest.raises(ProofLimitError) as exc:
            verify_proof(clauses, query, proof, max_steps=3)
        message = str(exc.value)
        assert "verify.max_steps" in message
        assert "exceeds" in message

    def test_limit_counts_repeated_and_irrelevant_steps(self):
        world = (_fact("r1", "a", "b"), _fact("r2", "b", "c"),
                 _rule((_atom("r1", "?x", "?y"), _atom("r2", "?y", "?z")),
                       "r3", "?x", "?z"),
                 _rule((_atom("r3", "?x", "?y"),), "r4", "?y", "?x"),
                 _fact("s", "a", "a"))
        proof = (ProofStep(0, (), _atom("r1", "a", "b")),
                 ProofStep(1, (), _atom("r2", "b", "c")),
                 ProofStep(4, (), _atom("s", "a", "a")),
                 ProofStep(2, (0, 1), _atom("r3", "a", "c")),
                 ProofStep(2, (0, 1), _atom("r3", "a", "c")),
                 ProofStep(3, (3,), _atom("r4", "c", "a")))
        query = _atom("r4", "c", "a")
        with pytest.raises(ProofLimitError):
            verify_proof(world, query, proof, max_steps=5)
        assert verify_proof(world, query, proof, max_steps=6) is True

    def test_single_fact_step_at_limit_one(self):
        clauses = (_fact("p", "a", "a"),)
        proof = (ProofStep(0, (), _atom("p", "a", "a")),)
        assert verify_proof(clauses, _atom("p", "a", "a"), proof,
                            max_steps=1) is True

    def test_large_positive_max_steps_accepted(self, int_limit_4300):
        large = 10 ** 5000
        clauses = (_fact("p", "a", "a"),)
        proof = (ProofStep(0, (), _atom("p", "a", "a")),)
        assert verify_proof(clauses, _atom("p", "a", "a"), proof,
                            max_steps=large) is True

    def test_proof_limit_error_is_runtime_error(self):
        assert issubclass(ProofLimitError, RuntimeError)


class TestErrorPriority:
    """Diagnoses run in a fixed order; the earlier one wins.

    These pin the observable priority (not an over-limit proof
    "beating any arbitrary exception"): budget-exceeded runs after all
    top-level input-type validation and before the per-member scan, and
    the premise-count check runs before per-reference member type
    checks.
    """

    def test_budget_exceeded_before_proof_member_scan(self):
        world = (_fact("p", "a", "b"),)
        query = _atom("p", "a", "b")
        # Two members; the second is not a ProofStep.
        proof = (ProofStep(0, (), query), "not-a-step")
        with pytest.raises(ProofLimitError) as limit_exc:
            verify_proof(world, query, proof, max_steps=1)
        message = str(limit_exc.value)
        assert "verify.max_steps" in message
        assert "exceeds" in message
        # With a budget of two, the length check passes and the
        # member scan reports the invalid second step instead.
        with pytest.raises(LogicValidationError) as member_exc:
            verify_proof(world, query, proof, max_steps=2)
        message = str(member_exc.value)
        assert "verify.proof[1]" in message
        assert "ProofStep" in message

    def test_non_atom_query_before_budget_exceeded(self):
        world = (_fact("p", "a", "b"),)
        good = ProofStep(0, (), _atom("p", "a", "b"))
        # The proof has two steps and the budget is one, but the
        # query type check runs before the budget check.
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(world, 42, (good, good), max_steps=1)
        message = str(exc.value)
        assert "verify.query" in message
        assert "Atom" in message

    def test_premise_count_before_premise_member_type(self):
        # Three references is rejected as too many before the float
        # third element is type-checked.
        with pytest.raises(LogicValidationError) as exc:
            ProofStep(0, (0, 0, 1.5), _atom("q", "a", "a"))
        message = str(exc.value)
        assert "at most 2" in message
        assert "premise_steps[2]" not in message


LARGE_DIGIT_VALUE = 10 ** 5000


@pytest.fixture
def int_limit_4300():
    """Pin the interpreter's int<->str digit limit to its maximum value.

    ``10**5000`` is above that 4300-digit limit, so a diagnostic that
    stringifies the value would raise ValueError and abort the test.
    Restored unconditionally.
    """
    previous = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        assert sys.get_int_max_str_digits() == 4300
        yield
    finally:
        sys.set_int_max_str_digits(previous)


class TestHugeIntAtDigitLimit4300:
    """Huge ``int`` misuse at ``sys.set_int_max_str_digits(4300)``.

    Diagnostics must name the field path and the ``int`` type without
    converting the huge value to a string, or the interpreter aborts
    the test with ``ValueError: Exceeds the limit ... for integer
    string conversion``.
    """

    def _world(self):
        return (_fact("p", "a", "b"),)

    def _query(self):
        return _atom("p", "a", "b")

    def test_negative_huge_clause_index_raises(self, int_limit_4300):
        with pytest.raises(LogicValidationError) as exc:
            ProofStep(-LARGE_DIGIT_VALUE, (), self._query())
        assert str(exc.value) == (
            "proof_step.clause_index must be a non-bool non-negative "
            "integer, got int"
        )

    def test_negative_huge_premise_reference_raises(
        self, int_limit_4300
    ):
        with pytest.raises(LogicValidationError) as exc:
            ProofStep(0, (-LARGE_DIGIT_VALUE,), self._query())
        assert str(exc.value) == (
            "proof_step.premise_steps[0] must be a non-bool "
            "non-negative integer, got int"
        )

    def test_huge_int_conclusion_raises(self, int_limit_4300):
        with pytest.raises(LogicValidationError) as exc:
            ProofStep(0, (), LARGE_DIGIT_VALUE)
        assert str(exc.value) == ("proof_step.conclusion must be an "
                                  "Atom, got int")

    def test_huge_clause_member_raises(self, int_limit_4300):
        with pytest.raises(LogicValidationError) as exc:
            verify_proof((LARGE_DIGIT_VALUE,), self._query(), ())
        assert str(exc.value) == (
            "verify.clauses[0] must be a Clause, got int"
        )

    def test_huge_proof_member_raises(self, int_limit_4300):
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(self._world(), self._query(),
                         (LARGE_DIGIT_VALUE,))
        assert str(exc.value) == ("verify.proof[0] must be a "
                                  "ProofStep, got int")

    def test_huge_query_raises(self, int_limit_4300):
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(self._world(), LARGE_DIGIT_VALUE, ())
        assert str(exc.value) == "verify.query must be an Atom, got int"

    def test_negative_huge_max_steps_raises(self, int_limit_4300):
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(self._world(), self._query(), (),
                         max_steps=-LARGE_DIGIT_VALUE)
        assert str(exc.value) == (
            "verify.max_steps must be a non-bool positive integer, got int"
        )

    def test_positive_huge_clause_index_verifies_false(
        self, int_limit_4300
    ):
        # Constructible (non-negative int); verification rejects the
        # out-of-range reference without raising.
        step = ProofStep(LARGE_DIGIT_VALUE, (), self._query())
        assert verify_proof(self._world(), self._query(),
                            (step,)) is False

    def test_positive_huge_premise_reference_verifies_false(
        self, int_limit_4300
    ):
        # Constructible; on a zero-premise fact clause the single
        # out-of-range reference is simply the wrong reference count,
        # so verification returns False without raising.
        step = ProofStep(0, (LARGE_DIGIT_VALUE,), self._query())
        assert verify_proof(self._world(), self._query(),
                            (step,)) is False

    def test_positive_huge_max_steps_accepted(self, int_limit_4300):
        step = ProofStep(0, (), self._query())
        assert verify_proof(self._world(), self._query(), (step,),
                            max_steps=LARGE_DIGIT_VALUE) is True


_ISO_SNIPPET = r'''
import sys


_BLOCKED_ROOTS = (
    "torch",
    "yaml",
    "kmesh.logic.engine",
    "kmesh.logic.reference_engine",
)


def _is_blocked(fullname):
    return any(
        fullname == root or fullname.startswith(root + ".")
        for root in _BLOCKED_ROOTS
    )


class _Guard:
    def find_spec(self, fullname, path=None, target=None):
        if _is_blocked(fullname):
            raise ImportError("blocked import: " + fullname)
        return None


sys.meta_path.insert(0, _Guard())

from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.types import Atom, Clause

def _run_case(clauses, query, proof):
    # Each verify call receives a fresh list of steps, as an external
    # prover would build one per submission.
    return verify_proof(clauses, query, tuple(proof))


clauses_fact = (Clause((), Atom("p", ("a", "a"))),)
query_fact = Atom("p", ("a", "a"))
proof_fact = (ProofStep(0, (), Atom("p", ("a", "a"))),)
assert _run_case(clauses_fact, query_fact, proof_fact) is True

clauses_copy = (
    Clause((), Atom("p", ("a", "a"))),
    Clause((Atom("p", ("?x", "?x")),), Atom("q", ("?x", "?x"))),
)
proof_copy = (
    ProofStep(0, (), Atom("p", ("a", "a"))),
    ProofStep(1, (0,), Atom("q", ("a", "a"))),
    ProofStep(0, (), Atom("p", ("a", "a"))),
)
assert _run_case(clauses_copy, query_fact, proof_copy) is True
assert _run_case(clauses_fact, query_fact, proof_fact) is True

# The proof-only import must not have pulled in a solver or a heavy
# third-party stack.  Scan the whole module table so blocked submodules
# (e.g. "kmesh.logic.engine.something") are caught, not just the roots.
leaked = [name for name in sys.modules if _is_blocked(name)]
assert not leaked, leaked
print("T0006-ISO-OK")
'''


class TestGuardSelfCheck:
    """The module-level guard must really refuse solver imports.

    A broken guard (e.g. comparing the ``parts[:3]`` list against a
    tuple of tuples) would silently let these imports through; these
    tests turn that silent failure into a test failure.  The autouse
    fixture removes any previously imported solver module for the test
    duration, so the import below must go through the guard.
    """

    def test_guard_actually_blocks_engine_import(self):
        with pytest.raises(ImportError):
            importlib.import_module("kmesh.logic.engine")

    def test_guard_actually_blocks_reference_engine_import(self):
        with pytest.raises(ImportError):
            importlib.import_module("kmesh.logic.reference_engine")


class TestIsolation:
    def test_proof_module_isolation_in_clean_subprocess(self):
        result = subprocess.run(
            [sys.executable, "-c", _ISO_SNIPPET],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        assert result.returncode == 0, result.stderr[-2000:]
        assert "T0006-ISO-OK" in result.stdout

    def test_logic_package_init_has_no_imports(self):
        init_path = REPO_ROOT / "src" / "kmesh" / "logic" / "__init__.py"
        for line in init_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            assert not stripped.startswith("import "), stripped
            assert not stripped.startswith("from "), stripped
