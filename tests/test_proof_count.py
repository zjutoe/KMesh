"""T0013 tests: ``count_canonical_proofs`` (thin T0009 + T0012 composition).

Groups A–E per the handoff.  Expected counts are hand-computed in the
fixture tables below (U0–U8 from [examples.json](../../reports/T0013/planning-examples/examples.json)),
never derived from the product under test.  Only the real T0009 enumerator
is used for cross-checks; no planning oracle / script or T0011 clause-key
oracle is imported.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import textwrap
from contextlib import contextmanager
from pathlib import Path

import pytest

from kmesh.logic import proof_count as pc
from kmesh.logic.derivations import DerivationLimitError
from kmesh.logic.proof import LogicValidationError, ProofLimitError, ProofStep
from kmesh.logic.proof_enumeration import enumerate_proofs, ProofEnumerationLimitError
from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof_count import count_canonical_proofs

__all__ = [
    "count_canonical_proofs",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _A(pred, a, b):
    return Atom(pred, (a, b))


def _fact(pred, a, b):
    return Clause((), _A(pred, a, b))


def _copy_rule(pred, head):
    return Clause((_A(pred, "?x", "?y"),), _A(head, "?x", "?y"))


def _inv_rule(pred, head):
    return Clause((_A(pred, "?x", "?y"),), _A(head, "?y", "?x"))


def cnt(world, query, c, d, s):
    """Thin wrapper: let the product's own exceptions propagate."""
    return count_canonical_proofs(
        world, query, max_fact_checks=c, max_derivations=d, max_proof_steps=s
    )


# shared fixture worlds (U0–U8 from the planning fixture table)
COPY = _copy_rule("p", "q")
ALPHA_COPY = Clause((_A("p", "?u", "?v"),), _A("q", "?u", "?v"))
INV = _inv_rule("p", "q")
SHARED = (_fact("p", "a", "a"), _fact("s", "a", "a"),
          Clause((_A("s", "?x", "?y"),), _A("p", "?x", "?y")))
NONSYMM = Clause((_A("p", "?z", "?x"), _A("p", "?x", "?y")), _A("q", "?x", "?x"))
SYMM = Clause((_A("p", "?x", "?y"), _A("p", "?x", "?y")), _A("q", "?x", "?y"))
JOIN = Clause((_A("p", "?x", "?y"), _A("q", "?y", "?z")), _A("r", "?x", "?z"))
JOIN_WORLD = (_fact("p", "a", "b"), _fact("p", "a", "d"),
              _fact("q", "b", "c"), _fact("q", "d", "c"), JOIN)
QUERY_U7 = _A("r", "a", "c")


def _atom_json(atom):
    return json.dumps([atom.pred, list(atom.args)], sort_keys=True)


def _world_json(world):
    items = [
        {"h": [cl.head.pred, list(cl.head.args)],
         "b": [[a.pred, list(a.args)] for a in cl.body]}
        for cl in world
    ]
    return json.dumps(items, sort_keys=True)


def _world_hash(world, query):
    payload = _world_json(world) + "\0" + _atom_json(query)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Group A: hand-counted anchors U0–U8
# ---------------------------------------------------------------------------

