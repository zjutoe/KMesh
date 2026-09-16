"""Index-based main closure solver for forward Horn clauses.

Computes the full set of ground atoms derivable from a tuple of already
validated ``Clause`` objects using the independent main-path procedure
required by D20: each synchronous round indexes the previous round's fact
snapshot by predicate (bucket order fixed by ``atom.args``), then applies
every non-empty rule by joining its premises in body order, one candidate
fact at a time.

The reference solver (``kmesh.logic.reference_engine``) is a deliberately
different procedure (global constant-domain enumeration). The two solvers
share only the content types and the static clause validation; they are
cross-validated in tests and must not wrap or call each other.

Contract highlights (see docs/handoffs/T0005-indexed-closure.md, D20):

- input must be ``tuple[Clause, ...]``; a non-conforming container or
  member raises ``LogicValidationError`` before any empty-input
  fast-return or reasoning;
- ``max_fact_checks`` must be a non-bool positive int, no coercion;
- the result is an exact ``frozenset`` of ground atoms containing the
  initial facts and every derived head — nothing else;
- exceeding the budget raises ``IndexedLimitError``; no partial closure is
  ever returned and nothing may be silently skipped;
- pure function: inputs are not mutated and no state persists between
  calls.

Budget accounting: every candidate fact prepared for a match against the
current premise and current binding consumes exactly one unit — the
remaining budget is checked first, then decremented. Failed constant,
repeated-variable and already-bound checks count; re-checking the same
fact for a different first-premise branch counts again; a premise whose
predicate has no facts costs zero. Initial facts, index building and head
instantiation cost nothing. Counts accumulate across rules and rounds;
the exception is raised only when preparing the
``max_fact_checks + 1``-th candidate check, so a run that completes its
final no-new round exactly on the budget still succeeds.

Standard library only: no torch, no YAML, no file access and no global
state.
"""

from __future__ import annotations

from kmesh.logic.types import Atom, Clause, LogicValidationError


class IndexedLimitError(RuntimeError):
    """The indexed solver cannot finish within its fact-check budget."""


def _validate_inputs(clauses: object, max_fact_checks: object) -> None:
    """Validate the container, members and budget before any fast-return.

    Messages name the failing field, the expected kind/reason and the
    offending ``type(...)`` name only — never a ``repr`` of an
    unvalidated object or container.
    """
    if not isinstance(clauses, tuple):
        raise LogicValidationError(
            f"indexed.clauses must be a tuple of Clause, "
            f"got {type(clauses).__name__}")
    for index, clause in enumerate(clauses):
        if not isinstance(clause, Clause):
            raise LogicValidationError(
                f"indexed.clauses[{index}] must be a Clause, "
                f"got {type(clause).__name__}")
    if type(max_fact_checks) is not int or max_fact_checks <= 0:
        raise LogicValidationError(
            "indexed.max_fact_checks must be a non-bool positive "
            f"integer, got {type(max_fact_checks).__name__}")


def _index_by_predicate(facts: set[Atom]) -> dict[str, tuple[Atom, ...]]:
    """Group ``facts`` by predicate, each bucket ordered by ``atom.args``."""
    buckets: dict[str, list[Atom]] = {}
    for atom in facts:
        buckets.setdefault(atom.pred, []).append(atom)
    return {predicate: tuple(sorted(bucket, key=lambda atom: atom.args))
            for predicate, bucket in buckets.items()}


def _match(premise: Atom, candidate: Atom,
           binding: dict[str, str]) -> dict[str, str] | None:
    """Try ``candidate`` for ``premise`` given ``binding``.

    Returns a new binding extended with this candidate's argument values,
    or ``None`` when a literal constant, a repeated variable or an
    already-bound variable disagrees. The input binding is never mutated,
    so a failed candidate cannot pollute later candidates or branches.
    An empty dict is a successful match for a ground premise.
    """
    extended = dict(binding)
    for symbol, value in zip(premise.args, candidate.args):
        if symbol.startswith("?"):
            previous = extended.get(symbol)
            if previous is not None and previous != value:
                return None
            extended[symbol] = value
        elif symbol != value:
            return None
    return extended


def _instantiate(atom: Atom, binding: dict[str, str]) -> Atom:
    """Ground ``atom`` from ``binding``; literal constants stay as is."""
    return Atom(atom.pred,
                tuple(binding.get(arg, arg) for arg in atom.args))


def indexed_closure(
    clauses: tuple[Clause, ...],
    *,
    max_fact_checks: int = 100_000,
) -> frozenset[Atom]:
    """Return the smallest closure of ``clauses`` as a frozenset of atoms.

    Each synchronous round reads only the previous round's fact snapshot
    ``F_t``: it builds the predicate index once, then applies every
    non-empty rule in input order by nested premise matching. Derived
    heads are collected per round and merged only after the whole round,
    so a head never feeds the rules of the same round. The loop returns
    ``frozenset(F_t)`` as soon as a whole round derives nothing new.

    Raises
    ------
    LogicValidationError
        ``clauses`` is not a tuple of ``Clause`` or ``max_fact_checks``
        is not a non-bool positive int.
    IndexedLimitError
        A candidate check would exceed ``max_fact_checks``; no partial
        closure is returned.
    """
    _validate_inputs(clauses, max_fact_checks)

    facts = {clause.head for clause in clauses if not clause.body}
    rules = [clause for clause in clauses if clause.body]
    if not rules:
        return frozenset(facts)

    known = set(facts)
    budget = max_fact_checks
    while True:
        index = _index_by_predicate(known)
        derived = set()
        for rule in rules:
            premises = rule.body
            if len(premises) == 1:
                candidates: tuple[Atom, ...] = index.get(premises[0].pred, ())
                for candidate in candidates:
                    if budget <= 0:
                        raise IndexedLimitError(
                            "indexed.max_fact_checks is exhausted "
                            "before the closure stabilises")
                    budget -= 1
                    match = _match(premises[0], candidate, {})
                    if match is not None:
                        derived.add(_instantiate(rule.head, match))
            else:
                first, second = premises
                for first_candidate in index.get(first.pred, ()):
                    if budget <= 0:
                        raise IndexedLimitError(
                            "indexed.max_fact_checks is exhausted "
                            "before the closure stabilises")
                    budget -= 1
                    first_binding = _match(first, first_candidate, {})
                    if first_binding is None:
                        continue
                    for second_candidate in index.get(second.pred, ()):
                        if budget <= 0:
                            raise IndexedLimitError(
                                "indexed.max_fact_checks is exhausted "
                                "before the closure stabilises")
                        budget -= 1
                        match = _match(second, second_candidate, first_binding)
                        if match is not None:
                            derived.add(_instantiate(rule.head, match))
        if derived <= known:
            return frozenset(known)
        known |= derived
