"""T0013: canonical proof count for one ground query.

A thin composition of T0009 (complete raw proof enumeration) and T0012
(single-tree canonical key).  Counts substantively distinct proof trees for
one ground query in one world: duplicate sources and alpha-equivalent raw
trees count once; genuinely different supports count separately.

0 means enumeration completed and the query has no proof; 1 means exactly
one canonical proof; >1 means multiple non-equivalent support proofs.  The
result is always ``int`` (a set length), never bool and never truncated.
"""

from __future__ import annotations

from .proof_enumeration import enumerate_proofs
from .proof_key import canonical_proof_key
from .types import Atom, Clause

__all__ = ["count_canonical_proofs"]


def count_canonical_proofs(
    clauses: tuple[Clause, ...],
    query: Atom,
    *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
    max_proof_steps: int = 100_000,
) -> int:
    """Return the exact canonical distinct proof count of ``query``.

    C / D / S (the three budgets) have T0009's cumulative semantics, passed
    through unchanged:

    * ``max_fact_checks`` / ``max_derivations`` govern the T0009 derivation
      step; ``DerivationLimitError`` propagates unchanged when exhausted.
    * ``max_proof_steps`` counts every proof step generated during
      enumeration, not just the final length.  Enumeration is the only
      lazy point: exhaustion raises ``ProofEnumerationLimitError`` as an
      original instance.  Budget exhaustion is a limit error, *not* a "no
      proof" result, and no partial count is returned.
    * World errors (including predicate cycles) propagate as T0009's
      ``LogicValidationError``, unchanged.

    After complete enumeration succeeds, T0012's ``canonical_proof_key`` is
    called exactly once per raw proof, in the original return order, with
    ``max_steps`` passed through as ``max_proof_steps`` (no default).
    Duplicate raw trees and duplicate keys merge via the set of full preorder
    keys; the result is the set length.  An empty enumeration completes
    enumeration and returns ``0`` without ever calling the key.

    This layer does not re-call the verifier, and adds no ``count.*`` error
    string, cache, or second uniqueness API.  It never early-returns after
    the first proof or the first two distinct keys.
    """
    proofs = enumerate_proofs(
        clauses,
        query,
        max_fact_checks=max_fact_checks,
        max_derivations=max_derivations,
        max_proof_steps=max_proof_steps,
    )
    keys = set()
    for proof in proofs:
        keys.add(canonical_proof_key(clauses, query, proof, max_steps=max_proof_steps))
    return len(keys)