class TestAHandCounted:
    def test_u0_empty_world(self):
        got = cnt((), _A("p", "a", "b"), 1, 1, 1)
        assert type(got) is int
        assert got == 0

    def test_u1_single_fact(self):
        world = (_fact("p", "a", "b"),)
        got = cnt(world, _A("p", "a", "b"), 1, 1, 1)
        assert type(got) is int
        assert got == 1

    def test_u2_duplicate_facts_one_canonical(self):
        world = (_fact("p", "a", "b"), _fact("p", "a", "b"))
        got = cnt(world, _A("p", "a", "b"), 1, 2, 2)
        assert type(got) is int
        assert got == 1
        # cross-check raw count against the real T0009 only (not the key):
        assert len(enumerate_proofs(world, _A("p", "a", "b"),
                                    max_fact_checks=1, max_derivations=2,
                                    max_proof_steps=2)) == 2

    def test_u3_four_trees_one_canonical(self):
        world = (_fact("p", "a", "b"), _fact("p", "a", "b"), COPY, ALPHA_COPY)
        got = cnt(world, _A("q", "a", "b"), 2, 4, 10)
        assert type(got) is int
        assert got == 1  # duplicate source + alpha-equivalent copy merge

    def test_u4_copy_and_inverse_two_canonical(self):
        world = (_fact("p", "a", "a"), COPY, INV)
        # copy gives q(a,a); inverse also reaches q(a,a) but through a
        # different clause, so the two supports are non-equivalent.
        got = cnt(world, _A("q", "a", "a"), 2, 3, 5)
        assert type(got) is int
        assert got == 2

    def test_u5_non_symmetric_two_premise_four_canonical(self):
        world = (*SHARED, NONSYMM)
        # q(a,a): p-proofs {fact, s-derived}; the two slots are asymmetric
        # (z,x) vs (x,y), so (fact, s) != (s, fact): 4 distinct proofs.
        got = cnt(world, _A("q", "a", "a"), 3, 4, 20)
        assert type(got) is int
        assert got == 4

    def test_u6_symmetric_two_premise_three_canonical(self):
        world = (*SHARED, SYMM)
        # same world, symmetric slots: (fact, s) and (s, fact) merge.
        got = cnt(world, _A("q", "a", "a"), 3, 4, 20)
        assert type(got) is int
        assert got == 3

    def test_u7_join_two_supports(self):
        # two support paths through the join:
        # (p(a,b), q(b,c)) and (p(a,d), q(d,c)) -> r(a,c).
        got = cnt(JOIN_WORLD, QUERY_U7, 6, 6, 10)
        assert type(got) is int
        assert got == 2

    def test_u7_structural_variants_each_count_two(self):
        """Local variable bijection, clause order flip, JOIN body slot flip.

        The variable-bijection variant renames the JOIN's own variables
        (?x/?y/?z -> ?u/?v/?w) and keeps facts + query unchanged; it is a
        different world (different hash) that must still count exactly 2.
        """
        orig_hash = _world_hash(JOIN_WORLD, QUERY_U7)
        # the variable-bijection variant reuses the four fact objects
        # verbatim (facts and query are unchanged); only the JOIN clause
        # is renamed.
        facts = JOIN_WORLD[:-1]
        renamed_join = Clause((_A("p", "?u", "?v"), _A("q", "?v", "?w")),
                              _A("r", "?u", "?w"))
        assert renamed_join != JOIN, "renamed JOIN clause must differ from original"
        variants = (
            # true local variable bijection on the JOIN only: ?x/?y/?z -> ?u/?v/?w
            ("local_variable_bijection", facts + (renamed_join,)),
            # clause order flip (reversal of the clause tuple)
            ("clause_order_flip",
             (JOIN, _fact("q", "d", "c"), _fact("q", "b", "c"),
              _fact("p", "a", "d"), _fact("p", "a", "b"))),
            # JOIN body slot flip, variables kept consistent:
            # (q(?y,?z), p(?x,?y)) -> r(?x,?z) binds identically to the
            # original (p(?x,?y), q(?y,?z)) -> r(?x,?z)
            ("join_body_slot_flip",
             (*JOIN_WORLD[:-1],
              Clause((_A("q", "?y", "?z"), _A("p", "?x", "?y")),
                    _A("r", "?x", "?z")))),
        )
        for name, world in variants:
            got = cnt(world, QUERY_U7, 6, 6, 10)
            assert type(got) is int
            assert got == 2, name
            assert _world_hash(world, QUERY_U7) != orig_hash, name
        # facts and query are unchanged by the local-variable bijection
        var_world = variants[0][1]
        for i in range(4):
            assert var_world[i] is facts[i], "facts must be unchanged"

    def test_u7_world_unchanged_under_u7_u0_u7(self):
        """Deep-copy the full (clauses, query) input pair before the first
        call; after U7 -> U0 -> U7 the inputs are unchanged and the first /
        last results agree.  All three results are the exact int type."""
        world = JOIN_WORLD
        query = QUERY_U7
        before_world, before_query = copy.deepcopy((world, query))
        before_hash = _world_hash(world, query)
        r1 = cnt(world, query, 6, 6, 10)
        r0 = cnt((), _A("p", "a", "b"), 1, 1, 1)
        r2 = cnt(world, query, 6, 6, 10)
        for r in (r1, r0, r2):
            assert type(r) is int
        assert r1 == 2 and r0 == 0 and r2 == r1
        assert world == before_world and query == before_query
        assert _world_hash(world, query) == before_hash

    def test_u8_missing_query_zero(self):
        """U8: non-empty acyclic world whose query no record can derive;
        enumeration completes and the exact int result is 0 (no limit error)."""
        world = (_fact("p", "a", "b"), _copy_rule("p", "q"))
        got = cnt(world, _A("missing", "a", "b"), 1, 2, 1)
        assert type(got) is int
        assert got == 0

