"""Canonical structure key for a single submitted occurrence tree.

Same-world proof identity (T0012, ``proof_identity_v1`` §3, D30).  For one
valid, fully submitted occurrence tree — a verified proof in which every
non-final step is referenced exactly once and the final step zero times —
return a flat canonical *preorder* key that removes clause storage position,
step numbers, local variable names, and the allowed premise/subtree joint
swaps, while preserving actual ground conclusions, clause content, every
support path, and duplicated occurrences.

Only the standard library plus ``kmesh.logic.types`` and ``kmesh.logic.proof``
are used; ``kmesh.logic``'s package ``__init__`` stays import-free and no heavy
module (engine, reference engine, solver, enumeration, depth) is imported.
No second budget, no general tree framework, no Python recursion over the
proof, and no per-node cache of a flattened subtree stream.

The output is a fixed-nesting-depth ``("proof_key_v1", (Header, ...))`` where
``Header = (GroundKey, ClauseKey)`` and ``ClauseKey`` is exactly the
``("clause_key_v1", ...)`` full format used by T0011.  A node's arity is
``len(ClauseKey[2])``, so the flat preorder stream decodes the whole tree
without terminators.  It is an offline audit artifact, not a persistent digest,
world fingerprint, uniqueness count, or motif signature.
"""

from __future__ import annotations

from kmesh.logic.proof import LogicValidationError, verify_proof

__all__ = ["canonical_proof_key"]


def _term_key(term: str, numbering: dict[str, int]) -> tuple:
    """Encode one argument string.

    A variable (``?`` prefix) is encoded by its first-occurrence number as
    ``("v", n)``; a constant keeps its original spelling as ``("c", s)``.
    Constants never consume a variable number.
    """
    if term.startswith("?"):
        number = numbering.setdefault(term, len(numbering))
        return ("v", number)
    return ("c", term)


def _atom_key(atom: object, numbering: dict[str, int]) -> tuple:
    """Encode a binary atom under a shared numbering table."""
    return (
        atom.pred,
        _term_key(atom.args[0], numbering),
        _term_key(atom.args[1], numbering),
    )


def _ordered_candidate_key(head: object, body: tuple) -> tuple:
    """Full ``clause_key_v1`` for one specific body ordering.

    A fresh variable numbering is built by scanning the head args
    left-to-right, then each atom of ``body`` (in the supplied order)
    args left-to-right; first occurrence gets 0, 1, 2, ... and constants
    do not consume numbers.  This returns the key for the *given* ordering
    only; it never merges two orderings before the caller chooses.
    """
    numbering: dict[str, int] = {}
    head_key = (
        head.pred,
        _term_key(head.args[0], numbering),
        _term_key(head.args[1], numbering),
    )
    body_keys = tuple(_atom_key(atom, numbering) for atom in body)
    return ("clause_key_v1", head_key, body_keys)


def _compare_subtrees(
    a: int, b: int, headers: list, children_order: list,
) -> int:
    """Compare the preorder header streams of two subtrees root-by-header.

    Iterative (explicit stack), never materialising a whole flattened subtree
    sequence.  Returns -1/0/1 (a<b / equal / a>b).  Legal complete tree
    streams never form a strict prefix of each other; simultaneous end means
    equal, and a mismatched end is treated defensively as a difference.
    """
    stack_a = [a]
    stack_b = [b]
    while stack_a and stack_b:
        ia = stack_a.pop()
        ib = stack_b.pop()
        ha = headers[ia]
        hb = headers[ib]
        if ha != hb:
            return -1 if ha < hb else 1
        for child in reversed(children_order[ia]):
            stack_a.append(child)
        for child in reversed(children_order[ib]):
            stack_b.append(child)
    if not stack_a and not stack_b:
        return 0
    return -1 if not stack_a else 1


def canonical_proof_key(
    clauses: tuple,
    query: object,
    proof: tuple,
    *,
    max_steps: int = 10_000,
) -> tuple:
    """Return the immutable, comparable canonical preorder key of ``proof``.

    The first operation is a single call to ``verify_proof`` with the original
    ``clauses`` / ``query`` / ``proof`` / ``max_steps``.  ``LogicValidationError``
    and ``ProofLimitError`` propagate unchanged (one call, no wrapping, no
    early scan of this layer's inputs).  If the verifier returns ``False``
    (empty proof, wrong query, illegal derivation), raise
    ``LogicValidationError("proof_key.proof must be a valid proof of query")``.
    After verification, require each non-final step to be referenced exactly
    once and the final step zero times; any other count raises
    ``LogicValidationError("proof_key.proof must be a single occurrence tree")``.
    """
    if not verify_proof(clauses, query, proof, max_steps=max_steps):
        raise LogicValidationError(
            "proof_key.proof must be a valid proof of query"
        )

    n = len(proof)
    if n == 0:
        raise LogicValidationError(
            "proof_key.proof must be a valid proof of query"
        )

    ref_count = [0] * n
    for step in proof:
        for ref in step.premise_steps:
            ref_count[ref] += 1
    for i in range(n - 1):
        if ref_count[i] != 1:
            raise LogicValidationError(
                "proof_key.proof must be a single occurrence tree"
            )
    if ref_count[n - 1] != 0:
        raise LogicValidationError(
            "proof_key.proof must be a single occurrence tree"
        )

    headers: list = [None] * n
    children_order: list = [None] * n

    for i, step in enumerate(proof):
        clause = clauses[step.clause_index]
        head = clause.head
        body = clause.body
        premise_steps = list(step.premise_steps)

        if len(premise_steps) <= 1:
            # 0- or 1-premise: a single ordered candidate, no swap.
            clause_key = _ordered_candidate_key(head, body)
            chosen_refs = tuple(premise_steps)
        else:
            # 2-premise: joint normalise the two body slots with their
            # corresponding subtree references; only reorder the subtrees
            # when the two slot keys are exactly equal.
            fwd_key = _ordered_candidate_key(head, body)
            rev_key = _ordered_candidate_key(head, tuple(reversed(body)))
            ref0, ref1 = premise_steps
            if fwd_key < rev_key:
                clause_key = fwd_key
                chosen_refs = (ref0, ref1)
            elif rev_key < fwd_key:
                clause_key = rev_key
                chosen_refs = (ref1, ref0)
            else:
                clause_key = fwd_key
                cmp = _compare_subtrees(ref0, ref1, headers, children_order)
                if cmp < 0:
                    chosen_refs = (ref0, ref1)
                elif cmp > 0:
                    chosen_refs = (ref1, ref0)
                else:
                    chosen_refs = (ref0, ref1)

        conclusion = step.conclusion
        ground_key = (conclusion.pred, conclusion.args[0], conclusion.args[1])
        headers[i] = (ground_key, clause_key)
        children_order[i] = chosen_refs

    stream: list = []
    stack = [n - 1]
    while stack:
        i = stack.pop()
        stream.append(headers[i])
        for child in reversed(children_order[i]):
            stack.append(child)
    return ("proof_key_v1", tuple(stream))
