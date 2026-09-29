"""Versioned motif split catalogue for the T0019 fixed candidate audit.

T0020 (D41, motif_split_v1): converts the accepted T0019 finite candidate
audit into the fixed machine-readable catalogue.  This is a thin, side-effect
free transformation layer over ``audit_motif_candidates``: each call makes
exactly one no-arg call to the accepted audit, checks the ``motif_split_v1``
protocol invariants on the real values, assigns the 80 candidates to three
fixed sets by two-letter root, and emits a plain ``dict``.  No file I/O, no
stdout, no state across calls; every returned value is recomputed from the
fresh dependency call.

The 80 candidates are the complete fixed left-spine family for this version
only.  This is not a general graph split, not an automatic search for a
better split, and not a data split; changing the construction family, key
equivalence, or open-boundary matching requires a protocol version bump and
a re-audit, not a repair here.
"""

from __future__ import annotations

import copy
import itertools
import json
import sys

from kmesh.logic.motif_candidates import audit_motif_candidates

__all__ = ["build_motif_split_catalogue"]

# ---------------------------------------------------------------------------
# Protocol literals (fixed by motif_split_v1 / the T0019 contract).
# ---------------------------------------------------------------------------
_SCHEMA_VERSION = "motif_candidate_audit_v1"
_CATALOGUE_VERSION = "motif_split_catalogue_v1"
_SPLIT_PROTOCOL = "motif_split_v1"
_RESEARCH_PROTOCOL = "e0_v3"
_CANDIDATE_FAMILY = "left_spine_ops_v1"
_MATCHING = "complete_rooted_support_subtree"
_BUDGETS = {
    "max_fact_checks": 100_000,
    "max_derivations": 100_000,
    "max_proof_steps": 100_000,
    "max_orientations": 100_000,
}
# Split name -> fixed two-letter roots, in directory order.
_SPLITS = (
    ("train", ("CJ", "CT", "IC", "II", "JC", "JI", "TJ", "TT")),
    ("dev_composition", ("CC", "IJ", "JT", "TI")),
    ("test_composition", ("CI", "IT", "JJ", "TC")),
)
# Protocol section 4: (depth, proof_steps) -> {set_name: cell}.
# Each cell is simultaneously that set's row count and distinct-key count for
# the (depth, proof_steps) bucket.
_BUCKET_TABLE = {
    (2, 3): {"train": 2, "dev_composition": 1, "test_composition": 1},
    (2, 4): {"train": 4, "dev_composition": 2, "test_composition": 2},
    (2, 5): {"train": 2, "dev_composition": 1, "test_composition": 1},
    (3, 4): {"train": 4, "dev_composition": 2, "test_composition": 2},
    (3, 5): {"train": 12, "dev_composition": 6, "test_composition": 6},
    (3, 6): {"train": 12, "dev_composition": 6, "test_composition": 6},
    (3, 7): {"train": 4, "dev_composition": 2, "test_composition": 2},
}
_BUCKET_ORDER = tuple(sorted(_BUCKET_TABLE))
_ERROR = "motif_split candidate audit violates motif_split_v1"
# Fixed 80 candidate IDs in T0019 directory order (all 2-letters, then
# all 3-letters over C/I/J/T).
_FIXED_IDS = tuple(
    ["".join(p) for p in itertools.product("CIJT", repeat=2)]
    + ["".join(p) for p in itertools.product("CIJT", repeat=3)]
)
_ROOT_TO_SPLIT = {root: name for name, roots in _SPLITS for root in roots}
_SPLITS_NAMES = [name for name, _ in _SPLITS]
_SPLIT_INDEX = {name: i for i, (name, _) in enumerate(_SPLITS)}
_ID_TO_SPLIT = {wid: _ROOT_TO_SPLIT[wid[:2]] for wid in _FIXED_IDS}
_ID_INDEX = {wid: i for i, wid in enumerate(_FIXED_IDS)}


def _key_tuple(key):
    """Convert the nested-list motif key to a hashable nested tuple."""
    if isinstance(key, list):
        return tuple(_key_tuple(x) for x in key)
    return key


def _is_real_int(value):
    """True only for genuine ``int`` objects (bool and int subclasses fail)."""
    return type(value) is int