# ---------------------------------------------------------------------------
# Group B: real exhaustion failures (exact one-step-below budgets)
# ---------------------------------------------------------------------------

class TestBRealFailures:
    def test_b1_each_one_below_budget_exhausts(self):
        world = (*SHARED, SYMM)
        query = _A("q", "a", "a")
        for c, d, s, expected_type, expected_msg in (
            (2, 4, 20, DerivationLimitError,
             "enumerate.max_fact_checks exhausted before enumeration completed"),
            (3, 3, 20, DerivationLimitError,
             "enumerate.max_derivations exhausted before enumeration completed"),
            (3, 4, 19, ProofEnumerationLimitError,
             "proofs.max_proof_steps exhausted before enumeration completed"),
        ):
            with pytest.raises(expected_type) as excinfo:
                cnt(world, query, c, d, s)
            assert str(excinfo.value) == expected_msg, excinfo.value
            # budget exhaustion is a limit error, not 0 and not a partial count

    def test_b2_irrelevant_cycle_rejections(self):
        # self-loop r(x,y) -> r(x,y) with one unrelated fact; cycle is a
        # world failure that must precede any fact/absent-query result.
        world = (_fact("p", "a", "b"),
                 Clause((_A("r", "?x", "?y"),), _A("r", "?x", "?y")))
        for query in (_A("p", "a", "b"), _A("missing", "a", "b")):
            with pytest.raises(LogicValidationError) as excinfo:
                cnt(world, query, 1, 2, 1)
            assert str(excinfo.value) == (
                "dependency.clauses: cyclic predicate dependency"), excinfo.value

    def test_b3_input_contract_propagates_t0009_messages(self):
        fact = _fact("p", "a", "b")
        query = _A("p", "a", "b")
        # (input, call, expected message)
        cases = (
            ("list",
             lambda: cnt([fact], query, 1, 2, 1),
             "proofs.clauses must be a tuple of Clause; got list"),
            ("non-ground query",
             lambda: cnt((fact,), _A("q", "?x", "b"), 1, 2, 1),
             "proofs.query must be a ground Atom"),
            ("bool proof-steps budget",
             lambda: cnt((fact,), query, 1, 2, True),
             "proofs.max_proof_steps must be a non-bool positive integer; got bool"),
        )
        for label, call, msg in cases:
            with pytest.raises(LogicValidationError) as excinfo:
                call()
            assert str(excinfo.value) == msg, (label, excinfo.value)
        # generator: a marker in the body proves the layer did not
        # pre-scan; the same "got list"-style message uses "got generator".
        consumed = []

        def gen():
            while True:
                consumed.append("iterated")
                yield fact

        with pytest.raises(LogicValidationError) as excinfo:
            cnt(gen(), query, 1, 2, 1)
        assert str(excinfo.value) == (
            "proofs.clauses must be a tuple of Clause; got generator"), excinfo.value
        assert consumed == [], "layer pre-scanned the generator input"


# ---------------------------------------------------------------------------
# Group C: combination call contract (spies on what proof_count references)
# ---------------------------------------------------------------------------

@contextmanager
def _patch(pc_module, fake_enum, fake_key):
    orig_enum, orig_key = pc_module.enumerate_proofs, pc_module.canonical_proof_key
    pc_module.enumerate_proofs = fake_enum
    pc_module.canonical_proof_key = fake_key
    try:
        yield
    finally:
        pc_module.enumerate_proofs, pc_module.canonical_proof_key = (
            orig_enum, orig_key
        )


