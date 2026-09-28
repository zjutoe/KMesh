"""Match a batch of ground queries against a fixed reference-motif directory.

T0018 (D37), heldout motif audit.  For one finite acyclic target world
``clauses`` and a non-empty tuple of ground query ``Atom``s, together with
a non-empty tuple of reference triples ``(reference_clauses,
reference_query, reference_proof)`` — each reference a complete,
manually submitted occurrence tree within T0014's acceptance range (no
world-DAG check is added at this layer) — return, one entry per query in
input order, the set of reference-directory positions whose **complete**
proof key occurs as a complete rooted subtree of that query.

Fixed business order (no partial result, no early stop, no cross-call
cache):

1.  Local shape validation on ``queries`` (tuple, non-empty, each member a
    ground ``Atom``), then on ``references`` (tuple, non-empty, each
    member a length-3 tuple).  The target world and the inner clause /
    query / proof contents are never read or iterated before this; a
    generator or list is rejected at the outer type test and its body is
    never consumed.
2.  For every reference in original order, exactly one call to T0014
    ``canonical_motif_key`` with the original objects and the original
    ``max_steps`` / ``max_orientations`` budgets (passed through, not
    copied).  Duplicate references are not deduplicated: each directory
    position is counted separately.  An exception from any reference stops
    the call before any target query is touched.
3.  Only after **all** reference keys succeeded, for every target query in
    original order, exactly one call to T0017
    ``query_subtree_motif_keys`` with the original target world, the
    original query and all four original budgets (passed through, not
    copied).  Repeated target queries are called exactly once per position;
    a fact, a non-derivable query, an already-hit query, or a query whose
    keys already cover the directory never skip a later query.
4.  Return ``tuple(hits[i])`` with
    ``hits[i] = frozenset(j for j in range(len(references)) if K_j in U_i)``,
    where ``K_j = canonical_motif_key(*references[j])`` and
    ``U_i = query_subtree_motif_keys(clauses, queries[i])``.  Matching
    compares complete tuple keys only (no summary, node count, depth,
    root header or endpoint shortcut, no re-normalisation).  An empty
    ``U_i`` yields an empty frozenset: this is the match result for
    *this query, this directory, complete-subtree semantics*, not a claim
    that the world or the dataset is leak-free.

Dependency exceptions are never caught, wrapped, re-raised with a new
message, or retried; the original class, instance, message, ``__cause__``,
``__context__`` and ``__suppress_context__`` propagate unchanged.  Only the
standard library, ``kmesh.logic.types`` ``Atom`` / ``LogicValidationError``
(``Clause`` appears only as an annotation, never used) and the two module-level
name-imported call points ``motif.canonical_motif_key`` and
``query_motifs.query_subtree_motif_keys`` are imported.  No solver, verifier,
enumerator, proof_count, depth or engine module, and no IO, is used.

Budgets: ``max_fact_checks`` / ``max_derivations`` bound each target-world
enumeration; ``max_proof_steps`` bounds the cumulative generated steps of
each target query and the step length of each reference tree;
``max_orientations`` bounds direction enumeration per reference tree and per
target subtree separately.  The four budgets are never deducted across
references or queries and are not a whole-batch computation budget.
"""

from __future__ import annotations

from kmesh.logic.motif import canonical_motif_key
from kmesh.logic.query_motifs import query_subtree_motif_keys
from kmesh.logic.types import Atom, Clause, LogicValidationError

__all__ = ["heldout_motif_hits"]


def heldout_motif_hits(
    clauses: tuple[Clause, ...],
    queries: tuple[Atom, ...],
    references: tuple[tuple, ...],
    *,
    max_fact_checks: int = 100_000,
    max_derivations: int = 100_000,
    max_proof_steps: int = 100_000,
    max_orientations: int = 100_000,
) -> tuple[frozenset[int], ...]:
    """Return, for each target query in input order, the set of reference
    directory positions whose complete proof key is a complete rooted
    subtree of that query's complete-subtree motif union.

    See the module docstring for the fixed business order, error contract
    and budget semantics.  ``clauses`` is never copied or converted by this
    layer; ``queries`` and ``references`` are read-only inputs whose
    local shape is validated before any dependency call.
    """
    if not isinstance(queries, tuple):
        raise LogicValidationError(
            f"heldout_motifs.queries must be a tuple of ground Atom; "
            f"got {type(queries).__name__}")
    if not queries:
        raise LogicValidationError("heldout_motifs.queries must be non-empty")
    for i, q in enumerate(queries):
        if not isinstance(q, Atom):
            raise LogicValidationError(
                f"heldout_motifs.queries[{i}] must be an Atom; "
                f"got {type(q).__name__}")
        if not q.is_ground:
            raise LogicValidationError(
                f"heldout_motifs.queries[{i}] must be a ground Atom")
    if not isinstance(references, tuple):
        raise LogicValidationError(
            f"heldout_motifs.references must be a tuple of reference triples; "
            f"got {type(references).__name__}")
    if not references:
        raise LogicValidationError("heldout_motifs.references must be non-empty")
    for i, ref in enumerate(references):
        if not isinstance(ref, tuple) or len(ref) != 3:
            raise LogicValidationError(
                f"heldout_motifs.references[{i}] must be a "
                f"(clauses, query, proof) tuple")

    key_to_indices: dict[tuple, set[int]] = {}
    for j, ref in enumerate(references):
        key = canonical_motif_key(
            ref[0], ref[1], ref[2],
            max_steps=max_proof_steps,
            max_orientations=max_orientations,
        )
        key_to_indices.setdefault(key, set()).add(j)

    hits: list[frozenset[int]] = []
    for q in queries:
        u = query_subtree_motif_keys(
            clauses, q,
            max_fact_checks=max_fact_checks,
            max_derivations=max_derivations,
            max_proof_steps=max_proof_steps,
            max_orientations=max_orientations,
        )
        found: set[int] = set()
        for key, indices in key_to_indices.items():
            if key in u:
                found.update(indices)
        hits.append(frozenset(found))
    return tuple(hits)
