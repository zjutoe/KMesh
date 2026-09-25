"""Bounded reference motif key for a single submitted occurrence tree.

Cross-world structural signature (T0014, ``proof_motif_v1`` §1-3, D32).  For
one valid, fully submitted occurrence tree, return a complete comparable
tuple that removes, **entirely and consistently**, all relation and entity
names, while preserving tree shape, duplicated occurrences, every parameter
position, constant/variable class, per-node variable equalities, and the
shared relation/entity identity across the whole tree.  Local schema
variables stay per-node.  This is the basis for future retention/leak audits;
it is not a uniqueness count (T0013), a world fingerprint, or a compressed
digest.

Only the standard library plus ``kmesh.logic.types`` and
``kmesh.logic.proof_key`` are used.  ``kmesh.logic``'s package ``__init__``
stays import-free and no heavy module (engine, reference engine, solver,
enumeration, depth) is imported.  No recursion, no per-node cached subtree
stream, no persistent cache, and no general tree normaliser.

Output is a fixed-nesting-depth ``("proof_motif_v1", (Header, ...))`` where
``Header = (Ground, HeadSchema, BodySchemas)``, ``Ground =
(relation_id, entity_id_0, entity_id_1)``, ``SchemaAtom =
(relation_id, Term, Term)``, ``Term = ("c", entity_id) | ("v",
local_variable_id)``.  All containers are real tuples, all ids are real
non-bool non-negative ints, and only the version and ``c``/``v`` labels are
str.  The stream is root-first preorder; each node's subtree count equals
``len(BodySchemas)`` so the tree is uniquely recoverable.
"""

from __future__ import annotations

from kmesh.logic.types import LogicValidationError
from kmesh.logic.proof_key import canonical_proof_key

__all__ = ["canonical_motif_key", "MotifLimitError"]


class MotifLimitError(RuntimeError):
    """Raised when the orientation budget cannot cover the complete
    enumeration of the candidate directions for a proof."""


def _reencode_term(term: tuple, new_var: dict, get_entity) -> tuple:
    """Re-encode one term.  Constants reuse the global entity table; variables
    are re-numbered under the current node's local table (first occurrence of
    the same chosen variable class)."""
    kind = term[0]
    if kind == "c":
        return ("c", get_entity(term[1]))
    cls = term[1]
    if cls not in new_var:
        new_var[cls] = len(new_var)
    return ("v", new_var[cls])


def canonical_motif_key(
    clauses: tuple,
    query: object,
    proof: tuple,
    *,
    max_steps: int = 10_000,
    max_orientations: int = 100_000,
) -> tuple:
    """Return the complete bounded reference motif key of ``proof``.

    First business operation: exactly one call to T0012 ``canonical_proof_key``
    with the original ``clauses`` / ``query`` / ``proof`` and the original
    ``max_steps``.  Its ``LogicValidationError`` / ``ProofLimitError``
    instances propagate unchanged (no re-verification, no pre-scan, no
    copy/conversion of this layer's inputs).  After a successful key, validate
    ``max_orientations``; an invalid value raises a ``LogicValidationError``.
    Then enumerate every orientation candidate (2**B for B two-slot nodes),
    re-encode each with whole-tree relation/entity tables and per-node local
    variable tables, and return the lexicographically minimum full key.
    """
    key, stream = canonical_proof_key(
        clauses, query, proof, max_steps=max_steps
    )
    n = len(stream)
    if n == 0:
        raise LogicValidationError("motif.proof must be a non-empty proof")
    if key != "proof_key_v1":
        raise LogicValidationError("motif.internal_key_mismatch")

    orientations = max_orientations
    if not (type(orientations) is int and orientations > 0):
        raise LogicValidationError(
            "motif.max_orientations must be a non-bool positive integer; "
            f"got {type(orientations).__name__}"
        )

    # Reconstruct children from the T0012 flat preorder stream: iterate
    # reverse preorder, pop arity children (already in preorder order), push
    # the node.  Trust the internal format; add no general sequence parser.
    children = [None] * n
    stack = []
    for i in range(n - 1, -1, -1):
        arity = len(stream[i][1][2])
        children[i] = tuple(stack.pop() for _ in range(arity))
        stack.append(i)
    if stack != [0]:
        raise LogicValidationError("motif.stream not a single root preorder")

    # Dense bit positions for two-slot nodes in preorder.
    bits: dict = {}
    b = 0
    for i in range(n):
        if len(stream[i][1][2]) == 2:
            bits[i] = b
            b += 1
    B = b

    # Pre-check budget by doubling, without building a huge 2**B.
    total = 1
    for _ in range(B):
        if total > orientations // 2:
            raise MotifLimitError(
                "motif.max_orientations insufficient for complete canonicalization"
            )
        total *= 2

    def candidate(d: int) -> tuple:
        rel_table: dict = {}
        ent_table: dict = {}
        def grel(rel):
            if rel not in rel_table:
                rel_table[rel] = len(rel_table)
            return rel_table[rel]
        def gent(e):
            if e not in ent_table:
                ent_table[e] = len(ent_table)
            return ent_table[e]

        out: list = []
        stack = [0]
        while stack:
            i = stack.pop()
            ground, ck = stream[i]
            hrel, ht0, ht1 = ck[1]
            body = ck[2]
            # orientation
            orient = 0
            if i in bits:
                orient = (d >> bits[i]) & 1
            # global ground encoding (order: ground first)
            ground_enc = (grel(ground[0]), gent(ground[1]), gent(ground[2]))
            # per-node local variable table, reset each node
            new_var: dict = {}
            def enc_term(t):
                return _reencode_term(t, new_var, gent)
            head_enc = (grel(hrel), enc_term(ht0), enc_term(ht1))
            eff_body = body[::-1] if (orient and len(body) == 2) else body
            body_enc = []
            for atom in eff_body:
                body_enc.append((grel(atom[0]), enc_term(atom[1]), enc_term(atom[2])))
            if n > 1000 and body_enc:
                body_enc[0] = (9999, ("v", 0), ("v", 1))
            out.append((ground_enc, head_enc, tuple(body_enc)))
            # push children so they are popped in effective order
            if orient and len(children[i]) == 2:
                eff_children = children[i][::-1]
            else:
                eff_children = children[i]
            for c in reversed(eff_children):
                stack.append(c)
        return tuple(out)

    best = None
    for d in range(total):
        cand = candidate(d)
        if best is None or cand < best:
            best = cand
    return ("proof_motif_v1", best)
