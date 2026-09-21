"""Minimum proof depth for one ground query in an acyclic clause world.

This module computes, after one complete T0008 enumeration of the whole
world, the smallest number of reasoning layers any direct-derivation
proof of the query needs.  ``minimum_proof_depth`` validates its own
input first (clauses container, member clauses, query type and
groundness, both budgets — in that fixed order), then calls
``enumerate_derivations`` exactly once with the caller's clauses and
budget values unchanged, and finally performs a single forward pass over
the dependency-ordered record sequence:

- a record with no premise (a fact) has candidate depth 0;
- a record with premises has candidate depth
  ``1 + max(the minimum depth of each premise)``.  The relationship
  topological order guarantees every premise's sources have already been
  processed, so a plain dictionary lookup is used and a missing premise
  is never defaulted;
- whenever several records derive the same conclusion, only the smallest
  depth is kept — the first or last source alone is not authoritative;
- after the whole sequence has been scanned, the query's depth is
  returned, or ``None`` when no record derives it.

``None`` therefore means "not derivable after a successful complete
enumeration of this finite world"; validation errors and
``DerivationLimitError`` propagate unchanged and can never become
``None``.  A fact is depth 0, and the result (including 0) is always a
true ``int``.  The input is not mutated and repeated calls agree.

The new single-pass dynamic program is O(R) in time and O(A) in
auxiliary space, where R is the number of ground derivation records and
A the number of distinct ground Atoms among them.  The full public call
still pays T0008's matching cost and stores all R records; nothing here
unfolds proof trees, iterates to a fixed point, recurses, or depends on
step counts, topological positions, or proof-tree quantities.

Depth is an offline audit metric for inference-depth grouping.  It is
never fed to any model as tokens, embeddings, or routing/prediction
input.  Standard library plus the accepted logic types and direct
derivations only: no heavy runtime dependency, no file access, no I/O, no
proof or enumeration module import, no closure solver, no global mutable state.
"""

from __future__ import annotations

from .derivations import enumerate_derivations
from .types import Atom, Clause, LogicValidationError

__all__ = ["minimum_proof_depth"]


def minimum_proof_depth(
    clauses: tuple[Clause, ...],
    query: Atom,
    *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
) -> int | None:
    """Minimum reasoning-layer count for a ground query, or ``None``.

    ``clauses`` is a tuple of ``Clause``; ``query`` is a ground
    ``Atom``; both budgets are non-bool positive integers (arbitrarily
    large values are accepted).  Validation raises the existing
    ``LogicValidationError`` with diagnostics that report only field
    positions and type names, never the repr of an unchecked value, and
    a non-tuple container is not consumed.  On full success, ``int``
    (``0`` for a fact) or ``None`` for a query the world cannot derive.

    The whole world is always enumerated before any result is returned:
    even a fact query, an absent query, or a world with an unrelated
    component must first survive T0008's cycle check and budgets.
    T0008's ``LogicValidationError`` (including the fixed cyclic-dependency
    message) and ``DerivationLimitError`` propagate unchanged.
    """
    if not isinstance(clauses, tuple):
        raise LogicValidationError(
            f"depth.clauses must be a tuple of Clause; "
            f"got {type(clauses).__name__}")
    for index, item in enumerate(clauses):
        if not isinstance(item, Clause):
            raise LogicValidationError(
                f"depth.clauses[{index}] must be a Clause; "
                f"got {type(item).__name__}")
    if not isinstance(query, Atom):
        raise LogicValidationError(
            f"depth.query must be an Atom; got {type(query).__name__}")
    if not query.is_ground:
        raise LogicValidationError("depth.query must be a ground Atom")
    for value, name in (
        (max_fact_checks, "max_fact_checks"),
        (max_derivations, "max_derivations"),
    ):
        if type(value) is not int or value <= 0:
            raise LogicValidationError(
                f"depth.{name} must be a non-bool positive integer; "
                f"got {type(value).__name__}")
    records = enumerate_derivations(
        clauses, max_fact_checks=max_fact_checks,
        max_derivations=max_derivations)
    depths: dict[Atom, int] = {}
    for record in records:
        if record.premises:
            candidate = 1 + max(depths[premise] for premise in record.premises)
        else:
            candidate = 0
        previous = depths.get(record.conclusion)
        if previous is None or candidate < previous:
            depths[record.conclusion] = candidate
    result = depths.get(query)
    return None if result is None else result