class TestCCallContract:
    def test_c1_single_enum_then_per_proof_key_original_objects_and_budgets(self):
        clauses = (_fact("p", "a", "b"),)
        query = _A("p", "a", "b")
        p0 = (ProofStep(0, (), _A("p", "a", "b")),)
        p1 = (ProofStep(0, (), _A("p", "a", "b")),)  # same content, distinct object
        A, B = ("k", "a"), ("k", "b")
        def make_spies():
            calls = []

            def fake_enum(clauses_, query_, *, max_fact_checks=None,
                          max_derivations=None, max_proof_steps=None):
                calls.append(("enum", clauses_, query_,
                              max_fact_checks, max_derivations, max_proof_steps))
                return (p0, p1, p0)

            def fake_key(clauses_, query_, proof, *, max_steps=None):
                calls.append(("key", clauses_, query_, proof, max_steps))
                return A if proof is p0 else B

            return fake_enum, fake_key, calls

        def run(*args, **kwargs):
            fake_enum, fake_key, calls = make_spies()
            with _patch(pc, fake_enum, fake_key):
                res = pc.count_canonical_proofs(*args, **kwargs)
            return res, calls

        res, calls = run(
            clauses, query,
            max_fact_checks=11, max_derivations=13, max_proof_steps=20001)
        assert res == 2
        assert len(calls) == 4
        (kind, cl, q, mfc, md, mps) = calls[0]
        assert kind == "enum"
        assert cl is clauses and q is query
        assert (mfc, md, mps) == (11, 13, 20001)
        for i, (kind, cl, q, proof, ms) in enumerate(calls[1:], start=1):
            assert kind == "key"
            assert cl is clauses and q is query          # originals passed through
            assert proof is (p0, p1, p0)[i - 1]         # original order, no rebuild
            assert ms == 20001                          # S passed to T0012, no default

        res_default, calls = run(clauses, query)
        assert res_default == 2
        assert len(calls) == 4
        (kind, cl, q, mfc, md, mps) = calls[0]
        assert kind == "enum"
        assert cl is clauses and q is query
        assert (mfc, md, mps) == (100_000, 100_000, 100_000)  # defaults recorded
        for i, (kind, cl, q, proof, ms) in enumerate(calls[1:], start=1):
            assert kind == "key"
            assert cl is clauses and q is query
            assert proof is (p0, p1, p0)[i - 1]
            assert ms == 100_000  # defaults passed to T0012, no 10k default

    def test_c2_empty_enumeration_is_zero_without_any_key_call(self):
        clauses = (_fact("p", "a", "b"),)
        query = _A("p", "a", "b")
        calls = []

        def fake_enum(clauses_, query_, *, max_fact_checks=None,
                      max_derivations=None, max_proof_steps=None):
            calls.append((clauses_, query_,
                          max_fact_checks, max_derivations, max_proof_steps))
            return ()

        def fake_key(clauses_, query_, proof, *, max_steps=None):
            calls.append(("key", clauses_, query_, proof, max_steps))
            return ("k", "none")

        with _patch(pc, fake_enum, fake_key):
            res = pc.count_canonical_proofs(
                clauses, query,
                max_fact_checks=11, max_derivations=13, max_proof_steps=20001)
        assert type(res) is int
        assert res == 0
        assert calls[0] == (clauses, query, 11, 13, 20001)
        assert calls[0][1] is query
        assert [c for c in calls if c[0] == "key"] == [], ("key was called on empty", calls)
        # the S=20001 was a spy check only: no 10k-step chain was ever generated

    def test_c3_all_and_plain_python_typeerrors(self):
        assert pc.__all__ == ["count_canonical_proofs"]
        clauses = (_fact("p", "a", "b"),)
        query = _A("p", "a", "b")
        for bad in (
            lambda: pc.count_canonical_proofs(clauses),            # missing query
            lambda: pc.count_canonical_proofs(clauses, query, 5),  # extra positional
            lambda: pc.count_canonical_proofs(clauses, query,
                                               max_steps=1),       # unknown keyword
        ):
            with pytest.raises(TypeError):
                bad()


# ---------------------------------------------------------------------------
# Group D: original exception instances propagate (layer does not mask them)
# ---------------------------------------------------------------------------

