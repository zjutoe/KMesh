"""Immutable Atom and Clause types with construction-time static checks.

Shared representation for the forward-Horn knowledge fragments used later
by the solver, data construction, and content encoding. Facts are clauses
with an empty body; no separate Fact/Rule classes or role labels exist.

This layer validates only syntax and per-clause variable scope:

- ``pred`` and constants are ASCII identifiers ``[A-Za-z][A-Za-z0-9_]*``;
- variables are ``?`` followed by the same identifier;
- ``Atom`` is binary; no implicit conversion or renaming is applied;
- ``Clause`` has 0 to 2 premises and every head variable must occur in
  the body (an empty body therefore requires a ground head);
- objects are frozen and hashable; equality is structural (including
  argument direction and body order).

World-level E0 constraints (vocabulary membership, symbol counts,
generation templates, relation DAGs, duplicate data, proof audit) are
NOT checked here. Constructing a valid object does not make a world
valid. Standard library only: no torch, no YAML, no file access, no
global variable-binding state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_IDENTIFIER_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")


class LogicValidationError(ValueError):
    """Raised when an Atom or Clause violates a static constraint."""


def _validate_atom_pred(pred: object) -> None:
    if not isinstance(pred, str):
        raise LogicValidationError(
            f"atom.pred must be a string, got {type(pred).__name__}")
    if pred.startswith("?"):
        raise LogicValidationError(
            f"atom.pred must not start with '?': {pred!r}")
    if _IDENTIFIER_RE.fullmatch(pred) is None:
        raise LogicValidationError(
            f"atom.pred is not an ASCII identifier "
            f"([A-Za-z][A-Za-z0-9_]*): {pred!r}")


def _validate_atom_arg(index: int, value: object) -> None:
    where = f"atom.args[{index}]"
    if not isinstance(value, str):
        raise LogicValidationError(
            f"{where} must be a string constant or variable, "
            f"got {type(value).__name__}")
    if value.startswith("?"):
        if _IDENTIFIER_RE.fullmatch(value[1:]) is None:
            raise LogicValidationError(
                f"{where} is not a valid variable ('?' followed by an ASCII "
                f"identifier): {value!r}")
        return
    if _IDENTIFIER_RE.fullmatch(value) is None:
        raise LogicValidationError(
            f"{where} is not an ASCII identifier constant "
            f"([A-Za-z][A-Za-z0-9_]*): {value!r}")


@dataclass(frozen=True)
class Atom:
    """A binary predicate application ``pred(arg1, arg2)``.

    ``args`` must be a two-item tuple of constant names or variable names.
    Repeated arguments are allowed. ``variables`` returns the set of
    variable names including the ``?`` prefix; ``is_ground`` is True when
    no variable occurs.
    """

    pred: str
    args: tuple[str, str]

    def __post_init__(self) -> None:
        _validate_atom_pred(self.pred)
        if not isinstance(self.args, tuple):
            # The container is reported by type only: its members are
            # unvalidated and may not be representable.
            raise LogicValidationError(
                f"atom.args must be a tuple of two strings, "
                f"got {type(self.args).__name__}")
        if len(self.args) != 2:
            raise LogicValidationError(
                f"atom.args must have exactly 2 items, "
                f"got {len(self.args)}")
        for index, value in enumerate(self.args):
            _validate_atom_arg(index, value)

    @property
    def variables(self) -> frozenset[str]:
        """Variable names (including the ``?`` prefix) in this atom."""
        return frozenset(arg for arg in self.args if arg.startswith("?"))

    @property
    def is_ground(self) -> bool:
        """True when the atom contains no variables."""
        return not self.variables


@dataclass(frozen=True)
class Clause:
    """A forward-Horn clause ``body -> head``; an empty body is a fact.

    ``body`` must be a tuple of 0 to 2 Atoms; ``head`` must be an Atom.
    Every head variable must occur in the body of this clause (range
    restriction), so a fact (empty body) can only have a ground head.
    Body order and duplicates are preserved; premises are not reordered,
    renamed, or deduplicated.
    """

    body: tuple[Atom, ...]
    head: Atom

    def __post_init__(self) -> None:
        if not isinstance(self.head, Atom):
            raise LogicValidationError(
                f"clause.head must be an Atom, "
                f"got {type(self.head).__name__}")
        if not isinstance(self.body, tuple):
            raise LogicValidationError(
                f"clause.body must be a tuple of Atoms, "
                f"got {type(self.body).__name__}")
        if not 0 <= len(self.body) <= 2:
            raise LogicValidationError(
                f"clause.body must have 0, 1, or 2 premises, "
                f"got {len(self.body)}")
        for index, atom in enumerate(self.body):
            if not isinstance(atom, Atom):
                raise LogicValidationError(
                    f"clause.body[{index}] must be an Atom, "
                    f"got {type(atom).__name__}")
        bound = set()
        for atom in self.body:
            bound |= atom.variables
        unbound = self.head.variables - bound
        if unbound:
            names = ", ".join(f"'{name}'" for name in sorted(unbound))
            raise LogicValidationError(
                f"clause.head contains variables not bound in clause.body: "
                f"{names}")
