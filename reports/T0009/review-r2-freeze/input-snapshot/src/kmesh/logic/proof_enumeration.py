"""Finite raw proof enumeration for one ground query.

Expands the direct ground derivations listed by
``kmesh.logic.derivations`` (T0008) into every ordered raw proof tree
for one ground query.  The world must already pass ``Clause``
construction checks and acyclic relation dependency checking inside
``enumerate_derivations``; that call is made exactly once, after every
local validation, and its errors propagate unchanged.

Each returned proof is a tuple of ``ProofStep`` objects.  The final
step concludes the query, and every premise index of each step points
at an earlier entry of that same proof, so the whole output can be
checked independently by ``kmesh.logic.proof.verify_proof``.  Expansion
does not judge canonical identity, uniqueness, or shortest depth: every
distinct source chain kept by the enumerator is expanded, proofs share
no subproof objects, and an empty result is not a proof count, a
denial, or a uniqueness verdict.

Inputs are validated strictly and in order, never copied, and never
reused across calls.  Budgets are cumulative: ``max_fact_checks`` /
``max_derivations`` are passed through to ``enumerate_derivations``
unchanged (exhaustion propagates its original error), while
``max_proof_steps`` is local and counts every generated proof step
(each fact step costs 1; each combination costs 1 plus its children's
step counts).
"""

from __future__ import annotations

import itertools

from .derivations import enumerate_derivations
from .proof import ProofStep
from .types import Atom, Clause, LogicValidationError

__all__ = ["ProofEnumerationLimitError", "enumerate_proofs"]


class ProofEnumerationLimitError(RuntimeError):
    """The local max_proof_steps budget ran out before expansion finished."""

    def __init__(self) -> None:
        super().__init__(
            "proofs.max_proof_steps exhausted before enumeration completed"
        )


def _require_budget(name: str, value: object) -> int:
    if type(value) is not int or value <= 0:
        raise LogicValidationError(
            f"proofs.{name} must be a non-bool positive integer; "
            f"got {type(value).__name__}"
        )
    return value


def _embed_child(child, offset: int) -> tuple[list[ProofStep], int]:
    """Re-anchor one child proof at ``offset``; return (steps, root index)."""
    steps = [
        ProofStep(
            step.clause_index,
            tuple(index + offset for index in step.premise_steps),
            step.conclusion,
        )
        for step in child
    ]
    return steps, offset + len(child) - 1


def enumerate_proofs(
    clauses: tuple[Clause, ...],
    query: Atom,
    *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
    max_proof_steps: int = 100_000,
) -> tuple[tuple[ProofStep, ...], ...]:
    """Enumerate every ordered raw proof tree for one ground query.

    Validation runs first (container, members, query type, query
    groundness, then the three budgets); only afterwards is
    ``enumerate_derivations`` called exactly once with ``clauses`` and
    the first two budgets, and its ``LogicValidationError`` (including
    world cycles) and ``DerivationLimitError`` propagate unchanged.
    A query with no record returns ``()`` after that call.

    Proofs are returned in global record order: after the derivation call,
    the records are indexed once by conclusion atom (every source record
    per atom, in record order); a query absent from the index returns
    ``()``.  The needed atoms are then collected with an explicit work
    list, fully iterative with no per-round rescan of the records.  A
    pool per needed atom is built by scanning the T0008 records in order
    (facts yield a one-step proof; one- and two-premise records combine
    their premise pools, outer slot first, one proof per child
    combination streamed via ``itertools.product`` with children
    re-anchored at their copy offset).  The query's pool is returned as
    a tuple.  When ``max_proof_steps`` runs out,
    ``ProofEnumerationLimitError`` is raised and no partial output is
    returned.  The result is verified externally; this function never
    calls ``verify_proof``.
    """
    if not isinstance(clauses, tuple):
        raise LogicValidationError(
            f"proofs.clauses must be a tuple of Clause; "
            f"got {type(clauses).__name__}"
        )
    for index, clause in enumerate(clauses):
        if not isinstance(clause, Clause):
            raise LogicValidationError(
                f"proofs.clauses[{index}] must be a Clause; "
                f"got {type(clause).__name__}"
            )
    if not isinstance(query, Atom):
        raise LogicValidationError(
            f"proofs.query must be an Atom; got {type(query).__name__}"
        )
    if not query.is_ground:
        raise LogicValidationError("proofs.query must be a ground Atom")
    fact_checks = _require_budget("max_fact_checks", max_fact_checks)
    derivations = _require_budget("max_derivations", max_derivations)
    steps_budget = _require_budget("max_proof_steps", max_proof_steps)

    records = enumerate_derivations(
        clauses, max_fact_checks=fact_checks, max_derivations=derivations
    )

    # Reverse index: every conclusion atom maps to the positions of all of
    # its direct source records, in record order.
    sources: dict[Atom, list[int]] = {}
    for position, record in enumerate(records):
        sources.setdefault(record.conclusion, []).append(position)
    if query not in sources:
        return ()

    # Needed set: the query plus every premise reachable through the
    # sources of an already-needed atom, walked with an explicit work
    # list (no recursion, no per-round rescan of all records).
    needed: set[Atom] = set()
    worklist = [query]
    while worklist:
        atom = worklist.pop()
        if atom in needed:
            continue
        needed.add(atom)
        for position in sources.get(atom, ()):
            for premise in records[position].premises:
                if premise not in needed:
                    worklist.append(premise)

    remaining = steps_budget
    pools: dict[Atom, list[tuple[ProofStep, ...]]] = {}
    for record in records:
        if record.conclusion not in needed:
            continue
        if not record.premises:
            # Fact: exactly one one-step proof.
            if remaining < 1:
                raise ProofEnumerationLimitError()
            remaining -= 1
            new_proofs = (
                (ProofStep(record.clause_index, (), record.conclusion),),
            )
        else:
            children = [pools[premise] for premise in record.premises]
            new_proofs = []
            for combo in itertools.product(*children):
                length = 1 + sum(len(child) for child in combo)
                if length > remaining:
                    raise ProofEnumerationLimitError()
                parts: list[ProofStep] = []
                refs: list[int] = []
                for child in combo:
                    steps, root = _embed_child(child, len(parts))
                    parts.extend(steps)
                    refs.append(root)
                parts.append(
                    ProofStep(record.clause_index, tuple(refs), record.conclusion)
                )
                remaining -= length
                new_proofs.append(tuple(parts))
        pools.setdefault(record.conclusion, []).extend(new_proofs)
    return tuple(pools.get(query, ()))
