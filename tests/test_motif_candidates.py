"""Behavior tests for ``kmesh.logic.motif_candidates`` (T0019).

These tests verify the fixed 80-candidate left-spine motif audit through its
public interface only.  They are independent oracles: hand-written witnesses
for the anchors, reconstructed-from-JSON witnesses for the full directory,
spies around the accepted dependency bindings for call/observation/field
participation, injected failure sentinels for propagation, isolated subprocess
checks for determinism and import isolation, and transformation invariance for
the structure key.  The tests do not import any planning probe and do not use
the product's private constructors to generate expected values.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from itertools import product
from pathlib import Path

import pytest

from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.proof_count import count_canonical_proofs
from kmesh.logic.depth import minimum_proof_depth
from kmesh.logic.motif import canonical_motif_key
from kmesh.logic.types import Atom, Clause, LogicValidationError

import kmesh.logic.motif_candidates as mcp

_MAX_FACT_CHECKS = 100_000
_MAX_DERIVATIONS = 100_000
_MAX_PROOF_STEPS = 100_000
_MAX_ORIENTATIONS = 100_000


# -----------------------------------------------------------------------------
# Hand-written anchor witnesses (independent oracles).  These are written out
# explicitly in the test; they are not generated from planning_probe or the
# product's private constructor.
# -----------------------------------------------------------------------------
def _atom(pred: str, x: str, y: str) -> Atom:
    return Atom(pred, (x, y))


def _fact(pred: str, x: str, y: str) -> Clause:
    return Clause((), _atom(pred, x, y))


def _copy_clause(pred: str, dst: str) -> Clause:
    return Clause((_atom(pred, "?x", "?y"),), _atom(dst, "?x", "?y"))


def _inv_clause(pred: str, dst: str) -> Clause:
    return Clause((_atom(pred, "?x", "?y"),), _atom(dst, "?y", "?x"))


def _join_clause(pred: str, side: str, dst: str) -> Clause:
    return Clause(
        (_atom(pred, "?x", "?y"), _atom(side, "?y", "?z")),
        _atom(dst, "?x", "?z"),
    )


def _inter_clause(pred: str, side: str, dst: str) -> Clause:
    return Clause(
        (_atom(pred, "?x", "?y"), _atom(side, "?x", "?y")),
        _atom(dst, "?x", "?y"),
    )


def _base_step() -> ProofStep:
    return ProofStep(0, (), _atom("p0", "e0", "e1"))


_W_CC = (
    (_fact("p0", "e0", "e1"), _copy_clause("p0", "p1"), _copy_clause("p1", "p2")),
    _atom("p2", "e0", "e1"),
    (_base_step(),
     ProofStep(1, (0,), _atom("p1", "e0", "e1")),
     ProofStep(2, (1,), _atom("p2", "e0", "e1"))),
)

_W_II = (
    (_fact("p0", "e0", "e1"), _inv_clause("p0", "p1"), _inv_clause("p1", "p2")),
    _atom("p2", "e0", "e1"),
    (_base_step(),
     ProofStep(1, (0,), _atom("p1", "e1", "e0")),
     ProofStep(2, (1,), _atom("p2", "e0", "e1"))),
)

_W_CJ = (
    (_fact("p0", "e0", "e1"), _copy_clause("p0", "p1"),
     _fact("s2", "e1", "e3"), _join_clause("p1", "s2", "p2")),
    _atom("p2", "e0", "e3"),
    (_base_step(),
     ProofStep(1, (0,), _atom("p1", "e0", "e1")),
     ProofStep(2, (), _atom("s2", "e1", "e3")),
     ProofStep(3, (1, 2), _atom("p2", "e0", "e3"))),
)

_W_JC = (
    (_fact("p0", "e0", "e1"), _fact("s1", "e1", "e2"),
     _join_clause("p0", "s1", "p1"), _copy_clause("p1", "p2")),
    _atom("p2", "e0", "e2"),
    (_base_step(),
     ProofStep(1, (), _atom("s1", "e1", "e2")),
     ProofStep(2, (0, 1), _atom("p1", "e0", "e2")),
     ProofStep(3, (2,), _atom("p2", "e0", "e2"))),
)

# CJC = CJ with one trailing COPY.  Built from the hand-written CJ structure
# by explicit tuple concatenation (no mutation), not from any private API.
_W_CJC = (
    _W_CJ[0] + (_copy_clause("p2", "p3"),),
    _atom("p3", "e0", "e3"),
    _W_CJ[2] + (ProofStep(4, (3,), _atom("p3", "e0", "e3")),),
)

_W_JJ = (
    (_fact("p0", "e0", "e1"), _fact("s1", "e1", "e2"),
     _join_clause("p0", "s1", "p1"),
     _fact("s2", "e2", "e3"), _join_clause("p1", "s2", "p2")),
    _atom("p2", "e0", "e3"),
    (_base_step(),
     ProofStep(1, (), _atom("s1", "e1", "e2")),
     ProofStep(2, (0, 1), _atom("p1", "e0", "e2")),
     ProofStep(3, (), _atom("s2", "e2", "e3")),
     ProofStep(4, (2, 3), _atom("p2", "e0", "e3"))),
)

_W_TTT = (
    (_fact("p0", "e0", "e1"),
     _fact("s1", "e0", "e1"), _inter_clause("p0", "s1", "p1"),
     _fact("s2", "e0", "e1"), _inter_clause("p1", "s2", "p2"),
     _fact("s3", "e0", "e1"), _inter_clause("p2", "s3", "p3")),
    _atom("p3", "e0", "e1"),
    (_base_step(),
     ProofStep(1, (), _atom("s1", "e0", "e1")),
     ProofStep(2, (0, 1), _atom("p1", "e0", "e1")),
     ProofStep(3, (), _atom("s2", "e0", "e1")),
     ProofStep(4, (2, 3), _atom("p2", "e0", "e1")),
     ProofStep(5, (), _atom("s3", "e0", "e1")),
     ProofStep(6, (4, 5), _atom("p3", "e0", "e1"))),
)

ANCHORS = {
    "CC": _W_CC,
    "II": _W_II,
    "CJ": _W_CJ,
    "JC": _W_JC,
    "CJC": _W_CJC,
    "JJ": _W_JJ,
    "TTT": _W_TTT,
}

_EXPECTED_IDS = [
    "".join(p) for p in product("CIJT", repeat=2)
] + [
    "".join(p) for p in product("CIJT", repeat=3)
]


# -----------------------------------------------------------------------------
# JSON <-> object reconstruction helpers (used to verify the report itself).
# -----------------------------------------------------------------------------
def _from_json_atom(obj) -> Atom:
    assert isinstance(obj, dict)
    assert "pred" in obj and "args" in obj
    return Atom(obj["pred"], tuple(obj["args"]))


def _from_json_clause(obj) -> Clause:
    return Clause(
        tuple(_from_json_atom(a) for a in obj["body"]),
        _from_json_atom(obj["head"]),
    )


def _from_json_step(obj) -> ProofStep:
    return ProofStep(
        obj["clause_index"],
        tuple(obj["premise_steps"]),
        _from_json_atom(obj["conclusion"]),
    )


def _reconstruct_row(row) -> tuple[tuple[Clause, ...], Atom, tuple[ProofStep, ...]]:
    clauses = tuple(_from_json_clause(c) for c in row["clauses"])
    query = _from_json_atom(row["query"])
    proof = tuple(_from_json_step(s) for s in row["proof"])
    return clauses, query, proof


def _key_as_json(key) -> object:
    if isinstance(key, tuple):
        return [_key_as_json(item) for item in key]
    return key


def _key_as_tuple(obj) -> object:
    """Inverse of _key_as_json for hashability: nested lists -> tuples."""
    if isinstance(obj, list):
        return tuple(_key_as_tuple(x) for x in obj)
    return obj


@pytest.fixture(scope="module")
def report() -> dict:
    """One real, shared 80-candidate audit for the whole test module."""
    return mcp.audit_motif_candidates()


# -----------------------------------------------------------------------------
# Construction anchors (hand-written).
# -----------------------------------------------------------------------------
class TestConstructionAnchors:
    def test_hand_written_witnesses_are_valid(self):
        for word, (clauses, query, proof) in ANCHORS.items():
            assert verify_proof(clauses, query, proof), word
            assert len(proof) == len(clauses), word
            # every witness is a full occurrence tree, not a single conclusion
            assert proof[-1].conclusion == query, word

    def test_hand_written_anchor_shape(self):
        for word, (clauses, query, proof) in ANCHORS.items():
            steps = len(proof)
            if word == "TTT":
                assert (steps, minimum_proof_depth(clauses, query),
                        count_canonical_proofs(clauses, query)) == (7, 3, 1)
            else:
                assert steps in (3, 4, 5)
                # depth equals word length
                assert minimum_proof_depth(clauses, query) == len(word)
                assert count_canonical_proofs(clauses, query) == 1

    def test_reconstructed_report_rows_match_hand_written_witnesses(self, report):
        """Full sequence and reference comparison for every anchor, which covers
        letter direction, side predicate, fresh entity and final query."""
        rows_by_id = {r["id"]: r for r in report["candidates"]}
        for word, (clauses, query, proof) in ANCHORS.items():
            assert word in rows_by_id, f"missing candidate {word!r}"
            rc, rq, rp = _reconstruct_row(rows_by_id[word])
            assert clauses == rc, f"clauses mismatch for {word}"
            assert query == rq, f"query mismatch for {word}"
            assert proof == rp, f"proof (steps/references) mismatch for {word}"

    def test_cj_cjc_full_sequence_and_reference(self, report):
        """CJ/CJC specifically: full clause list and full premise-step
        reference sequence, plus direction (CJ vs JC) and fresh side entity."""
        for word in ("CJ", "CJC", "JC"):
            clauses, query, proof = ANCHORS[word]
            row = next(r for r in report["candidates"] if r["id"] == word)
            rcl, rqu, rpf = _reconstruct_row(row)
            assert clauses == rcl
            assert query == rqu
            assert proof == rpf
        # The side-fact predicates (empty-body fact clauses) differ: CJ
        # introduces s2 (its join uses a fresh s2 fact), JC introduces s1.
        cj_side_facts = {c.head.pred for c in ANCHORS["CJ"][0]
                         if not c.body and c.head.pred.startswith("s")}
        jc_side_facts = {c.head.pred for c in ANCHORS["JC"][0]
                         if not c.body and c.head.pred.startswith("s")}
        assert cj_side_facts == {"s2"}, cj_side_facts
        assert jc_side_facts == {"s1"}, jc_side_facts
        # CJC has exactly one extra COPY step after CJ.
        cj_proof = ANCHORS["CJ"][2]
        cjc_proof = ANCHORS["CJC"][2]
        assert len(cjc_proof) == len(cj_proof) + 1
        assert cjc_proof[:-1] == cj_proof
        assert cjc_proof[-1].clause_index == len(ANCHORS["CJC"][0]) - 1


# -----------------------------------------------------------------------------
# Full directory and real witnesses.
# -----------------------------------------------------------------------------
class TestDirectoryAndRealWitnesses:
    def test_eighty_ids_in_fixed_order(self, report):
        ids = [r["id"] for r in report["candidates"]]
        assert ids == _EXPECTED_IDS
        assert len(ids) == 80
        assert ids[0] == "CC"
        assert ids[-1] == "TTT"

    def test_all_witnesses_reconstruct_and_verify(self, report):
        """Reconstruct every witness from JSON and run the independent verifier
        over the full proof (not just the final step)."""
        for row in report["candidates"]:
            clauses, query, proof = _reconstruct_row(row)
            assert verify_proof(clauses, query, proof), row["id"]
            assert len(proof) == row["proof_steps"], row["id"]
            # clause indices / premise references are real and in-range
            for s in proof:
                assert s.clause_index < len(clauses), row["id"]
                for ref in s.premise_steps:
                    assert ref < len(proof), row["id"]

    def test_recheck_key_count_depth_against_accepted_api(self, report):
        """Re-run the accepted APIs on the reconstructed witnesses and require
        the report values to match the real API results (no mirroring)."""
        for row in report["candidates"]:
            clauses, query, proof = _reconstruct_row(row)
            key = canonical_motif_key(
                clauses, query, proof,
                max_steps=_MAX_PROOF_STEPS, max_orientations=_MAX_ORIENTATIONS,
            )
            count = count_canonical_proofs(
                clauses, query,
                max_fact_checks=_MAX_FACT_CHECKS, max_derivations=_MAX_DERIVATIONS,
                max_proof_steps=_MAX_PROOF_STEPS,
            )
            depth = minimum_proof_depth(
                clauses, query,
                max_fact_checks=_MAX_FACT_CHECKS, max_derivations=_MAX_DERIVATIONS,
            )
            assert row["motif_key"] == _key_as_json(key), row["id"]
            assert row["canonical_proof_count"] == count, row["id"]
            assert row["minimum_depth"] == depth, row["id"]


# -----------------------------------------------------------------------------
# Structure and containment.
# -----------------------------------------------------------------------------
class TestStructureAndContainment:
    def test_summary_counts(self, report):
        summary = report["summary"]
        assert summary == {
            "candidate_count": 80,
            "distinct_motif_count": 80,
            "containment_edges": 144,
            "proper_containment_edges": 64,
        }
        # independent recount from contained_ids
        edges = sum(len(r["contained_ids"]) for r in report["candidates"])
        proper = sum(
            1 for r in report["candidates"]
            for cid in r["contained_ids"] if cid != r["id"]
        )
        assert edges == 144
        assert proper == 64
        # independent recount: distinct full keys must match the summary
        assert summary["distinct_motif_count"] == len(
            {_key_as_tuple(r["motif_key"]) for r in report["candidates"]}
        )

    def test_buckets_exact(self, report):
        expected = [
            {"depth": 2, "proof_steps": 3, "candidate_count": 4,
             "distinct_motif_count": 4},
            {"depth": 2, "proof_steps": 4, "candidate_count": 8,
             "distinct_motif_count": 8},
            {"depth": 2, "proof_steps": 5, "candidate_count": 4,
             "distinct_motif_count": 4},
            {"depth": 3, "proof_steps": 4, "candidate_count": 8,
             "distinct_motif_count": 8},
            {"depth": 3, "proof_steps": 5, "candidate_count": 24,
             "distinct_motif_count": 24},
            {"depth": 3, "proof_steps": 6, "candidate_count": 24,
             "distinct_motif_count": 24},
            {"depth": 3, "proof_steps": 7, "candidate_count": 8,
             "distinct_motif_count": 8},
        ]
        assert report["buckets"] == expected

    def test_contained_ids_match_prefix_derivation(self, report):
        """Derived expectation: 2-letter words hit only themselves; 3-letter
        words hit their 2-letter prefix plus themselves, in directory order.
        No same-depth cross-edges.  This is an expectation checked against the
        computed contained_ids, not a value the product hard-codes."""
        for row in report["candidates"]:
            w = row["id"]
            if len(w) == 2:
                assert row["contained_ids"] == [w], w
            else:
                assert row["contained_ids"] == [w[:2], w], w

    def test_cc_ii_same_query_different_keys(self, report):
        cc = next(r for r in report["candidates"] if r["id"] == "CC")
        ii = next(r for r in report["candidates"] if r["id"] == "II")
        assert cc["query"] == ii["query"]  # same ground endpoint p2(e0,e1)
        assert cc["motif_key"] != ii["motif_key"]

    def test_cj_jc_same_length_depth_different_keys(self, report):
        cj = next(r for r in report["candidates"] if r["id"] == "CJ")
        jc = next(r for r in report["candidates"] if r["id"] == "JC")
        assert cj["minimum_depth"] == jc["minimum_depth"]
        assert cj["proof_steps"] == jc["proof_steps"]
        assert cj["query"] != jc["query"]
        assert cj["motif_key"] != jc["motif_key"]
        # queries land on different endpoints
        assert cj["query"]["args"] == ["e0", "e3"]
        assert jc["query"]["args"] == ["e0", "e2"]

    def test_cjc_contains_cj_not_jc(self, report):
        cjc = next(r for r in report["candidates"] if r["id"] == "CJC")
        assert "CJ" in cjc["contained_ids"]
        assert "JC" not in cjc["contained_ids"]
        assert cjc["contained_ids"] == ["CJ", "CJC"]


# -----------------------------------------------------------------------------
# Spy machinery over the product's accepted dependency bindings.
# -----------------------------------------------------------------------------
@contextmanager
def _spy_four(cm_ret=None, cp_ret=None, dp_ret=None, hm_ret=None):
    """Wrap the four product bindings with recording spies.

    Each ret is ``None`` (passthrough to the real function) or a value or
    callable.  ``None`` always delegates to the real implementation so the
    rest of the report is still produced.
    """
    rets = {
        "canonical_motif_key": cm_ret,
        "count_canonical_proofs": cp_ret,
        "minimum_proof_depth": dp_ret,
        "heldout_motif_hits": hm_ret,
    }
    real = {name: getattr(mcp, name) for name in rets}
    rec = {name: [] for name in rets}
    for name, ret in rets.items():
        if ret is None:
            ret = real[name]
        lst = rec[name]
        fn = real[name]

        def make(fn=fn, ret=ret, lst=lst):
            def spy(*a, **kw):
                lst.append({"args": a, "kwargs": kw})
                if callable(ret):
                    return ret(*a, **kw)
                return ret
            return spy

        setattr(mcp, name, make())
    try:
        yield rec
    finally:
        for name, fn in real.items():
            setattr(mcp, name, fn)


def _kw(**kw):
    return dict(kw)


class TestDependencyObserved:
    def test_each_api_called_per_candidate_with_fixed_budgets(self):
        with _spy_four() as rec:
            report = mcp.audit_motif_candidates()
        assert report["summary"]["candidate_count"] == 80
        assert len(rec["canonical_motif_key"]) == 80
        assert len(rec["count_canonical_proofs"]) == 80
        assert len(rec["minimum_proof_depth"]) == 80
        assert len(rec["heldout_motif_hits"]) == 80
        for c in rec["canonical_motif_key"]:
            assert c["kwargs"] == _kw(
                max_steps=_MAX_PROOF_STEPS, max_orientations=_MAX_ORIENTATIONS)
            assert len(c["args"]) == 3
        for c in rec["count_canonical_proofs"]:
            assert c["kwargs"] == _kw(
                max_fact_checks=_MAX_FACT_CHECKS, max_derivations=_MAX_DERIVATIONS,
                max_proof_steps=_MAX_PROOF_STEPS)
        for c in rec["minimum_proof_depth"]:
            assert c["kwargs"] == _kw(
                max_fact_checks=_MAX_FACT_CHECKS, max_derivations=_MAX_DERIVATIONS)
        for c in rec["heldout_motif_hits"]:
            assert c["kwargs"] == _kw(
                max_fact_checks=_MAX_FACT_CHECKS, max_derivations=_MAX_DERIVATIONS,
                max_proof_steps=_MAX_PROOF_STEPS, max_orientations=_MAX_ORIENTATIONS)
            args = c["args"]
            assert len(args) == 3
            # single-query batch
            queries = args[1]
            assert isinstance(queries, tuple) and len(queries) == 1

    def test_references_full_80_in_directory_order_and_shared(self):
        with _spy_four() as rec:
            mcp.audit_motif_candidates()
        cp_calls = rec["count_canonical_proofs"]
        hm_calls = rec["heldout_motif_hits"]
        clauses_by_i = [c["args"][0] for c in cp_calls]
        queries_by_i = [c["args"][1] for c in cp_calls]
        assert len(cp_calls) == 80
        assert len(hm_calls) == 80
        refs = hm_calls[0]["args"][2]
        # one references tuple object, reused for all 80 target calls
        assert all(c["args"][2] is refs for c in hm_calls)
        assert len(refs) == 80
        for j in range(80):
            ref = refs[j]
            assert len(ref) == 3
            # reference j has the same clauses and query as candidate j
            assert ref[0] == clauses_by_i[j]
            assert ref[1] == queries_by_i[j]
            # reference j is an independently verified complete witness
            assert verify_proof(ref[0], ref[1], ref[2])
        # target call k is (clauses_k, (query_k,), shared_refs)
        for k in range(80):
            args = hm_calls[k]["args"]
            assert args[0] == clauses_by_i[k]
            assert args[1] == (queries_by_i[k],)

    def test_count_field_participates_not_hardcoded(self):
        with _spy_four(cp_ret=42) as rec:
            report = mcp.audit_motif_candidates()
        for row in report["candidates"]:
            assert row["canonical_proof_count"] == 42
        assert report["summary"]["candidate_count"] == 80

    def test_depth_field_participates_not_word_length(self):
        with _spy_four(dp_ret=17) as rec:
            report = mcp.audit_motif_candidates()
        for row in report["candidates"]:
            assert row["minimum_depth"] == 17
            # depth must not fall back to len(id)
            assert row["minimum_depth"] != len(row["id"])

    def test_key_field_drives_distinct_count(self):
        counter = {"n": 0}

        def fake_cm(*a, **kw):
            counter["n"] += 1
            # first two candidates share one key; the rest are distinct
            return ("fake_key_v1", 0 if counter["n"] <= 2 else counter["n"])

        with _spy_four(cm_ret=fake_cm) as rec:
            report = mcp.audit_motif_candidates()
        # distinct drops by exactly 1 (80 -> 79)
        assert report["summary"]["distinct_motif_count"] == 79
        assert len(rec["canonical_motif_key"]) == 80

    def test_hits_field_maps_into_contained_ids(self):
        def fake_hm(*a, **kw):
            # always hit the last directory reference (index 79 = "TTT")
            return (frozenset({79}),)

        with _spy_four(hm_ret=fake_hm) as rec:
            report = mcp.audit_motif_candidates()
        for row in report["candidates"]:
            assert row["contained_ids"] == ["TTT"], row["id"]


# -----------------------------------------------------------------------------
# Failure propagation (not faked as success).
# -----------------------------------------------------------------------------
class TestFailureNotFaked:
    """Inject dependency-supported exceptions at a later candidate's call and
    require the original instance (class, message, cause, context) to propagate
    with no later calls and no partial success.  Every dependency supports
    ``LogicValidationError``; we attach a meaningful cause and context to the
    raised instance and verify both survive unchanged (not just the instance).
    """

    _BOUNDINGS = {
        "count_canonical_proofs": "sentinel_count_fail",
        "minimum_proof_depth": "sentinel_depth_fail",
        "canonical_motif_key": "sentinel_key_fail",
        "heldout_motif_hits": "sentinel_hits_fail",
    }

    def _patch_and_run(self, name, raise_idx):
        real = getattr(mcp, name)
        seen_n = {"n": 0}
        label = name.replace(".", "_")
        exc = LogicValidationError(f"{self._BOUNDINGS[name]}_{raise_idx}")
        # Message saved before the audit is invoked; only this pre-call string
        # is compared below, so a wrapper rewriting exc.args after capture is
        # rejected (comparing str(exc) after the call compares the same instance
        # against its own, possibly altered, message and passes falsely).
        msg_before = str(exc)
        # meaningful, distinct cause and context sentinels
        cause = RuntimeError(f"{label}_cause_marker")
        context = LogicValidationError(f"{label}_context_marker")
        exc.__cause__ = cause
        exc.__context__ = context

        def spy(*a, **kw):
            seen_n["n"] += 1
            if seen_n["n"] == raise_idx:
                raise exc
            return real(*a, **kw)

        old = getattr(mcp, name)
        setattr(mcp, name, spy)
        with pytest.raises(LogicValidationError) as excinfo:
            mcp.audit_motif_candidates()
        setattr(mcp, name, old)
        return excinfo, exc, msg_before, cause, context, seen_n

    def _assert_propagation(self, excinfo, exc, msg_before, cause, context):
        # class, message against the pre-call string, instance identity, and
        # preserved cause/context (used by all four bindings)
        assert isinstance(excinfo.value, LogicValidationError)
        assert str(excinfo.value) == msg_before
        assert excinfo.value is exc
        # cause and context must be the SAME instances we attached (preserved)
        assert excinfo.value.__cause__ is cause
        assert excinfo.value.__context__ is context

    def test_count_exception_propagates(self):
        excinfo, exc, msg, cause, context, seen = self._patch_and_run("count_canonical_proofs", 41)
        self._assert_propagation(excinfo, exc, msg, cause, context)
        assert seen["n"] == 41  # 40 passes + 1 raise, nothing after

    def test_depth_exception_propagates(self):
        excinfo, exc, msg, cause, context, seen = self._patch_and_run("minimum_proof_depth", 41)
        self._assert_propagation(excinfo, exc, msg, cause, context)
        assert seen["n"] == 41

    def test_key_exception_propagates(self):
        excinfo, exc, msg, cause, context, seen = self._patch_and_run("canonical_motif_key", 41)
        self._assert_propagation(excinfo, exc, msg, cause, context)
        assert seen["n"] == 41

    def test_hits_exception_propagates_and_stops(self):
        excinfo, exc, msg, cause, context, seen = self._patch_and_run("heldout_motif_hits", 41)
        self._assert_propagation(excinfo, exc, msg, cause, context)
        assert seen["n"] == 41  # no heldout calls after the failure

    def test_cli_failure_writes_no_partial_json(self):
        """Run the real module entry in a child with a late injected failure.
        The blocker is installed before _main and retained throughout; require
        non-zero exit, sentinel+traceback on stderr and empty (no partial) stdout."""
        repo_root = Path(__file__).resolve().parents[1]
        src = repo_root / "src"
        env = _child_env()
        script = _child_script(
            src,
            "import kmesh.logic.motif_candidates as m\n"
            "from kmesh.logic.types import LogicValidationError\n"
            "real = m.canonical_motif_key\n"
            "seen = {'n': 0}\n"
            "def fake(*a, **kw):\n"
            "    seen['n'] += 1\n"
            "    if seen['n'] > 10:\n"
            "        raise LogicValidationError('cli_fail_sentinel_idx11')\n"
            "    return real(*a, **kw)\n"
            "m.canonical_motif_key = fake\n"
            "m._main()\n",
            footer_asserts=False,
        )
        out = subprocess.run([sys.executable, "-I", "-B", "-c", script], env=env,
                             capture_output=True, text=True, timeout=600)
        assert out.returncode != 0, f"exit={out.returncode}"
        assert "cli_fail_sentinel_idx11" in out.stderr
        assert "Traceback" in out.stderr
        # no partial JSON, no success marker on stdout
        assert out.stdout.strip() == ""


# -----------------------------------------------------------------------------
# Determinism and isolation.
# -----------------------------------------------------------------------------
def _child_env():
    """Environment for the -I -B child.  -I ignores PYTHONPATH, so the worktree
    src is inserted inside the child itself; there is no PYTHONPATH here.  Bytecode
    writing is disabled explicitly."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def _child_script(src, body, tail=None, footer_asserts=True):
    """Assemble the -I -B child script.

    Every child explicitly puts this worktree's src first on sys.path, asserts
    the actual product path (the kmesh.logic.motif_candidates product path,
    in addition to the package file: both the module file and the resolved
    ``__spec__.origin`` must real-path to the worktree file, which rejects an
    in-memory module merely claiming the path), installs a self-tested import
    blocker (all four forbidden roots + dotted prefixes) before the product
    import and retains it throughout the audit, and scans sys.modules before
    and after the operation.  The runpy CLI child additionally verifies the
    executed namespace: the globals dict in which the module ran as
    ``__main__`` must carry the product's resolved origin via ``__spec__`` and
    ``__file__``.  The product must not import a forbidden root; a probe doing
    so during import or during the audit fails the child.
    """
    src_str = str(src)
    types_real = str(src / "kmesh" / "logic" / "types.py")
    motif_real = str(src / "kmesh" / "logic" / "motif_candidates.py")
    header = (
        "import sys, os, importlib\n"
        f"sys.path.insert(0, {repr(src_str)})\n"
        "import kmesh.logic.types as _kt\n"
        f"assert os.path.realpath(_kt.__file__) == {repr(types_real)}, _kt.__file__\n"
        "FORBIDDEN = ('torch', 'yaml', 'kmesh.logic.engine',"
        "'kmesh.logic.reference_engine')\n"
        "class BlockFinder:\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        for f in FORBIDDEN:\n"
        "            if fullname == f or fullname.startswith(f + '.'):\n"
        "                raise ImportError('forbidden-import: ' + fullname)\n"
        "        return None\n"
        "sys.meta_path.insert(0, BlockFinder())\n"
        "def _assert_blocked(name):\n"
        "    try:\n"
        "        importlib.import_module(name)\n"
        "    except ImportError as e:\n"
        "        assert 'forbidden-import: ' in str(e), (name, e)\n"
        "        return\n"
        "    raise AssertionError('forbidden ' + name + ' imported despite blocker')\n"
        "for name in FORBIDDEN + ('torch.sub', 'kmesh.logic.engine.sub',"
        "'kmesh.logic.reference_engine.sub'):\n"
        "    _assert_blocked(name)\n"
        "import kmesh.logic.motif_candidates as _pm\n"
        f"assert os.path.realpath(_pm.__file__) == {repr(motif_real)}, _pm.__file__\n"
        "assert _pm.__spec__ is not None, _pm.__spec__\n"
        f"assert os.path.realpath(_pm.__spec__.origin) == {repr(motif_real)}, _pm.__spec__.origin\n"
        "def _bad():\n"
        "    return [n for n in sys.modules if any("
        "n == f or n.startswith(f + '.') for f in FORBIDDEN)]\n"
        "before = _bad()\n"
        "assert before == [], before\n"
    )
    if footer_asserts:
        footer = (
            "assert _bad() == before, _bad()\n"
            "assert isinstance(sys.meta_path[0], BlockFinder)\n"
        )
        if tail:
            footer += f"print('{tail}')\n"
    else:
        footer = ""
    return header + body + footer




