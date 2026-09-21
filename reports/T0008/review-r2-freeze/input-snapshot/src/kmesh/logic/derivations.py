"""Complete enumeration of direct ground derivations for acyclic worlds.

For a tuple of clauses whose relation dependency is acyclic,
``enumerate_derivations`` lists every ground direct application kept by
the world: each fact and each rule application with its exact source
clause position, its ordered ground premises and its instantiated
conclusion.  Distinct sources of the same conclusion are all kept; the
result records direct applications only, not full proof combinations.
It does not count, order by depth, or decide uniqueness or shortest
proof for any query.

A ``GroundDerivation`` is a frozen three-field record validated
structurally; it carries no world, clause, role, template, or proof
identity.  Enumeration scans each head predicate once in the
relationship topological order from
``kmesh.logic.dependency`` (which rejects cycles with its own error),
matching deduplicated candidate atoms kept per completed predicate.

The caller controls output size through two cumulative integer budgets:
``max_fact_checks`` counts candidate-versus-premise matching attempts
(including failed matches), ``max_derivations`` counts emitted records.
Either budget may be exhausted mid-enumeration, in which case
``DerivationLimitError`` is raised and no partial result is returned;
exhaustion is not a denial, a proof count, or a uniqueness decision.

Standard library, ``kmesh.logic.types`` and ``kmesh.logic.dependency``
only: no engine, reference engine, proof, torch, or YAML; no file I/O,
randomness, global mutable state, or input mutation.
"""

from __future__ import annotations

from dataclasses import dataclass

from kmesh.logic.dependency import relation_topological_order
from kmesh.logic.types import Atom, Clause, LogicValidationError


@dataclass(frozen=True)
class GroundDerivation:
    """One direct ground derivation: source position, premises, result.

    ``clause_index`` is a position in one caller-provided clauses tuple,
    not a stable identifier; ``premises`` holds 0 to 2 ground Atoms in
    the clause body order; ``conclusion`` is the instantiated head.
    Validation is structural only: local shape, groundness, and order —
    it never inspects the world or checks derivation semantics.
    """

    clause_index: int
    premises: tuple[Atom, ...]
    conclusion: Atom

    def __post_init__(self) -> None:
        if type(self.clause_index) is not int or self.clause_index < 0:
            # ``type(...) is int`` rejects bool as well as non-ints; the
            # message names the actual type only, never the value.
            raise LogicValidationError(
                f"derivation.clause_index must be a non-bool non-negative "
                f"integer; got {type(self.clause_index).__name__}")
        if not isinstance(self.premises, tuple):
            # Container is reported by type only: its members are
            # unvalidated and may not be representable.
            raise LogicValidationError(
                f"derivation.premises must be a tuple of Atom; "
                f"got {type(self.premises).__name__}")
        if len(self.premises) > 2:
            raise LogicValidationError(
                f"derivation.premises holds at most 2 atoms; "
                f"got {len(self.premises)}")
        for index, atom in enumerate(self.premises):
            if not isinstance(atom, Atom):
                raise LogicValidationError(
                    f"derivation.premises[{index}] must be an Atom; "
                    f"got {type(atom).__name__}")
            if not atom.is_ground:
                raise LogicValidationError(
                    f"derivation.premises[{index}] must be a ground Atom")
        if not isinstance(self.conclusion, Atom):
            raise LogicValidationError(
                f"derivation.conclusion must be an Atom; "
                f"got {type(self.conclusion).__name__}")
        if not self.conclusion.is_ground:
            raise LogicValidationError(
                "derivation.conclusion must be a ground Atom")


class DerivationLimitError(RuntimeError):
    """Either enumeration budget ran out before completion; no partial result."""


def _match(pattern: Atom, candidate: Atom, binding: dict[str, str]) -> dict[str, str] | None:
    """Try to match ``pattern`` against ground ``candidate``.

    Constants must be equal; each variable occurrence must agree with
    earlier bindings in ``binding`` (a variable dictionary shared only
    within this one rule-matching branch).  Returns a (possibly empty)
    binding on success — an empty binding is a legitimate match for a
    ground pattern — or ``None`` on conflict.
    """
    for pattern_arg, value in zip(pattern.args, candidate.args):
        if pattern_arg.startswith("?"):
            existing = binding.get(pattern_arg)
            if existing is not None:
                if existing != value:
                    return None
            else:
                binding[pattern_arg] = value
        elif pattern_arg != value:
            return None
    return binding


