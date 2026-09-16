"""Bounded Codex review probes; no product or submitted-test edits."""
import json
import sys
from unittest.mock import patch

from kmesh.logic import engine
from kmesh.logic.types import Atom, Clause


def fact(pred, x, y):
    return Clause((), Atom(pred, (x, y)))


def streaming(n):
    world = tuple(fact("p", f"a{i}", f"a{i}") for i in range(n)) + tuple(
        fact("q", f"b{i}", f"b{i}") for i in range(n)
    ) + (Clause((Atom("p", ("?x", "?x")), Atom("q", ("?y", "?y"))),
                Atom("out", ("k", "k"))),)
    observed = {"n": n, "checks": 0, "first_head_after_checks": None,
                "live_match_results": 0, "peak_live_match_results": 0}
    original_match = engine._match
    original_instantiate = engine._instantiate

    class TrackedBinding(dict):
        def __init__(self, values):
            super().__init__(values)
            observed["live_match_results"] += 1
            observed["peak_live_match_results"] = max(
                observed["peak_live_match_results"], observed["live_match_results"]
            )

        def __del__(self):
            observed["live_match_results"] -= 1

    def match(*args):
        observed["checks"] += 1
        result = original_match(*args)
        return None if result is None else TrackedBinding(result)

    def instantiate(*args):
        if observed["first_head_after_checks"] is None:
            observed["first_head_after_checks"] = observed["checks"]
        return original_instantiate(*args)

    with patch.object(engine, "_match", match), patch.object(engine, "_instantiate", instantiate):
        result = engine.indexed_closure(world)
    expected = frozenset(c.head for c in world if not c.body) | {Atom("out", ("k", "k"))}
    assert result == expected
    assert observed["checks"] == 2 * (n + n * n)
    observed["closure_size"] = len(result)
    # All candidates match. Nested streaming produces the first head after
    # the first p and q checks, before scanning later p candidates.
    observed["streaming_contract_pass"] = observed["first_head_after_checks"] == 2
    return observed


def intersection():
    initial = (fact("p", "a", "b"), fact("p", "c", "d"),
               fact("q", "a", "b"), fact("q", "b", "a"), fact("q", "c", "e"))
    rule = Clause((Atom("p", ("?x", "?y")), Atom("q", ("?x", "?y"))),
                  Atom("inter", ("?x", "?y")))
    expected = frozenset(c.head for c in initial) | {Atom("inter", ("a", "b"))}
    actual = engine.indexed_closure(initial + (rule,))
    assert actual == expected
    return {"manual_intersection": "PASS", "closure_size": len(actual),
            "expected_new_atom": "inter(a,b)", "uses_reference_solver": False}


if __name__ == "__main__":
    if sys.argv[1:] == ["streaming"]:
        observations = [streaming(n) for n in (2, 32)]
        print(json.dumps(observations, indent=2))
        raise SystemExit(0 if all(r["streaming_contract_pass"] for r in observations) else 1)
    if sys.argv[1:] == ["intersection"]:
        print(json.dumps(intersection(), indent=2))
    else:
        raise SystemExit("expected streaming or intersection")
