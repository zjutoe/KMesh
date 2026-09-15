"""Naive enumeration reference solver for forward-Horn closure.

Computes the full set of derivable ground atoms (the closure) from a tuple
of already-validated :class:`~kmesh.logic.types.Clause` objects, using the
simplest correct reference procedure: a fixed global constant domain,
per-rule exhaustive binding enumeration, and a synchronous fixpoint loop
against the previous round's fact snapshot. The result is meant to be
checked by hand on small worlds and later cross-validated by an index-based
main solver; it is NOT the main solving path and deliberately shares no
matching/binding/closure code with it.

Contract highlights (see docs/handoffs/T0004-reference-closure.md, D19):

- only ``tuple[Clause, ...]`` input; members must be ``Clause``;
- ``max_rule_evaluations`` must be a non-bool positive int, no coercion;
- inputs are validated before any empty-input fast-return or reasoning;
- invalid input raises :class:`~kmesh.logic.types.LogicValidationError`
  with the failing field path and the expected kind/reason, never a
  ``repr`` of an unvalidated object or container;
- exceeding the budget raises :class:`ReferenceLimitError`; no partial
  closure is ever returned;
- the result is an immutable ``frozenset`` of ground atoms containing the
  initial facts and every derived head; nothing else (rules, proofs,
  depths) and no state persists between calls.

Budget accounting: every candidate binding prepared for a non-empty rule
consumes exactly one unit, checked and then decremented; failed premise
checks, duplicate rules, and the final no-new round all count. Initial
empty-body facts consume nothing. Standard library only: no torch, no
YAML, no file access, no global state.
"""

from __future__ import annotations

import itertools

from kmesh.logic.types import Atom, Clause, LogicValidationError


class ReferenceLimitError(RuntimeError):
    """The reference solver cannot finish within its evaluation budget."""


def _validate_inputs(clauses: object, max_rule_evaluations: object) -> None:
    if not isinstance(clauses, tuple):
        raise LogicValidationError(
            f"reference.clauses must be a tuple of Clause, "
            f"got {type(clauses).__name__}")
    for index, clause in enumerate(clauses):
        if not isinstance(clause, Clause):
            raise LogicValidationError(
                f"reference.clauses[{index}] must be a Clause, "
                f"got {type(clause).__name__}")
    if type(max_rule_evaluations) is not int or max_rule_evaluations <= 0:
        raise LogicValidationError(
            "reference.max_rule_evaluations must be a non-bool positive "
            f"integer, got {type(max_rule_evaluations).__name__}")


def _collect_domain(clauses: tuple[Clause, ...]) -> tuple[str, ...]:
    """Sorted constants occurring in any body or head argument."""
    constants = set()
    for clause in clauses:
        for atom in tuple(clause.body) + (clause.head,):
            for arg in atom.args:
                if not arg.startswith("?"):
                    constants.add(arg)
    return tuple(sorted(constants))


def _rule_variables(rule: Clause) -> tuple[str, ...]:
    """Sorted distinct rule variables over body plus head, each once."""
    variables = set()
    for atom in tuple(rule.body) + (rule.head,):
        variables |= atom.variables
    return tuple(sorted(variables))


def _substitute(atom: Atom, binding: dict[str, str]) -> Atom:
    return Atom(atom.pred, tuple(binding.get(arg, arg) for arg in atom.args))


def reference_closure(
    clauses: tuple[Clause, ...],
    *,
    max_rule_evaluations: int = 100_000,
) -> frozenset[Atom]:
    """Return the closure of ``clauses`` as a frozenset of ground atoms.

    Raises :class:`LogicValidationError` for invalid input and
    :class:`ReferenceLimitError` if a further candidate check is needed
    after the budget is exhausted.
    """
    _validate_inputs(clauses, max_rule_evaluations)

    domain = _collect_domain(clauses)
    facts = {clause.head for clause in clauses if not clause.body}
    rules = [clause for clause in clauses if clause.body]
    if not rules:
        return frozenset(facts)
    rule_variables = [_rule_variables(rule) for rule in rules]

    known = set(facts)
    budget = max_rule_evaluations
    while True:
        derived = set()
        for rule, variables in zip(rules, rule_variables):
            for values in itertools.product(domain, repeat=len(variables)):
                if budget <= 0:
                    raise ReferenceLimitError(
                        "reference.max_rule_evaluations is exhausted "
                        "before the closure stabilises")
                budget -= 1
                binding = dict(zip(variables, values))
                if all(_substitute(atom, binding) in known
                       for atom in rule.body):
                    derived.add(_substitute(rule.head, binding))
        if derived <= known:
            return frozenset(known)
        known |= derived
