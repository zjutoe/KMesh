"""Codex acceptance probes; synthetic fixtures, not a second solver."""
import importlib.util
from pathlib import Path

from kmesh.logic.reference_engine import ReferenceLimitError, reference_closure
from kmesh.logic.types import Atom as A, Clause as C, LogicValidationError


def exact_budget(name, clauses, budget, expected):
    assert reference_closure(clauses, max_rule_evaluations=budget) == frozenset(expected), name
    try:
        reference_closure(clauses, max_rule_evaluations=budget - 1)
    except ReferenceLimitError as exc:
        assert "reference.max_rule_evaluations" in str(exc), name
    else:
        raise AssertionError(f"{name}: expected limit error")
    print(f"PASS {name}: {budget} succeeds, {budget - 1} fails")


# No facts is not permission to bypass candidate checks, including ground rules.
empty_ground = (
    C((A("p", ("a", "a")),), A("q", ("a", "a"))),
    C((A("q", ("a", "a")),), A("r", ("a", "a"))),
)
exact_budget("no-facts-ground-rules", empty_ground, 2, ())

# A zero-variable rule still has one binding per synchronous round.
ground_rule = (C((), A("p", ("a", "a"))), empty_ground[0])
exact_budget("zero-variable-rule", ground_rule, 2, (A("p", ("a", "a")), A("q", ("a", "a"))))

# A constant appearing only in a rule body still belongs to the fixed domain.
body_constant = (
    C((), A("p", ("a", "a"))),
    C((A("p", ("?x", "k")),), A("q", ("?x", "?x"))),
)
exact_budget("body-only-constant-domain", body_constant, 2, (A("p", ("a", "a")),))

# Body-only variables must all be enumerated even when the head is ground.
ground_head = (
    C((), A("p", ("a", "b"))),
    C((A("p", ("?x", "?y")),), A("q", ("a", "b"))),
)
exact_budget("body-only-variables-budget", ground_head, 8, (A("p", ("a", "b")), A("q", ("a", "b"))))

# Several successful bindings must all contribute, with consistent middle terms.
facts = (A("p", ("a", "b")), A("p", ("a", "c")), A("q", ("b", "d")), A("q", ("c", "a")))
join = C((A("p", ("?x", "?y")), A("q", ("?y", "?z"))), A("r", ("?x", "?z")))
world = tuple(C((), atom) for atom in facts) + (join,)
exact_budget("multiple-join-bindings", world, 128, facts + (A("r", ("a", "d")), A("r", ("a", "a"))))
misbound = (C((), A("p", ("a", "b"))), C((), A("q", ("c", "a"))), join)
assert reference_closure(misbound) == frozenset((misbound[0].head, misbound[1].head))
print("PASS inconsistent-join-binding")

# Exercise Pi's actual assertions against a deliberately reason-free error.
# This replaces only the test module's callable in memory; no file is edited.
repo = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("t0004_submitted_tests", repo / "tests/test_reference_engine.py")
submitted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submitted)
message = "reference.max_rule_evaluations: invalid type or size"


def reason_free_error(*args, **kwargs):
    raise LogicValidationError(message)


original = submitted.reference_closure
submitted.reference_closure = reason_free_error
try:
    for budget, reason in ((0, "positive"), (-1, "positive"), (1.5, "float"), ("2", "str")):
        assert reason not in message
        submitted.test_invalid_budget_rejected_with_field_and_reason(budget, reason)
        print(f"REPRODUCED test false positive: missing complete reason {reason!r}, budget type {type(budget).__name__}")
finally:
    submitted.reference_closure = original

print("SUMMARY: 6 solver probes passed; 4 reason-assertion false positives reproduced")
