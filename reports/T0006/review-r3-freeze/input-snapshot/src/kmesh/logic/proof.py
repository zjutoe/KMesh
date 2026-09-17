"""Independent verifier for a finite, fully submitted proof.

T0006 (D21): given ``clauses``, a ground ``query`` and a finite proof
submitted as :class:`ProofStep` records, verify that every step is legally
derived from the clause it cites and from previously verified
conclusions.  ``verify_proof`` only checks the submitted evidence: it never
searches for or generates a proof, never returns a score or a partial
result, and does not import either closure solver.

Research boundary (E0 v2 S4.1/S4.5): ``True`` only certifies that this
evidence is valid — it says nothing about uniqueness, minimality, or the
existence of alternative paths; ``False`` only says this evidence is
invalid and **must not** be used as a negative label for the query; an
over-limit proof raises :class:`ProofLimitError` and merely means the
verification was not completed, which is also not a semantic ``False``.  A
proof, its indices, and its intermediate conclusions are offline audit
artifacts only and must never reach model inputs or forward/predict.
"""

from __future__ import annotations

from dataclasses import dataclass

from kmesh.logic.types import Atom, Clause, LogicValidationError


@dataclass(frozen=True)
class ProofStep:
    """One submitted step: a clause index, premise-step references, and a
    ground conclusion.

    ``clause_index`` points into the ``clauses`` tuple handed to
    :func:`verify_proof` for this submission only — it is not a stable patch
    ID or persistent content identifier.  ``premise_steps`` references
    earlier steps in this same proof, in the same order as the cited
    clause's body.  The constructor enforces only local structure; legal
    structure does not imply a valid proof.
    """

    clause_index: int
    premise_steps: tuple[int, ...]
    conclusion: Atom

    def __post_init__(self) -> None:
        if type(self.clause_index) is not int or self.clause_index < 0:
            raise LogicValidationError(
                "proof_step.clause_index must be a non-bool non-negative "
                f"integer, got {type(self.clause_index).__name__}"
            )
        if not isinstance(self.premise_steps, tuple):
            raise LogicValidationError(
                "proof_step.premise_steps must be a tuple of step "
                f"references, got {type(self.premise_steps).__name__}"
            )
        if len(self.premise_steps) > 2:
            raise LogicValidationError(
                "proof_step.premise_steps holds at most 2 step references, "
                f"got {len(self.premise_steps)}"
            )
        for j, ref in enumerate(self.premise_steps):
            if type(ref) is not int or ref < 0:
                raise LogicValidationError(
                    f"proof_step.premise_steps[{j}] must be a non-bool "
                    f"non-negative integer, got {type(ref).__name__}"
                )
        if not isinstance(self.conclusion, Atom):
            raise LogicValidationError(
                "proof_step.conclusion must be an Atom, "
                f"got {type(self.conclusion).__name__}"
            )
        if not self.conclusion.is_ground:
            raise LogicValidationError(
                "proof_step.conclusion must be a ground Atom"
            )


class ProofLimitError(RuntimeError):
    """The submitted proof exceeds the allowed number of steps."""


def verify_proof(
    clauses: tuple[Clause, ...],
    query: Atom,
    proof: tuple[ProofStep, ...],
    *,
    max_steps: int = 10_000,
) -> bool:
    """Verify a fully submitted proof of ``query`` from ``clauses``.

    Every step is checked in submission order against the clause it cites
    and the already-verified conclusions of the steps it references.
    Returns ``True`` exactly when every step is legal and the final
    conclusion equals ``query``; returns ``False`` (never raises) for any
    semantic failure.  Raises :class:`LogicValidationError` for invalid
    inputs and :class:`ProofLimitError` when ``len(proof) > max_steps``;
    the limit check runs before any per-member type check, so an over-limit
    proof fails fast without scanning its members.
    """
    if not isinstance(clauses, tuple):
        raise LogicValidationError(
            "verify.clauses must be a tuple of Clause, "
            f"got {type(clauses).__name__}"
        )
    for i, clause in enumerate(clauses):
        if not isinstance(clause, Clause):
            raise LogicValidationError(
                f"verify.clauses[{i}] must be a Clause, "
                f"got {type(clause).__name__}"
            )
    if not isinstance(query, Atom):
        raise LogicValidationError(
            "verify.query must be an Atom, "
            f"got {type(query).__name__}"
        )
    if not query.is_ground:
        raise LogicValidationError("verify.query must be a ground Atom")
    if not isinstance(proof, tuple):
        raise LogicValidationError(
            "verify.proof must be a tuple of ProofStep, "
            f"got {type(proof).__name__}"
        )
    if type(max_steps) is not int or max_steps <= 0:
        raise LogicValidationError(
            "verify.max_steps must be a non-bool positive integer, "
            f"got {type(max_steps).__name__}"
        )

    if len(proof) > max_steps:
        raise ProofLimitError(
            "verify.proof length "
            "exceeds verify.max_steps"
        )

    for i, step in enumerate(proof):
        if not isinstance(step, ProofStep):
            raise LogicValidationError(
                f"verify.proof[{i}] must be a ProofStep, "
                f"got {type(step).__name__}"
            )

    if not proof:
        return False

    conclusions: list[Atom] = []
    for i, step in enumerate(proof):
        if step.clause_index >= len(clauses):
            return False
        clause = clauses[step.clause_index]
        if len(step.premise_steps) != len(clause.body):
            return False
        binding: dict[str, str] = {}
        legal = True
        for ref, premise in zip(step.premise_steps, clause.body):
            if ref >= i:
                legal = False
                break
            premise_atom = conclusions[ref]
            if premise_atom.pred != premise.pred:
                legal = False
                break
            for symbol, value in zip(premise.args, premise_atom.args):
                if symbol.startswith("?"):
                    fixed = binding.get(symbol)
                    if fixed is not None and fixed != value:
                        legal = False
                        break
                    binding[symbol] = value
                elif symbol != value:
                    legal = False
                    break
            if not legal:
                break
        if not legal:
            return False
        expected = Atom(
            clause.head.pred,
            tuple(binding.get(arg, arg) for arg in clause.head.args),
        )
        if expected != step.conclusion:
            return False
        conclusions.append(step.conclusion)

    return conclusions[-1] == query
