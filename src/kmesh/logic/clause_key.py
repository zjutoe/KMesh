"""Canonical content key for a single forward-Horn clause.

Implements the clause-identity contract: two well-formed ``Clause`` values
receive the same key if and only if they differ only by the internal
variable names and, for a two-premise body, the premise order. Predicates,
constant spellings, argument positions (direction) and duplicated premises
are all preserved. ``("c", "x")`` and ``("v", 0)`` are distinct.

This is a local structural operation on one clause. It does not solve world
isomorphism, proof uniqueness, motif counting, world deduplication or any
world-level audit, and it produces no serialised digest or Python hash.

Standard library plus ``kmesh.logic.types`` only. The ``kmesh.logic``
package ``__init__`` stays import-free.
"""

from __future__ import annotations

from kmesh.logic.types import Atom, Clause, LogicValidationError

__all__ = ["canonical_clause_key"]

_KEY_VERSION = "clause_key_v1"


def _term_key(term: str, numbering: dict[str, int]) -> tuple:
    """Encode a single argument string as a TermKey.

    A variable (``?`` prefix) is encoded by its first-occurrence number
    ``("v", n)``; a constant keeps its original spelling ``("c", s)``.
    Constants never consume a variable number.
    """
    if term.startswith("?"):
        number = numbering.setdefault(term, len(numbering))
        return ("v", number)
    return ("c", term)


def _atom_key(atom: Atom, numbering: dict[str, int]) -> tuple:
    """Encode a binary atom as an AtomKey under a numbering table."""
    return (
        atom.pred,
        _term_key(atom.args[0], numbering),
        _term_key(atom.args[1], numbering),
    )


def _candidate_key(head: Atom, body: tuple[Atom, ...]) -> tuple:
    """Full Key for one candidate body ordering.

    A fresh variable numbering is built by scanning head args left-to-right,
    then each candidate-body atom's args left-to-right; first occurrence gets
    0, 1, 2, ... and constants do not consume numbers.
    """
    numbering: dict[str, int] = {}
    head_key = (
        head.pred,
        _term_key(head.args[0], numbering),
        _term_key(head.args[1], numbering),
    )
    body_keys = tuple(_atom_key(atom, numbering) for atom in body)
    return (_KEY_VERSION, head_key, body_keys)


def canonical_clause_key(clause: Clause) -> tuple:
    """Return the immutable, comparable canonical content key of ``clause``.

    A zero- or one-premise body is considered in its original order only; a
    two-premise body considers both the original order and its reverse, and
    the lexicographic minimum of the two keys is returned. The input object
    is never mutated.

    Raises ``LogicValidationError`` if ``clause`` is not a ``Clause``; the
    diagnostic names only the received type and does not consume a generator
    or echo input ``repr``/``str``. Missing/extra/unknown positional arguments
    keep the ordinary Python ``TypeError``.
    """
    if not isinstance(clause, Clause):
        raise LogicValidationError(
            f"clause_key.clause must be a Clause; got {type(clause).__name__}"
        )

    head = clause.head
    body = clause.body
    candidates = [body]
    if len(body) == 2:
        candidates.append(body[::-1])

    best = min(_candidate_key(head, candidate) for candidate in candidates)
    return best
