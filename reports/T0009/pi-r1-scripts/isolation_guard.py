"""T0009 isolation self-check, executed as ``python -c <this file>`` from the
repository root in a clean interpreter.

Blocks the four import roots (torch, yaml, and the two solver modules) with a
MetaPathFinder that raises ImportError, patches verify_proof with a sentinel,
runs one positive enumeration and one S-1 exhaustion, then verifies that no
blocked module is present in sys.modules. Prints ISOLATION PASS on success.
"""

import importlib.abc
import sys
from pathlib import Path

ROOTS = ("torch", "yaml", "kmesh.logic.engine", "kmesh.logic.reference_engine")


class T0009Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        for root in ROOTS:
            if name == root or name.startswith(root + "."):
                raise ImportError(f"blocked by T0009 isolation guard: {name}")
        return None


sys.meta_path.insert(0, T0009Blocker())

for _root in ROOTS:
    try:
        __import__(_root)
    except ImportError:
        continue
    raise AssertionError(f"self-check failed: {_root} is importable")

sys.path.insert(0, str(Path.cwd() / "src"))

import kmesh.logic.proof as proof_mod


def _sentinel(*_args, **_kwargs):
    raise AssertionError("proof.verify_proof was called by enumerate_proofs")


proof_mod.verify_proof = _sentinel

from kmesh.logic.proof import ProofStep
from kmesh.logic.proof_enumeration import (
    ProofEnumerationLimitError,
    enumerate_proofs,
)
from kmesh.logic.types import Atom, Clause


def _atom(pred, x, y):
    return Atom(pred, (x, y))


def _fact(pred, x, y):
    return Clause((), _atom(pred, x, y))


def _rule(*body, head):
    return Clause(tuple(body), head)


# P4 world (T0009 planning example).
clauses = (
    _fact("p", "a", "b"),
    _rule(_atom("p", "?x", "?y"), head=_atom("q", "?x", "?y")),
    _rule(_atom("p", "?x", "?y"), head=_atom("r", "?x", "?y")),
    _rule(
        _atom("q", "?x", "?y"),
        _atom("r", "?x", "?y"),
        head=_atom("s", "?x", "?y"),
    ),
)
expected = (
    (
        ProofStep(0, (), _atom("p", "a", "b")),
        ProofStep(1, (0,), _atom("q", "a", "b")),
        ProofStep(0, (), _atom("p", "a", "b")),
        ProofStep(2, (2,), _atom("r", "a", "b")),
        ProofStep(3, (1, 3), _atom("s", "a", "b")),
    ),
)

out = enumerate_proofs(
    clauses, _atom("s", "a", "b"),
    max_fact_checks=4, max_derivations=4, max_proof_steps=10,
)
assert out == expected, "positive enumeration output mismatch"

try:
    enumerate_proofs(
        clauses, _atom("s", "a", "b"),
        max_fact_checks=4, max_derivations=4, max_proof_steps=9,
    )
except ProofEnumerationLimitError as exc:
    assert str(exc) == (
        "proofs.max_proof_steps exhausted before enumeration completed"
    )
else:
    raise AssertionError("expected the S-1 call to exhaust")

blocked = [
    name
    for name in sys.modules
    if any(name == root or name.startswith(root + ".") for root in ROOTS)
]
assert not blocked, f"blocked modules present in sys.modules: {blocked}"

print("ISOLATION PASS")