class TestDeterminismAndIsolation:
    def test_audit_call_writes_no_stdout(self):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            mcp.audit_motif_candidates()
        finally:
            sys.stdout = old
        assert buf.getvalue() == ""

    def test_repeated_calls_not_shared_mutable_state(self):
        # Independent serialized baseline: the comparison target must not be a
        # returned report, whose nested containers the product might otherwise
        # share; with a shared shallow copy the mutations below would corrupt the
        # baseline and the test would pass falsely.
        base = mcp.audit_motif_candidates()
        base_snapshot = json.loads(json.dumps(base, ensure_ascii=False))
        a = mcp.audit_motif_candidates()
        b = mcp.audit_motif_candidates()
        assert a == base_snapshot
        assert b == base_snapshot
        assert a is not base
        assert b is not base
        assert a is not b
        # Mutate one returned report; a fresh audit must be unaffected (repeated
        # calls return independent copies, not one shared global report).
        a["candidates"][0]["id"] = "MUTATED-CC"
        a["summary"]["candidate_count"] = 79
        b["buckets"].append({"depth": 99, "proof_steps": 99,
                            "candidate_count": 99, "distinct_motif_count": 99})
        c = mcp.audit_motif_candidates()
        d = mcp.audit_motif_candidates()
        assert c == base_snapshot, c
        assert d == base_snapshot, d
        assert c is not a
        assert d is not c

    def test_subprocess_byte_identical_and_valid_json(self):
        repo_root = Path(__file__).resolve().parents[1]
        src = repo_root / "src"
        motif_real = str(src / "kmesh" / "logic" / "motif_candidates.py")
        env = _child_env()
        # The shared header has already imported the product (and asserted
        # its path).  runpy re-executes it as __main__; it emits one
        # harmless RuntimeWarning that the module was already in sys.modules.
        # Suppress only that known, benign warning so the child's stderr stays
        # empty; any other warning still surfaces.
        script = _child_script(
            src,
            "import runpy\n"
            "import warnings\n"
            "with warnings.catch_warnings():\n"
            "    warnings.filterwarnings('ignore', message=\".+' found in sys\\\\.modules after import of package\")\n"
            "    main_ns = runpy.run_module('kmesh.logic.motif_candidates', run_name='__main__')\n"
            "assert main_ns['__name__'] == '__main__', main_ns['__name__']\n"
            "run_spec = main_ns['__spec__']\n"
            "assert run_spec is not None, run_spec\n"
            f"assert os.path.realpath(run_spec.origin) == {repr(motif_real)}, run_spec.origin\n"
            f"assert os.path.realpath(main_ns['__file__']) == {repr(motif_real)}, main_ns['__file__']\n",
            tail=None,
        )
        # initial bytecode snapshot BEFORE any subprocess run
        pyc_before = {str(p) for p in src.rglob("*.pyc")}
        out1 = subprocess.run([sys.executable, "-I", "-B", "-c", script], env=env,
                              capture_output=True, text=False, timeout=600)
        out2 = subprocess.run([sys.executable, "-I", "-B", "-c", script], env=env,
                              capture_output=True, text=False, timeout=600)
        assert out1.returncode == 0
        assert out2.returncode == 0
        assert out1.stdout == out2.stdout
        assert out1.stderr == b""
        assert out1.stdout.endswith(b"\n")
        cli = json.loads(out1.stdout.decode("utf-8"))
        # the decoded CLI report equals a fresh function result
        assert cli == mcp.audit_motif_candidates()
        assert cli["schema_version"] == "motif_candidate_audit_v1"
        assert cli["summary"]["candidate_count"] == 80
        # final snapshot: the child runs created no new source bytecode
        pyc_after = {str(p) for p in src.rglob("*.pyc")}
        assert pyc_after == pyc_before, f"new pyc: {sorted(pyc_after - pyc_before)}"

    def test_import_resolves_to_worktree_src(self):
        repo_root = Path(__file__).resolve().parents[1]
        src = repo_root / "src"
        env = _child_env()
        script = _child_script(
            src,
            "import kmesh.logic.motif_candidates as m\n"
            "assert m.__spec__ is not None, m.__spec__\n"
            "assert os.path.realpath(m.__spec__.origin) == "
            + repr(str(src / "kmesh" / "logic" / "motif_candidates.py"))
            + ", m.__spec__.origin\n"
            "assert os.path.realpath(m.__file__) == "
            + repr(str(src / "kmesh" / "logic" / "motif_candidates.py"))
            + ", m.__file__\n",
            tail="OK_REALPATH",
        )
        out = subprocess.run([sys.executable, "-I", "-B", "-c", script], env=env,
                             capture_output=True, text=True, timeout=60)
        assert out.returncode == 0, out.stderr
        assert "OK_REALPATH" in out.stdout

    def test_isolated_process_import_and_audit_no_forbidden_modules(self):
        repo_root = Path(__file__).resolve().parents[1]
        src = repo_root / "src"
        env = _child_env()
        script = _child_script(
            src,
            "import kmesh.logic.motif_candidates as m\n"
            "r = m.audit_motif_candidates()\n"
            "assert r['summary']['candidate_count'] == 80\n",
            tail="OK_ISOLATION",
        )
        out = subprocess.run([sys.executable, "-I", "-B", "-c", script], env=env,
                             capture_output=True, text=True, timeout=600)
        assert out.returncode == 0, out.stderr
        assert "OK_ISOLATION" in out.stdout


