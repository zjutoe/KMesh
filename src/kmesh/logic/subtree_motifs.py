"""Per-occurrence-position complete rooted subtree motif keys.

T0016 (D34).  Given one legal, fully submitted single-occurrence proof, return
the complete bounded reference motif key of the whole proof **and** the key of
every occurrence position ``i`` (the complete rooted sub-proof of ``i``), in
storage order, with the whole-proof key appended last.

Only the standard library plus the already-accepted public APIs are used:
  * T0012 ``kmesh.logic.proof_key.canonical_proof_key`` — reached only through
    the T0014 public entry; never called here.
  * T0014 ``kmesh.logic.motif.canonical_motif_key`` (key encoder / verifier).
  * T0015 ``kmesh.logic.proof_subtree.extract_proof_subtree`` (subtree).
No new exception, validator, general tree traverser, or motif-encoding code is
added; the package ``__init__`` stays import-free and no heavy module
(engine, reference engine, solver, enumeration, depth) is imported.  The output
is tied to the original storage order: it is not a canonical whole-directory
key, and duplicate occurrences are kept as-is (no sorting, no deduplication).
"""

from __future__ import annotations

from kmesh.logic.motif import canonical_motif_key
from kmesh.logic.proof_subtree import extract_proof_subtree

__all__ = ["proof_subtree_motif_keys"]


def proof_subtree_motif_keys(
    clauses, query, proof, *, max_steps: int = 10_000, max_orientations: int = 100_000
) -> tuple[tuple, ...]:
    """Return the per-position complete rooted subtree motif directory.

    Step 1 (the first business operation, exactly once): call T0014
    ``canonical_motif_key(clauses, query, proof, max_steps, max_orientations)``
    on the **original** objects and budgets, saving the complete whole-proof key.
    Before this call no ``len`` / traversal / tuple conversion / copy /
    independent input check is performed; its ``LogicValidationError`` /
    ``ProofLimitError`` / ``MotifLimitError`` instances propagate unchanged.

    Step 2: after success, for ``i = 0..n-2`` in storage order (``n = len(proof)``)
    call T0015 ``extract_proof_subtree(clauses, query, proof, i, max_steps=max_steps)``
    and then T0014 ``canonical_motif_key(clauses, proof[i].conclusion, sub,
    max_steps, max_orientations)`` on the extracted object ``sub`` (the returned
    object, not a copy).  The last root (``n-1``) is neither extracted nor
    recomputed — its key is the whole-tree key from step 1.

    Step 3: join the step-2 subtree keys (storage order) with the saved
    whole-proof key (appended last) into a real tuple and return it.

    Budget semantics: ``max_steps`` bounds the **full input** and is passed
    unchanged to every dependent call.  ``max_orientations`` is a **per-subtree**
    orientation budget, not an accumulated / deducted whole-directory budget;
    the whole proof runs first so a whole-tree orientation shortage can fail
    fast.  A single-fact proof performs 1 T0014 / 0 T0015 calls.
    """
    whole_key = canonical_motif_key(
        clauses, query, proof,
        max_steps=max_steps, max_orientations=max_orientations,
    )
    n = len(proof)
    keys: list[tuple] = []
    for i in range(n - 1):
        sub = extract_proof_subtree(clauses, query, proof, i, max_steps=max_steps)
        keys.append(
            canonical_motif_key(
                clauses, proof[i].conclusion, sub,
                max_steps=max_steps, max_orientations=max_orientations,
            )
        )
    keys.append(whole_key)
    return tuple(keys)
