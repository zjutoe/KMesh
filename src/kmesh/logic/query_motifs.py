"""Union of complete rooted subtree motifs for one query.

T0017 (D36).  Given a finite acyclic world ``clauses`` and a ground ``query``,
this module first enumerates **all** raw proofs of the query (T0009) and then
returns the union of the complete rooted subtree motif keys of **every**
occurrence position of **every** raw proof (T0016).  The returned ``frozenset``
is a set of complete motif keys, not a proof count and not a retained-world
size; it may be intersected with a future retained-key list.

Order of business is fixed:

1.  The first business operation is exactly one call to T0009
    ``enumerate_proofs`` with the original ``clauses``, ``query`` and the
    original three budgets, waited on for a complete return.  Before that call
    the inputs are never converted, iterated, copied or measured, and
    ``max_orientations`` is never checked.
2.  Only after a successful enumeration (including an empty enumeration) is
    ``max_orientations`` checked with the exact rule ``type(O) is int and
    O > 0``.
3.  Each raw proof, in the return order of T0009, receives exactly one T0016
    call with the original objects and
    ``max_steps=max_proof_steps`` / ``max_orientations``.  Every complete key
    of each per-tree directory is collected (whole-proof key, repeated
    occurrences and duplicate keys included); T0016 results are never deduped
    before the call.
4.  All T0016 calls must succeed before a real ``frozenset`` is returned.
    An empty enumeration plus a legal orientation budget returns
    ``frozenset()`` with no T0016 call.

No dependency exception is caught, wrapped or retried and no new exception
type is introduced: the original instances and messages propagate unchanged.
Consequently a T0009 failure precedes any orientation check, the first
per-tree T0016 failure stops the whole call with no partial set, and no
iterator, bool or partial result path exists.

Only the accepted dependencies are imported: the standard library (none used
here except ``__future__``), ``kmesh.logic.types`` for ``LogicValidationError``
and the two public call points, imported by name at module level.
"""

from __future__ import annotations

from kmesh.logic.proof_enumeration import enumerate_proofs
from kmesh.logic.subtree_motifs import proof_subtree_motif_keys
from kmesh.logic.types import LogicValidationError

__all__ = ["query_subtree_motif_keys"]


def query_subtree_motif_keys(
    clauses, query, *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
    max_proof_steps: int = 100_000,
    max_orientations: int = 100_000,
) -> frozenset[tuple]:
    """Return the union of complete rooted subtree motif keys for one query.

    ``clauses`` and ``query`` are passed unmodified to the single T0009 call
    below; ``max_orientations`` is only validated after that call returns,
    including for an empty enumeration.  Every raw proof then gets exactly one
    T0016 directory call with the original objects and the original S/O
    budgets, and every complete key of every directory is added to the result.
    The original exception classes, instances, messages and contexts of either
    dependency propagate unchanged: a T0009 failure precedes the orientation
    check, and the first failing proof stops the call with no partial result.
    """
    proofs = enumerate_proofs(
        clauses, query,
        max_fact_checks=max_fact_checks,
        max_derivations=max_derivations,
        max_proof_steps=max_proof_steps,
    )
    if type(max_orientations) is not int or max_orientations <= 0:
        raise LogicValidationError(
            "query_motifs.max_orientations must be a non-bool positive integer; "
            f"got {type(max_orientations).__name__}"
        )
    motifs: set[tuple] = set()
    for proof in proofs:
        motifs.update(
            proof_subtree_motif_keys(
                clauses, query, proof,
                max_steps=max_proof_steps,
                max_orientations=max_orientations,
            )
        )
    return frozenset(motifs)