def _instantiate(atom: Atom, binding: dict[str, str]) -> Atom:
    return Atom(atom.pred, tuple(binding.get(name, name) for name in atom.args))


def _check_budget(remaining: int, name: str) -> None:
    if remaining <= 0:
        raise DerivationLimitError(
            f"enumerate.{name} exhausted before enumeration completed")


def enumerate_derivations(
    clauses: tuple[Clause, ...],
    *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
) -> tuple[GroundDerivation, ...]:
    """List every direct ground derivation of an acyclic clause world.

    Input is validated in order — clauses container, each clause, then
    both budgets — and finally ``relation_topological_order`` runs and
    any cycle error propagates unchanged.  Records are emitted in
    relationship topological order, then original clause position within
    a head predicate group, then the candidate nesting order of the
    scan; the same conclusion may appear once per distinct (source
    clause, ordered premises) pair.  Returns a tuple; ``()`` for empty
    input.  Raises ``LogicValidationError`` for bad input and
    ``DerivationLimitError`` (partial work discarded) when a budget is
    exhausted; exhaustion says nothing about derivability or uniqueness.
    """
    if not isinstance(clauses, tuple):
        raise LogicValidationError(
            f"enumerate.clauses must be a tuple of Clause; "
            f"got {type(clauses).__name__}")
    for index, item in enumerate(clauses):
        if not isinstance(item, Clause):
            raise LogicValidationError(
                f"enumerate.clauses[{index}] must be a Clause; "
                f"got {type(item).__name__}")
    for value, name in ((max_fact_checks, "max_fact_checks"),
                        (max_derivations, "max_derivations")):
        if type(value) is not int or value <= 0:
            raise LogicValidationError(
                f"enumerate.{name} must be a non-bool positive integer; "
                f"got {type(value).__name__}")
    order = relation_topological_order(clauses)

    groups: dict[str, list[int]] = {}
    for index, clause in enumerate(clauses):
        groups.setdefault(clause.head.pred, []).append(index)

    facts_left = max_fact_checks
    derivations_left = max_derivations
    records: list[GroundDerivation] = []
    buckets: dict[str, tuple[Atom, ...]] = {}

    for pred in order:
        bucket: list[Atom] = []
        for index in groups.get(pred, ()):
            clause = clauses[index]
            if not clause.body:
                _check_budget(derivations_left, "max_derivations")
                derivations_left -= 1
                records.append(GroundDerivation(index, (), clause.head))
                bucket.append(clause.head)
                continue
            if len(clause.body) == 1:
                pattern = clause.body[0]
                for candidate in buckets.get(pattern.pred, ()):
                    _check_budget(facts_left, "max_fact_checks")
                    facts_left -= 1
                    binding: dict[str, str] = {}
                    if _match(pattern, candidate, binding) is not None:
                        _check_budget(derivations_left, "max_derivations")
                        derivations_left -= 1
                        conclusion = _instantiate(clause.head, binding)
                        records.append(GroundDerivation(
                            index, (candidate,), conclusion))
                        # A derived conclusion feeds later head groups;
                        # its own group cannot consume it (that would be
                        # a self-loop already rejected by the DAG check).
                        bucket.append(conclusion)
                continue
            first, second = clause.body
            outer = buckets.get(first.pred, ())
            inner = buckets.get(second.pred, ())
            for outer_candidate in outer:
                _check_budget(facts_left, "max_fact_checks")
                facts_left -= 1
                partial: dict[str, str] = {}
                if _match(first, outer_candidate, partial) is None:
                    # The failed attempt already consumed its check; the
                    # next candidate simply starts a fresh binding.
                    continue
                # An empty ``inner`` still leaves the outer scanned: each
                # first-bucket candidate above costs exactly one check.
                for inner_candidate in inner:
                    _check_budget(facts_left, "max_fact_checks")
                    facts_left -= 1
                    binding = dict(partial)
                    if _match(second, inner_candidate, binding) is not None:
                        _check_budget(derivations_left, "max_derivations")
                        derivations_left -= 1
                        conclusion = _instantiate(clause.head, binding)
                        records.append(GroundDerivation(
                            index, (outer_candidate, inner_candidate),
                            conclusion))
                        # Feeds later head groups only; the same self-loop
                        # argument as in the single-premise branch applies.
                        bucket.append(conclusion)
        # Finalize this predicate once its whole group is done: dedupe
        # atoms (not derivations) and order candidates by args tuple.
        buckets[pred] = tuple(sorted(set(bucket), key=lambda atom: atom.args))

    return tuple(records)