class TestDOriginalExceptions:
    def test_d1_enum_sentinels_propagate_as_original_instances(self):
        clauses = (_fact("p", "a", "b"),)
        query = _A("p", "a", "b")
        for sentinel in (
            LogicValidationError("sentinel-logic"),
            DerivationLimitError("sentinel-fact"),
            ProofEnumerationLimitError(),
        ):
            calls = 0
            consumed = []

            def gen():
                while True:
                    consumed.append("iterated")
                    yield clauses

            def fake_enum(clauses_, query_, *, max_fact_checks=None,
                          max_derivations=None, max_proof_steps=None):
                nonlocal calls
                calls += 1
                raise sentinel

            def fake_key(clauses_, query_, proof, *, max_steps=None):
                raise AssertionError("key must not run when enumeration fails")

            with _patch(pc, fake_enum, fake_key):
                with pytest.raises(type(sentinel)) as excinfo:
                    pc.count_canonical_proofs(
                        gen(), query,
                        max_fact_checks=2, max_derivations=2, max_proof_steps=2)
            assert excinfo.value is sentinel, "sentinel was reconstructed"
            assert calls == 1
            # generator input is not pre-scanned by the layer:
            assert consumed == [], "layer pre-scanned the generator input"

    def test_d2_key_spot_sentinels_propagate_and_reach_later_calls(self):
        clauses = (_fact("p", "a", "b"),)
        query = _A("p", "a", "b")
        valid = (ProofStep(0, (), query),)  # a real 1-step valid proof
        sentinels = (
            LogicValidationError("sentinel-key-late"),
            ProofLimitError("sentinel-proof-limit"),
        )
        for sentinel in sentinels:
            calls = []

            def fake_enum(clauses_, query_, *, max_fact_checks=None,
                          max_derivations=None, max_proof_steps=None):
                # three raw proofs, the first two already merge-equivalent on purpose
                return (valid, valid, valid)

            def fake_key(clauses_, query_, proof, *, max_steps=None):
                calls.append(len(calls) + 1)
                if len(calls) == 3:
                    raise sentinel
                return ("k", len(calls))  # distinct keys: a skip would not be detected

            with _patch(pc, fake_enum, fake_key):
                with pytest.raises(type(sentinel)) as excinfo:
                    pc.count_canonical_proofs(clauses, query,
                                              max_fact_checks=1,
                                              max_derivations=1,
                                              max_proof_steps=3)
            assert excinfo.value is sentinel, "sentinel was reconstructed"
            assert calls == [1, 2, 3], (
                "layer skipped / stopped early before the failing call")

    def test_d3_bad_third_proof_propagates_real_t0012_error(self):
        clauses = (_fact("p", "a", "b"),)
        query = _A("p", "a", "b")
        valid = (ProofStep(0, (), query),)
        bad = (ProofStep(0, (), _A("q", "x", "y")),)  # conclusion does not match query
        calls = []

        def fake_enum(clauses_, query_, *, max_fact_checks=None,
                      max_derivations=None, max_proof_steps=None):
            return (valid, valid, bad)

        real_key = pc.canonical_proof_key

        def spy_key(clauses_, query_, proof, *, max_steps=None):
            calls.append(proof)
            return real_key(clauses_, query_, proof, max_steps=max_steps)

        with _patch(pc, fake_enum, spy_key):
            with pytest.raises(LogicValidationError) as excinfo:
                pc.count_canonical_proofs(clauses, query,
                                          max_fact_checks=1,
                                          max_derivations=1,
                                          max_proof_steps=3)
        assert str(excinfo.value) == (
            "proof_key.proof must be a valid proof of query"), excinfo.value
        assert calls == [valid, valid, bad], "real T0012 not reached / skipped"
        # the first two proofs were the same valid proof; an early return of 1
        # would have happened only if the third proof were not processed


# ---------------------------------------------------------------------------
# Group E: execution isolation (fresh subprocess)
# ---------------------------------------------------------------------------

