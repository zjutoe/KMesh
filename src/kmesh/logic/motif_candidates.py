"""Fixed finite candidate motif audit for depth-2 and depth-3 left-spine ops.

T0019 (D39): produces a deterministic, reconstructable witness-based report
over the 80 fixed left-spine candidate worlds (all 2-letters then all
3-letters over ``C I J T``) that precede the formal retained-directory
freeze.  This is an offline reference audit only; the 80 candidates are not
the complete set of depth-2/3 proof structures, nor a data split.

The public interface is a single no-arg function.  The report is a plain
dict of plain containers (dict/list) with str/int leaves; it is never
written to the worktree.  ``python -m kmesh.logic.motif_candidates`` prints
the report as one JSON document to stdout for controller capture.

The four budgets (C, D, S, O) are per-dependency-call budgets, not a whole
audit computation budget.  All values in the report come from real calls to the
accepted dependency APIs; the hand-constructed witness is the input to those
calls and is what makes the report reproducible.
"""

from __future__ import annotations

import json
import sys
from itertools import product

from kmesh.logic.depth import minimum_proof_depth
from kmesh.logic.heldout_motifs import heldout_motif_hits
from kmesh.logic.motif import canonical_motif_key
from kmesh.logic.proof_count import count_canonical_proofs
from kmesh.logic.proof import ProofStep
from kmesh.logic.types import Atom, Clause

__all__ = ["audit_motif_candidates"]

# Per-call budgets, fixed at the T0019 contract values.
_MAX_FACT_CHECKS: int = 100_000
_MAX_DERIVATIONS: int = 100_000
_MAX_PROOF_STEPS: int = 100_000
_MAX_ORIENTATIONS: int = 100_000

# Operation vocabulary in fixed order; character order is the product order.
_OPS: tuple[str, ...] = ("C", "I", "J", "T")


def _atom(pred: str, a: str, b: str) -> Atom:
    return Atom(pred, (a, b))


def _fact(pred: str, a: str, b: str) -> Clause:
    return Clause((), _atom(pred, a, b))


def _copy_clause(src: str, dst: str) -> Clause:
    return Clause((_atom(src, "?x", "?y"),), _atom(dst, "?x", "?y"))


def _inv_clause(src: str, dst: str) -> Clause:
    return Clause((_atom(src, "?x", "?y"),), _atom(dst, "?y", "?x"))


def _join_clause(src: str, side: str, dst: str) -> Clause:
    return Clause(
        (_atom(src, "?x", "?y"), _atom(side, "?y", "?z")),
        _atom(dst, "?x", "?z"),
    )


def _inter_clause(src: str, side: str, dst: str) -> Clause:
    return Clause(
        (_atom(src, "?x", "?y"), _atom(side, "?x", "?y")),
        _atom(dst, "?x", "?y"),
    )


def _candidate_witness(word: str):
    """Build the ``(clauses, query, proof)`` witness for a fixed word.

    The initial clause is the ground fact ``p0(e0, e1)`` with proof step 0.
    For each character (1-indexed) the current ground root is ``p{i-1}(u, v)``;
    the new head is always ``p{i}``.  J and T add a fresh side fact first
    (so the rule can cite it in the second premise), then the rule.  Each
    new clause contributes exactly one proof step in append order.
    """
    clauses: list[Clause] = [_fact("p0", "e0", "e1")]
    steps: list[ProofStep] = [ProofStep(0, (), _atom("p0", "e0", "e1"))]
    u, v = "e0", "e1"
    for i, ch in enumerate(word, start=1):
        if ch == "C":
            clauses.append(_copy_clause(f"p{i - 1}", f"p{i}"))
            new_u, new_v = u, v
            steps.append(
                ProofStep(
                    len(clauses) - 1,
                    (len(steps) - 1,),
                    _atom(f"p{i}", new_u, new_v),
                )
            )
        elif ch == "I":
            clauses.append(_inv_clause(f"p{i - 1}", f"p{i}"))
            new_u, new_v = v, u
            steps.append(
                ProofStep(
                    len(clauses) - 1,
                    (len(steps) - 1,),
                    _atom(f"p{i}", new_u, new_v),
                )
            )
        elif ch == "J":
            clauses.append(_fact(f"s{i}", v, f"e{i + 1}"))
            steps.append(ProofStep(len(clauses) - 1, (), _atom(f"s{i}", v, f"e{i + 1}")))
            clauses.append(_join_clause(f"p{i - 1}", f"s{i}", f"p{i}"))
            new_u, new_v = u, f"e{i + 1}"
            steps.append(
                ProofStep(
                    len(clauses) - 1,
                    (len(steps) - 2, len(steps) - 1),
                    _atom(f"p{i}", new_u, new_v),
                )
            )
        else:  # ch == "T"
            clauses.append(_fact(f"s{i}", u, v))
            steps.append(ProofStep(len(clauses) - 1, (), _atom(f"s{i}", u, v)))
            clauses.append(_inter_clause(f"p{i - 1}", f"s{i}", f"p{i}"))
            new_u, new_v = u, v
            steps.append(
                ProofStep(
                    len(clauses) - 1,
                    (len(steps) - 2, len(steps) - 1),
                    _atom(f"p{i}", new_u, new_v),
                )
            )
        u, v = new_u, new_v
    return tuple(clauses), steps[-1].conclusion, tuple(steps)