def build_motif_split_catalogue() -> dict:
    """Build the motif_split_v1 catalogue from a fresh T0019 audit.

    Exactly one no-arg call to ``audit_motif_candidates``; every value comes
    from that call.  Raises ``RuntimeError`` (``_ERROR``) when any protocol
    invariant is violated; upstream exceptions propagate unchanged (no retry,
    no partial output).
    """
    report = audit_motif_candidates()

    # ---- upstream contract -----------------------------------------------
    if report.get("schema_version") != _SCHEMA_VERSION:
        raise RuntimeError(_ERROR)
    if report.get("candidate_family") != _CANDIDATE_FAMILY:
        raise RuntimeError(_ERROR)
    if report.get("matching") != _MATCHING:
        raise RuntimeError(_ERROR)
    if report.get("budgets") != _BUDGETS:
        raise RuntimeError(_ERROR)

    rows = report.get("candidates")
    if not isinstance(rows, list) or len(rows) != len(_FIXED_IDS):
        raise RuntimeError(_ERROR)
    ids = [r["id"] for r in rows]
    if ids != list(_FIXED_IDS):
        raise RuntimeError(_ERROR)

    # ---- per-row verification, accumulating counts -------------------------
    per = []
    browc = {name: {} for name in _SPLITS_NAMES}
    bkeys = {name: {} for name in _SPLITS_NAMES}
    edge = {(si, tj): 0 for si in range(3) for tj in range(3)}
    for row in rows:
        wid = row["id"]
        split = _ID_TO_SPLIT[wid]
        depth = row["minimum_depth"]
        if not _is_real_int(depth) or depth != len(wid):
            raise RuntimeError(_ERROR)
        steps = row["proof_steps"]
        if not _is_real_int(steps) or steps != len(row["proof"]):
            raise RuntimeError(_ERROR)
        count = row["canonical_proof_count"]
        if not _is_real_int(count) or count != 1:
            raise RuntimeError(_ERROR)
        key = _key_tuple(row["motif_key"])

        cid = row["contained_ids"]
        if not isinstance(cid, list):
            raise RuntimeError(_ERROR)
        seen = set()
        for x in cid:
            if x not in _ID_INDEX:          # only known IDs
                raise RuntimeError(_ERROR)
            if x in seen:                   # no duplicates
                raise RuntimeError(_ERROR)
            seen.add(x)
            if _ID_TO_SPLIT[x] != split:    # same split only
                raise RuntimeError(_ERROR)
        if wid not in seen:                 # self always present
            raise RuntimeError(_ERROR)
        idxs = [_ID_INDEX[x] for x in cid]
        if idxs != sorted(idxs):            # global directory order
            raise RuntimeError(_ERROR)

        ks = (depth, steps)
        browc[split][ks] = browc[split].get(ks, 0) + 1
        bkeys[split].setdefault(ks, set()).add(key)
        src = _SPLIT_INDEX[split]
        for x in cid:
            edge[(src, _SPLIT_INDEX[_ID_TO_SPLIT[x]])] += 1
        per.append({"id": wid, "split": split, "key": key,
                    "row": row, "cid": cid, "depth": depth, "steps": steps})

    # ---- key uniqueness (all 80) and cross-split disjointness --------------
    all_keys = [p["key"] for p in per]
    if len(set(all_keys)) != len(all_keys):
        raise RuntimeError(_ERROR)
    key_sets = [set() for _ in _SPLITS_NAMES]
    for p in per:
        key_sets[_SPLIT_INDEX[p["split"]]].add(p["key"])
    for i in range(3):
        for j in range(i + 1, 3):
            if key_sets[i] & key_sets[j]:
                raise RuntimeError(_ERROR)

    # ---- bucket table verification (protocol literals, not observed) -------
    for (d, s), cells in _BUCKET_TABLE.items():
        for name, expected in cells.items():
            rowc = browc[name].get((d, s), 0)
            dkc = len(bkeys[name].get((d, s), set()))
            if rowc != expected or dkc != expected:
                raise RuntimeError(_ERROR)
    for name in _SPLITS_NAMES:
        for ks in browc[name]:
            if ks not in _BUCKET_TABLE:
                raise RuntimeError(_ERROR)

    # ---- assemble output ---------------------------------------------------
    candidates = []
    for p in per:
        nr = copy.deepcopy(p["row"])       # full independent copy; the audit
        nr["split"] = p["split"]           # report is never mutated or shared
        candidates.append(nr)

    splits = []
    for i, (name, roots) in enumerate(_SPLITS):
        ids_here = [p["id"] for p in per if p["split"] == name]
        splits.append({
            "name": name,
            "root_ids": list(roots),
            "candidate_ids": ids_here,
            "candidate_count": len(ids_here),
            "distinct_motif_count": len(key_sets[i]),
            "buckets": [
                {
                    "depth": d,
                    "proof_steps": s,
                    "candidate_count": browc[name].get((d, s), 0),
                    "distinct_motif_count": len(bkeys[name].get((d, s), set())),
                }
                for (d, s) in _BUCKET_ORDER
            ],
        })

    matrix = [
        {
            "source_split": src,
            "target_split": tgt,
            "edge_count": edge[(_SPLIT_INDEX[src], _SPLIT_INDEX[tgt])],
        }
        for src in _SPLITS_NAMES
        for tgt in _SPLITS_NAMES
    ]

    containment_edges = sum(len(p["cid"]) for p in per)
    return {
        "schema_version": _CATALOGUE_VERSION,
        "split_protocol": _SPLIT_PROTOCOL,
        "research_protocol": _RESEARCH_PROTOCOL,
        "candidate_family": _CANDIDATE_FAMILY,
        "matching": _MATCHING,
        "budgets": dict(report["budgets"]),
        "candidates": candidates,
        "splits": splits,
        "containment_matrix": matrix,
        "summary": {
            "candidate_count": len(per),
            "distinct_motif_count": len(all_keys),
            "containment_edges": containment_edges,
            "proper_containment_edges": containment_edges - len(per),
            "cross_split_edges": sum(
                edge[(si, tj)] for si in range(3) for tj in range(3) if si != tj
            ),
        },
    }


def _main() -> None:
    catalogue = build_motif_split_catalogue()
    sys.stdout.write(
        json.dumps(catalogue, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    )


if __name__ == "__main__":
    _main()