# -----------------------------------------------------------------------------
# Transformation invariance for the structure key.
# -----------------------------------------------------------------------------
def _dual_map(clauses, query, proof, pred_map, const_map, var_map):
    """Rename predicates / constants / local variables via the maps; any
    symbol not in a map keeps its original spelling (identity)."""
    def _term(t):
        if t.startswith("?"):
            return var_map.get(t, t)
        return const_map.get(t, t)

    def _atom(a):
        return Atom(pred_map.get(a.pred, a.pred), (_term(a.args[0]), _term(a.args[1])))
    
    tclauses = tuple(
        Clause(tuple(_atom(x) for x in c.body), _atom(c.head))
        for c in clauses
    )
    tquery = _atom(query)
    tproof = tuple(
        ProofStep(s.clause_index, s.premise_steps, _atom(s.conclusion))
        for s in proof
    )
    return tclauses, tquery, tproof


def _swap_two_premise(clauses, query, proof):
    """Swap the two body slots of the (unique) two-premise clause and
    simultaneously swap the corresponding premise steps of the step that
    cites it.  This is exactly the joint swap the structure key normalises."""
    ci = next(i for i, c in enumerate(clauses) if len(c.body) == 2)
    si = next(i for i, s in enumerate(proof) if s.clause_index == ci)
    new_clause = Clause(tuple(reversed(clauses[ci].body)), clauses[ci].head)
    tclauses = list(clauses)
    tclauses[ci] = new_clause
    old = proof[si]
    new_proof = list(proof)
    new_proof[si] = ProofStep(
        old.clause_index, tuple(reversed(old.premise_steps)), old.conclusion
    )
    return tuple(tclauses), query, tuple(new_proof)


