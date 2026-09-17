"""Tests for the independent given-proof verifier (T0006).

All expected results are hand-computed from the fixtures below; no closure
solver is imported here, and assertions target the documented behaviour of
``ProofStep`` and ``verify_proof`` (field paths, reason fragments, and the
True/False/ProofLimitError boundary), not solver output.
"""

from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path

import pytest

from kmesh.logic.proof import ProofLimitError, ProofStep, verify_proof
from kmesh.logic.types import Atom, Clause, LogicValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _forbid_solver_and_blocked_imports(monkeypatch):
    """Keep every test free of torch/yaml/solver modules."""
    for name in ("kmesh.logic.engine", "kmesh.logic.reference_engine"):
        sys.modules.pop(name, None)

    class _Guard:
        def find_spec(self, fullname, path, target=None):
            parts = fullname.split(".")
            blocked_root = parts[0] in ("torch", "yaml")
            solver = (
                len(parts) >= 3
                and parts[:3] in (("kmesh", "logic", "engine"),
                                  ("kmesh", "logic", "reference_engine"))
            )
            if blocked_root or solver:
                raise ImportError(f"test forbids importing {fullname}")
            return None

    sys.meta_path.insert(0, _Guard())
    try:
        yield
    finally:
        sys.meta_path.pop(0)


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

    def test_large_positive_clause_index_is_false(self):
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
        world = (_fact("p", "a", "b"), _fact("p", "b", "c"),
                 _rule((_atom("p", "?x", "?y"), _atom("p", "?y", "?z")),
                       "r", "?x", "?z"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(2, (0,), _atom("r", "a", "b")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is False

    def test_rule_with_too_many_premise_references_is_false(self):
        world = (_fact("p", "a", "b"), _fact("q", "a", "c"),
                 _rule((_atom("p", "?x", "?y"),), "r", "?y", "?x"))
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("q", "a", "c")),
                 ProofStep(2, (0, 1), _atom("r", "b", "a")))
        assert verify_proof(world, _atom("r", "b", "a"), proof) is False

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
    def _world(self):
        return (_fact("p", "a", "b"),
                _fact("p", "b", "c"),
                _fact("p", "d", "c"),
                _rule((_atom("p", "?x", "?y"), _atom("p", "?y", "?z")),
                      "r", "?x", "?z"))

    def test_alternative_premise_path_is_true(self):
        world = self._world()
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("p", "b", "c")),
                 ProofStep(3, (0, 1), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is True

    def test_wrong_alternative_path_is_false(self):
        world = self._world()
        proof = (ProofStep(0, (), _atom("p", "a", "b")),
                 ProofStep(1, (), _atom("p", "d", "c")),
                 ProofStep(2, (0, 1), _atom("r", "a", "c")))
        assert verify_proof(world, _atom("r", "a", "c"), proof) is False


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
        clauses = (Clause((), Atom("s1", ("x", "y"))),
                   Clause((), Atom("s2", ("y", "z"))),
                   Clause((Atom("s1", ("?u", "?v")),
                           Atom("s2", ("?w", "?t"))),
                          Atom("s3", ("?v", "?t"))),
                   Clause((Atom("s3", ("?m", "?n")),),
                          Atom("s4", ("?n", "?m"))))
        proof = (ProofStep(0, (), Atom("s1", ("x", "y"))),
                 ProofStep(1, (), Atom("s2", ("y", "z"))),
                 ProofStep(2, (0, 1), Atom("s3", ("y", "z"))),
                 ProofStep(3, (2,), Atom("s4", ("z", "y"))))
        assert verify_proof(clauses, Atom("s4", ("z", "y")), proof) is True

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
    def test_proof_step_field_validation(self, kind):
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

    def test_query_huge_int_reports_type_name_only(self):
        large = 10 ** 5000
        clauses, proof, _ = self._verify_base()
        with pytest.raises(LogicValidationError) as exc:
            verify_proof(clauses, large, proof)
        message = str(exc.value)
        assert "verify.query" in message
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
    def test_max_steps_validation(self, kind):
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

    def test_large_positive_max_steps_accepted(self):
        large = 10 ** 5000
        clauses = (_fact("p", "a", "a"),)
        proof = (ProofStep(0, (), _atom("p", "a", "a")),)
        assert verify_proof(clauses, _atom("p", "a", "a"), proof,
                            max_steps=large) is True

    def test_proof_limit_error_is_runtime_error(self):
        assert issubclass(ProofLimitError, RuntimeError)


_ISO_SNIPPET = r'''
import importlib.machinery
import sys


class _BlockedLoader:
    def create_module(self, spec):
        raise ImportError("blocked import: " + spec.name)

    def exec_module(self, module):
        raise ImportError("blocked import: " + module.__name__)


class _Guard:
    def find_spec(self, fullname, path=None, target=None):
        parts = fullname.split(".")
        if (parts[0] in ("torch", "yaml")
                or parts[:3] in (("kmesh", "logic", "engine"),
                                 ("kmesh", "logic", "reference_engine"))):
            return importlib.machinery.ModuleSpec(fullname, _BlockedLoader())
        return None


sys.meta_path.insert(0, _Guard())

from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.types import Atom, Clause

clauses = (
    Clause((), Atom("p", ("a", "a"))),
    Clause((Atom("p", ("?x", "?x")),), Atom("q", ("?x", "?x"))),
)
proof = (
    ProofStep(0, (), Atom("p", ("a", "a"))),
    ProofStep(1, (0,), Atom("q", ("a", "a"))),
)
assert verify_proof(clauses, Atom("q", ("a", "a")), proof) is True
blocked = ("kmesh.logic.engine", "kmesh.logic.reference_engine")
assert not any(name in sys.modules for name in blocked)
print("T0006-ISO-OK")
'''


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