class TestEIsolation:
    def test_e1_fresh_subprocess_blocks_engine_and_reference_engine(self):
        repo = Path(__file__).resolve().parents[1]
        src_root = repo / "src"
        expected_pc_file = str(src_root / "kmesh" / "logic" / "proof_count.py")
        code = textwrap.dedent("""
        import importlib, sys, types

        BLOCK_MSG = "t0013-import-isolation: import blocked"
        BLOCKED = ("torch", "yaml", "kmesh.logic.engine",
                   "kmesh.logic.reference_engine")

        class _BlockFinder:
            def find_spec(self, name, path=None, target=None):
                # exact root and any descendant (submodule) are both blocked;
                # the reported name is the full dotted name actually attempted.
                # A copy that only matched the exact root would not block
                # submodules and the submodule probe below would fail (it would
                # raise ModuleNotFoundError, not the custom ImportError).
                for root in BLOCKED:
                    if name == root or name.startswith(root + "."):
                        raise ImportError(BLOCK_MSG + " " + repr(name))
                return None

        sys.meta_path.insert(0, _BlockFinder())

        def _probe_root(root):
            # target must not be preloaded: the blocker (meta-path, full-name
            # match) is what must catch the import, not a pre-seeded sys.modules
            # entry.
            assert root not in sys.modules, f"root {root!r} unexpectedly preloaded"
            # step 1 -- actually import the root; the block message must carry the
            # full attempted root name (distinguishes a root-level block from a
            # submodule-level block).
            try:
                importlib.import_module(root)
                raise SystemExit(f"root {root!r} imported; isolation failed")
            except ImportError as exc:
                assert str(exc) == BLOCK_MSG + " " + repr(root), (root, exc)
            # step 2 -- 占位包、空 __path__ (placeholder package, empty __path__):
            # the next import is a *submodule* import; the meta-path finder
            # must be consulted with the full dotted submodule name and block
            # with that exact name. This exercises the startswith(root + ".")
            # branch (a root-only-match copy would fail this step).
            sys.modules[root] = types.ModuleType(root)
            sys.modules[root].__path__ = []
            probe = root + "._t0013_probe"
            try:
                importlib.import_module(probe)
                raise SystemExit(f"submodule {probe!r} imported; isolation failed")
            except ImportError as exc:
                assert str(exc) == BLOCK_MSG + " " + repr(probe), (root, exc)
            finally:
                # clean up the placeholder root; the parent package (e.g.
                # kmesh.logic) is never touched and stays intact.
                sys.modules.pop(root, None)

        for root in ("torch", "yaml", "kmesh.logic.engine",
                     "kmesh.logic.reference_engine"):
            _probe_root(root)

        # Keep the blocker (finder) active through the real import, the U2/U6
        # computations and the final scan: the product must run under the same
        # hard isolation and use the current src.
        sys.path.insert(0, str(__SRC__))
        from kmesh.logic import proof_count as pc
        from kmesh.logic.types import Atom, Clause

        def fact(pred, a, b):
            return Clause((), Atom(pred, (a, b)))

        u2 = (fact("p", "a", "b"), fact("p", "a", "b"))
        u6 = (fact("p", "a", "a"), fact("s", "a", "a"),
              Clause((Atom("s", ("?x", "?y")),), Atom("p", ("?x", "?y"))),
              Clause((Atom("p", ("?x", "?y")), Atom("p", ("?x", "?y"))),
                     Atom("q", ("?x", "?y"))))

        assert pc.__file__ == __EXPECTED__, pc.__file__

        assert pc.count_canonical_proofs(u2, Atom("p", ("a", "b")),
                                        max_fact_checks=1,
                                        max_derivations=2,
                                        max_proof_steps=2) == 1
        assert pc.count_canonical_proofs(u6, Atom("q", ("a", "a")),
                                        max_fact_checks=3,
                                        max_derivations=4,
                                        max_proof_steps=20) == 3

        # No blocked module (root or descendant) may remain in sys.modules.
        leaked = [n for n in list(sys.modules)
                  if any(n == b or n.startswith(b + ".") for b in BLOCKED)]
        assert not leaked, f"blocked modules in sys.modules: {leaked}"
        print("ISOLATION-OK")
        """).replace("__SRC__", json.dumps(str(src_root))) \
            .replace("__EXPECTED__", json.dumps(expected_pc_file))

        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr
        assert "ISOLATION-OK" in proc.stdout