class TestTransformationInvariance:
    def _key(self, clauses, query, proof):
        return canonical_motif_key(
            clauses, query, proof,
            max_steps=_MAX_PROOF_STEPS, max_orientations=_MAX_ORIENTATIONS,
        )

    def test_global_relation_entity_dual_mapping_invariance(self):
        clauses, query, proof = ANCHORS["CJ"]
        base = self._key(clauses, query, proof)
        tc, tq, tp = _dual_map(
            clauses, query, proof,
            pred_map={"p0": "p90", "p1": "p91", "p2": "p92", "s2": "r92"},
            const_map={"e0": "Z0", "e1": "Z1", "e3": "Z3"},
            var_map={"?x": "?a", "?y": "?b", "?z": "?c"},
        )
        assert verify_proof(tc, tq, tp)
        assert self._key(tc, tq, tp) == base

    def test_local_variable_dual_mapping_invariance(self):
        """Rename only local variables (predicates and constants keep their
        original spellings); the structure key must be unchanged."""
        clauses, query, proof = ANCHORS["CJ"]
        base = self._key(clauses, query, proof)
        tc, tq, tp = _dual_map(
            clauses, query, proof,
            pred_map={},  # identity: keep p0/p1/p2/s2
            const_map={},  # identity: keep e0/e1/e3
            var_map={"?x": "?alpha", "?y": "?beta", "?z": "?gamma"},
        )
        assert verify_proof(tc, tq, tp)
        assert self._key(tc, tq, tp) == base

    def test_two_premise_joint_swap_invariance(self):
        clauses, query, proof = ANCHORS["CJ"]
        base = self._key(clauses, query, proof)
        sc, sq, sp = _swap_two_premise(clauses, query, proof)
        assert verify_proof(sc, sq, sp)
        assert self._key(sc, sq, sp) == base