def _words() -> list[str]:
    return (
        ["".join(p) for p in product(_OPS, repeat=2)]
        + ["".join(p) for p in product(_OPS, repeat=3)]
    )


def _atom_json(atom: Atom) -> dict:
    return {"pred": atom.pred, "args": list(atom.args)}


def _clause_json(clause: Clause) -> dict:
    return {
        "body": [_atom_json(a) for a in clause.body],
        "head": _atom_json(clause.head),
    }


def _step_json(step: ProofStep) -> dict:
    return {
        "clause_index": step.clause_index,
        "premise_steps": list(step.premise_steps),
        "conclusion": _atom_json(step.conclusion),
    }


def _key_json(key: object) -> object:
    if isinstance(key, tuple):
        return [_key_json(item) for item in key]
    return key


def _serialized_candidate(
    word: str, clauses, query, proof, motif_key, depth, count, contained_ids
) -> dict:
    return {
        "id": word,
        "clauses": [_clause_json(c) for c in clauses],
        "query": _atom_json(query),
        "proof": [_step_json(s) for s in proof],
        "motif_key": _key_json(motif_key),
        "minimum_depth": depth,
        "canonical_proof_count": count,
        "proof_steps": len(proof),
        "contained_ids": contained_ids,
    }


def audit_motif_candidates() -> dict:
    """Run the fixed 80-candidate left-spine motif audit and return its dict.

    No file I/O, no stdout, no side effects.  Returns the report as a plain
    ``dict`` (only dict/list containers, str/int leaves).
    """
    words = _words()

    # Build every witness once; measure each with the accepted APIs.
    measured = []
    for word in words:
        clauses, query, proof = _candidate_witness(word)
        motif_key = canonical_motif_key(
            clauses, query, proof,
            max_steps=_MAX_PROOF_STEPS, max_orientations=_MAX_ORIENTATIONS,
        )
        canonical_count = count_canonical_proofs(
            clauses, query,
            max_fact_checks=_MAX_FACT_CHECKS, max_derivations=_MAX_DERIVATIONS,
            max_proof_steps=_MAX_PROOF_STEPS,
        )
        depth = minimum_proof_depth(
            clauses, query,
            max_fact_checks=_MAX_FACT_CHECKS, max_derivations=_MAX_DERIVATIONS,
        )
        measured.append((word, clauses, query, proof, motif_key, depth, canonical_count))

    # One fixed reference directory, in directory order.
    references = tuple(
        (clauses, query, proof) for (_, clauses, query, proof, _, _, _) in measured
    )
    id_by_index = {i: w for i, w in enumerate(words)}

    # Per-candidate containment (full 80 reference directory each time,
    # single-query batch).  contained_ids are listed in directory order.
    rows = []
    containment_edges = 0
    proper_containment_edges = 0
    for word, clauses, query, proof, motif_key, depth, canonical_count in measured:
        hits = heldout_motif_hits(
            clauses, (query,), references,
            max_fact_checks=_MAX_FACT_CHECKS, max_derivations=_MAX_DERIVATIONS,
            max_proof_steps=_MAX_PROOF_STEPS, max_orientations=_MAX_ORIENTATIONS,
        )
        hit_indices = sorted(next(iter(hits)))
        contained = [id_by_index[j] for j in hit_indices]
        containment_edges += len(contained)
        proper_containment_edges += sum(1 for cid in contained if cid != word)
        rows.append(
            _serialized_candidate(
                word, clauses, query, proof, motif_key, depth,
                canonical_count, contained,
            )
        )

    # Buckets by (actual depth, witness proof_steps), ascending.
    bucket_map: dict[tuple[int, int], list[str]] = {}
    for word, clauses, query, proof, motif_key, depth, canonical_count in measured:
        bucket_map.setdefault((depth, len(proof)), []).append(motif_key)
    buckets = []
    for (depth, proof_steps), keys in sorted(bucket_map.items()):
        buckets.append({
            "depth": depth,
            "proof_steps": proof_steps,
            "candidate_count": len(keys),
            "distinct_motif_count": len(set(keys)),
        })

    summary = {
        "candidate_count": len(measured),
        "distinct_motif_count": len({m[4] for m in measured}),
        "containment_edges": containment_edges,
        "proper_containment_edges": proper_containment_edges,
    }

    return {
        "schema_version": "motif_candidate_audit_v1",
        "candidate_family": "left_spine_ops_v1",
        "matching": "complete_rooted_support_subtree",
        "budgets": {
            "max_fact_checks": _MAX_FACT_CHECKS,
            "max_derivations": _MAX_DERIVATIONS,
            "max_proof_steps": _MAX_PROOF_STEPS,
            "max_orientations": _MAX_ORIENTATIONS,
        },
        "candidates": rows,
        "buckets": buckets,
        "summary": summary,
    }


def _main() -> None:
    report = audit_motif_candidates()
    sys.stdout.write(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )


if __name__ == "__main__":
    _main()
