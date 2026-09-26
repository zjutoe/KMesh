"""T0015 tests for ``extract_proof_subtree`` (D33).

A complete rooted subtree: choose a step of a legal single-occurrence proof
and return that conclusion plus all steps it depends on, renumbered into a
contiguous, verifier-checkable sub-proof.  The tests are hand-written (never
built from the target function), use the independent T0006 verifier and the
T0012 single-occurrence check, and cover main example, occurrences,
delegation/root boundaries, reorder/purity/scale, and hard import isolation.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from kmesh.logic.proof import ProofStep, ProofLimitError, verify_proof
from kmesh.logic.proof_key import canonical_proof_key
from kmesh.logic.proof_subtree import extract_proof_subtree
from kmesh.logic.types import Atom, Clause, LogicValidationError


def a(pred, x, y):
    return Atom(pred, (x, y))


def fact(pred, x, y):
    return Clause((), a(pred, x, y))


def rule(head, hx, hy, *body):
    return Clause(
        tuple(a(b[0], b[1], b[2]) for b in body), a(head, hx, hy)
    )


def step(ci, refs, pred, x, y):
    return ProofStep(ci, tuple(refs), a(pred, x, y))


def world_main():
    return (
        rule("w", "?x", "?z", ("u", "?x", "?y"), ("v", "?y", "?z")),
        fact("q", "b", "c"),
        rule("u", "?x", "?y", ("p", "?x", "?y"),),
        fact("p", "a", "b"),
        rule("v", "?x", "?y", ("q", "?x", "?y"),),
    )


QUERY = a("w", "a", "c")


def proof_main():
    return (
        step(3, (), "p", "a", "b"),
        step(1, (), "q", "b", "c"),
        step(2, (0,), "u", "a", "b"),
        step(4, (1,), "v", "b", "c"),
        step(0, (2, 3), "w", "a", "c"),
    )


W = world_main()
Q = QUERY
P = proof_main()


def _sub(steps):
    return tuple(
        ProofStep(ci, tuple(refs), a(pred, x, y))
        for ci, refs, pred, x, y in steps
    )


def _check_sub(w, p, root):
    sub = extract_proof_subtree(w, Q, p, root)
    root_concl = p[root].conclusion
    assert verify_proof(w, root_concl, sub) is True, (root, sub)
    return sub


# --------------------------------------------------------------------------
# A. main example outputs + occurrence semantics
# --------------------------------------------------------------------------

def test_main_example_anchors_and_occurrence():
    assert verify_proof(W, Q, P) is True
    # root=0 / root=1 : single original facts
    s0 = _check_sub(W, P, 0)
    assert s0 == _sub([(3, (), "p", "a", "b")])
    assert verify_proof(W, a("p", "a", "b"), s0) is True
    s1 = _check_sub(W, P, 1)
    assert s1 == _sub([(1, (), "q", "b", "c")])
    assert verify_proof(W, a("q", "b", "c"), s1) is True
    # root=2 : steps 0,2 ; ci=(3,2); refs=((),(0,))
    s2 = _check_sub(W, P, 2)
    assert s2 == _sub([
        (3, (), "p", "a", "b"),
        (2, (0,), "u", "a", "b"),
    ])
    # root=3 : steps 1,3 ; ci=(1,4); old ref=1 -> new ref=0
    s3 = _check_sub(W, P, 3)
    assert s3 == _sub([
        (1, (), "q", "b", "c"),
        (4, (0,), "v", "b", "c"),
    ])
    # root=4 (last) : whole interleaved proof, original order
    s4 = _check_sub(W, P, 4)
    assert s4 == P


def test_internal_join_not_last_root():
    # add a COPY w->z rule and a step using it, so the old join is internal
    w2 = W + (
        rule("z", "?x", "?y", ("w", "?x", "?y"),),
    )
    q2 = a("z", "a", "c")
    # P has 5 steps (0..4); add a 6th using clause index 5 (the new z rule),
    # whose only premise is the internal w-join at step 4.
    p2 = P + (ProofStep(5, (4,), a("z", "a", "c")),)
    assert verify_proof(w2, q2, p2) is True
    sub = extract_proof_subtree(w2, q2, p2, root_step=4)
    # root=4 (the internal w-join, now non-final) still returns the full
    # interleaved 0..4 proof (no last-root special case).
    assert sub == P
    assert verify_proof(w2, P[4].conclusion, sub) is True


def test_repeated_occurrence_not_deduped():
    # world: p(a,b) fact and rule p(x,y),p(x,y) -> q(x,y)
    w = (fact("p", "a", "b"),
         rule("q", "?x", "?y", ("p", "?x", "?y"), ("p", "?x", "?y")))
    q = a("q", "a", "b")
    s = ProofStep(0, (), a("p", "a", "b"))
    proof = (s, s, ProofStep(1, (0, 1), a("q", "a", "b")))
    assert verify_proof(w, q, proof) is True
    # root=2 keeps all three occurrences, refs=(0,1)
    sub = extract_proof_subtree(w, q, proof, root_step=2)
    assert len(sub) == 3
    assert sub[0] == proof[0] and sub[1] == proof[1]
    assert sub[2].premise_steps == (0, 1)
    assert verify_proof(w, q, sub) is True
    # root=0 and root=1 each single
    assert extract_proof_subtree(w, q, proof, root_step=0) == (s,)
    assert extract_proof_subtree(w, q, proof, root_step=1) == (s,)


def test_bounded_cycle():
    # p fact, p->q, q->p ; valid 3-step proof, middle root=1 -> first two
    w = (fact("p", "a", "b"),
         rule("q", "?x", "?y", ("p", "?x", "?y"),),
         rule("p", "?x", "?y", ("q", "?x", "?y"),))
    # last step concludes p(a,b), so the query is p(a,b) (cyclic chain)
    q = a("p", "a", "b")
    p = (
        ProofStep(0, (), a("p", "a", "b")),
        ProofStep(1, (0,), a("q", "a", "b")),
        ProofStep(2, (1,), a("p", "a", "b")),
    )
    assert verify_proof(w, q, p) is True
    sub = extract_proof_subtree(w, q, p, root_step=1)
    assert len(sub) == 2
    assert sub == (ProofStep(0, (), a("p", "a", "b")),
                   ProofStep(1, (0,), a("q", "a", "b")))
    assert verify_proof(w, a("q", "a", "b"), sub) is True


def test_accepted_proofstep_subclass():
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class AnnotatedStep(ProofStep):
        note: str

    # same main example, but every step is a subclass with a required `note`;
    # the new layer must rebuild plain ProofStep (no subclass re-instantiation).
    ann = (
        AnnotatedStep(3, (), a("p", "a", "b"), "fact p"),
        AnnotatedStep(1, (), a("q", "b", "c"), "fact q"),
        AnnotatedStep(2, (0,), a("u", "a", "b"), "u"),
        AnnotatedStep(4, (1,), a("v", "b", "c"), "v"),
        AnnotatedStep(0, (2, 3), a("w", "a", "c"), "w"),
    )
    assert verify_proof(W, Q, ann) is True
    assert canonical_proof_key(W, Q, ann) == canonical_proof_key(W, Q, P)
    sub = extract_proof_subtree(W, Q, ann, root_step=3)
    assert sub == (ProofStep(1, (), a("q", "b", "c")),
                   ProofStep(4, (0,), a("v", "b", "c")))
    assert verify_proof(W, sub[1].conclusion, sub) is True


# --------------------------------------------------------------------------
# B. full input + delegation boundaries
# --------------------------------------------------------------------------

def test_full_input_budget_precedes_root():
    # main proof has 5 steps: max_steps=5 ok, 4 fails even for leaf root=0
    assert extract_proof_subtree(W, Q, P, root_step=0, max_steps=5)
    with pytest.raises(ProofLimitError):
        extract_proof_subtree(W, Q, P, root_step=0, max_steps=4)
    # empty proof + legal world -> T0012 rejection message, propagated
    with pytest.raises(LogicValidationError) as exc:
        extract_proof_subtree(W, Q, (), root_step=0)
    assert str(exc.value) == "proof_key.proof must be a valid proof of query"


def test_single_occurrence_rejection_propagates():
    # two steps, fact 0 referenced twice -> not a single occurrence tree
    s = ProofStep(0, (), a("p", "a", "b"))
    # rule needs identical body atoms so using fact 0 twice is a legal derivation
    w = (fact("p", "a", "b"),
         rule("q", "?x", "?y", ("p", "?x", "?y"), ("p", "?x", "?y")))
    q = a("q", "a", "b")
    bad = (s, ProofStep(1, (0, 0), a("q", "a", "b")))
    assert verify_proof(w, q, bad) is True
    with pytest.raises(LogicValidationError) as exc:
        extract_proof_subtree(w, q, bad, root_step=0)
    assert str(exc.value) == "proof_key.proof must be a single occurrence tree"
    # independent fixture: an unused step (root=1) rejected for its own reason
    bad2 = (s, s, s, ProofStep(1, (1, 2), a("q", "a", "b")))
    assert verify_proof(w, q, bad2) is True
    with pytest.raises(LogicValidationError) as exc:
        extract_proof_subtree(w, q, bad2, root_step=1)
    assert str(exc.value) == "proof_key.proof must be a single occurrence tree"


def test_delegation_single_call_original_objects():
    import kmesh.logic.proof_subtree as m
    calls = []
    orig = m.canonical_proof_key

    def spy(*a, **kw):
        calls.append((a, kw))
        return orig(*a, **kw)

    # default budget -> spy sees max_steps=10_000, exactly one call
    m.canonical_proof_key = spy
    try:
        extract_proof_subtree(W, Q, P, 0)
    finally:
        m.canonical_proof_key = orig
    assert len(calls) == 1
    (a, kw), = calls
    assert a[0] is W and a[1] is Q and a[2] is P
    assert kw == {"max_steps": 10_000}

    # non-default budget -> spy sees max_steps=5, original objects, one call
    calls.clear()
    m.canonical_proof_key = spy
    try:
        extract_proof_subtree(W, Q, P, 0, max_steps=5)
    finally:
        m.canonical_proof_key = orig
    assert len(calls) == 1
    (a, kw), = calls
    assert a[0] is W and a[1] is Q and a[2] is P
    assert kw == {"max_steps": 5}


def test_sentinel_priority():
    import kmesh.logic.proof_subtree as m
    calls = []
    orig = m.canonical_proof_key
    # LogicValidationError sentinel + root=-1 : LVE first, then root check
    sentinel1 = LogicValidationError("t0015-lve-sentinel")
    def raiser1(*a, **kw):
        calls.append((a, kw)); raise sentinel1
    calls.clear()
    m.canonical_proof_key = raiser1
    try:
        with pytest.raises(LogicValidationError) as exc:
            extract_proof_subtree(W, Q, P, -1, max_steps=10_000)
        assert exc.value is sentinel1
        assert type(exc.value) is LogicValidationError
        assert str(exc.value) == "t0015-lve-sentinel"
        assert len(calls) == 1
    finally:
        m.canonical_proof_key = orig
    # ProofLimitError sentinel + root=-1 : delegate first, then root check
    sentinel2 = ProofLimitError("t0015-limit-sentinel")
    calls.clear()
    def raiser2(*a, **kw):
        calls.append((a, kw)); raise sentinel2
    m.canonical_proof_key = raiser2
    try:
        with pytest.raises(ProofLimitError) as exc:
            extract_proof_subtree(W, Q, P, -1, max_steps=10_000)
        assert exc.value is sentinel2
        assert type(exc.value) is ProofLimitError
        assert str(exc.value) == "t0015-limit-sentinel"
        assert len(calls) == 1
    finally:
        m.canonical_proof_key = orig


def test_input_generation_and_list_rejected():
    # proof as a REAL generator: T0012 rejects it on the
    # isinstance(proof, tuple) check, *before* any iteration/consumption.
    consumed = []
    def gen_proof():
        for s in (ProofStep(3, (), a("p", "a", "b")),
                  ProofStep(1, (), a("q", "b", "c"))):
            consumed.append(s)
            yield s
    gp = gen_proof()
    with pytest.raises(LogicValidationError) as exc:
        extract_proof_subtree(W, Q, gp, 0)
    assert type(exc.value) is LogicValidationError
    assert str(exc.value) == "verify.proof must be a tuple of ProofStep, got generator"
    assert consumed == [], "T0012 consumed the generator before rejecting"
    # a list of clauses is rejected too (new layer does not tuple-ize it)
    with pytest.raises(LogicValidationError) as exc2:
        extract_proof_subtree(list(W), Q, P, 0)
    assert type(exc2.value) is LogicValidationError
    assert str(exc2.value) == "verify.clauses must be a tuple of Clause, got list"


# --------------------------------------------------------------------------
# C. root boundaries
# --------------------------------------------------------------------------

def test_root_type_boundaries():
    for bad, tname in ((None, "NoneType"), (True, "bool"), (False, "bool"),
                        (-1, "int"), (1.5, "float"), ("0", "str")):
        with pytest.raises(LogicValidationError) as exc:
            extract_proof_subtree(W, Q, P, bad)
        assert type(exc.value) is LogicValidationError
        assert str(exc.value) == (
            "proof_subtree.root_step must be a non-bool non-negative integer, "
            "got " + tname)
    # out of range (non-echoed)
    with pytest.raises(LogicValidationError) as exc:
        extract_proof_subtree(W, Q, P, len(P))
    assert type(exc.value) is LogicValidationError
    assert str(exc.value) == "proof_subtree.root_step must be less than the proof length"
    # normal bounds work
    assert extract_proof_subtree(W, Q, P, 0)
    assert extract_proof_subtree(W, Q, P, 4)


def test_root_giant_integer_not_echoed():
    import sys
    from sys import get_int_max_str_digits, set_int_max_str_digits
    old = get_int_max_str_digits()
    try:
        set_int_max_str_digits(4300)
        assert get_int_max_str_digits() == 4300
        with pytest.raises(LogicValidationError) as exc:
            extract_proof_subtree(W, Q, P, -10**5000)
        assert type(exc.value) is LogicValidationError
        assert str(exc.value) == (
            "proof_subtree.root_step must be a non-bool non-negative integer, "
            "got int")
        assert "999" not in str(exc.value)
        with pytest.raises(LogicValidationError) as exc:
            extract_proof_subtree(W, Q, P, 10**5000)
        assert type(exc.value) is LogicValidationError
        assert str(exc.value) == (
            "proof_subtree.root_step must be less than the proof length")
    finally:
        set_int_max_str_digits(old)


def test_signature_type_errors():
    with pytest.raises(TypeError):
        extract_proof_subtree(W, Q, P)  # missing root_step
    with pytest.raises(TypeError):
        extract_proof_subtree(W, Q, P, 0, 1)  # extra positional
    with pytest.raises(TypeError):
        extract_proof_subtree(W, Q, P, 0, bogus=1)  # unknown keyword
    import kmesh.logic.proof_subtree as m
    assert m.__all__ == ["extract_proof_subtree"]


# --------------------------------------------------------------------------
# D. reorder / purity / scale
# --------------------------------------------------------------------------

def test_reorder_premise_remap():
    # swap the two facts 0 and 1, remap dependent refs
    w = (
        rule("w", "?x", "?z", ("u", "?x", "?y"), ("v", "?y", "?z")),
        fact("q", "b", "c"),
        rule("u", "?x", "?y", ("p", "?x", "?y"),),
        fact("p", "a", "b"),
        rule("v", "?x", "?y", ("q", "?x", "?y"),),
    )
    p = (
        ProofStep(1, (), a("q", "b", "c")),   # swapped: fact q now at 0
        ProofStep(3, (), a("p", "a", "b")),   # swapped: fact p now at 1
        ProofStep(2, (1,), a("u", "a", "b")), # u now references p at 1
        ProofStep(4, (0,), a("v", "b", "c")), # v now references q at 0
        ProofStep(0, (2, 3), a("w", "a", "c")),
    )
    assert verify_proof(w, Q, p) is True
    sub = extract_proof_subtree(w, Q, p, root_step=2)
    assert sub == _sub([(3, (), "p", "a", "b"), (2, (0,), "u", "a", "b")])
    # independently reverse the ORIGINAL world storage + remap ci; refs unchanged
    wr = tuple(reversed(W))
    rp = tuple(ProofStep(len(W) - 1 - o.clause_index, tuple(o.premise_steps), o.conclusion)
               for o in P)
    assert wr != W
    for o, n in zip(P, rp):
        assert n.premise_steps == o.premise_steps
        assert n.conclusion == o.conclusion
        assert n.clause_index == len(W) - 1 - o.clause_index
    assert verify_proof(wr, Q, rp) is True
    sub_r = extract_proof_subtree(wr, Q, rp, root_step=3)
    assert sub_r == (ProofStep(3, (), a("q", "b", "c")),
                     ProofStep(0, (0,), a("v", "b", "c")))
    assert verify_proof(wr, sub_r[1].conclusion, sub_r) is True


def test_input_pure_and_output_shape():
    import copy
    # full structural snapshot + field snapshots + hash BEFORE the first call
    w0 = copy.deepcopy(W)
    p0 = tuple(copy.deepcopy(s) for s in P)
    q0 = Q
    h = hash((tuple(map(repr, W)), repr(Q), tuple(map(repr, P))))
    # three calls: root 3 -> 0 -> 3 ; input unchanged, first/last output equal
    s3 = extract_proof_subtree(W, Q, P, 3)
    s0 = extract_proof_subtree(W, Q, P, 0)
    s3b = extract_proof_subtree(W, Q, P, 3)
    # input field-by-field + hash unchanged after the three calls
    assert W == w0 and Q == q0
    for o, n in zip(p0, P):
        assert o.clause_index == n.clause_index
        assert o.premise_steps == n.premise_steps
        assert o.conclusion == n.conclusion
    assert hash((tuple(map(repr, W)), repr(Q), tuple(map(repr, P)))) == h
    # first/last output (root=3) equal; each sub-proof verifies
    assert s3 == s3b
    assert verify_proof(W, s3[-1].conclusion, s3) is True
    assert verify_proof(W, s0[-1].conclusion, s0) is True
    # shape checks on the root=3 sub-proof; refs bound by own position
    sub = s3
    assert isinstance(sub, tuple)
    for i, s in enumerate(sub):
        assert isinstance(s, ProofStep)
        assert isinstance(s.premise_steps, tuple)
        for ref in s.premise_steps:
            assert type(ref) is int and 0 <= ref < i


def test_1201_step_copy_chain():
    # hand-made 1201-step chain c0 -> c1 -> ... -> c1200 (distinct
    # predicates); root=600 yields the 601-step prefix, max_steps=600
    # must raise ProofLimitError (full input, not just the local prefix).
    n = 1201
    def pred(i):
        return "c%d" % i
    w = (fact(pred(0), "a", "b"),) + tuple(
        rule(pred(i), "?x", "?y", (pred(i - 1), "?x", "?y"),)
        for i in range(1, n)
    )
    p = (ProofStep(0, (), a(pred(0), "a", "b")),) + tuple(
        ProofStep(i, (i - 1,), a(pred(i), "a", "b")) for i in range(1, n)
    )
    q = a(pred(n - 1), "a", "b")
    assert verify_proof(w, q, p) is True
    sub = extract_proof_subtree(w, q, p, root_step=600, max_steps=1201)
    assert len(sub) == 601
    for i in range(601):
        assert sub[i].clause_index == i
        assert sub[i].conclusion == a(pred(i), "a", "b")
        assert sub[i].premise_steps == (() if i == 0 else (i - 1,))
    assert verify_proof(w, a(pred(600), "a", "b"), sub) is True
    with pytest.raises(ProofLimitError):
        extract_proof_subtree(w, q, p, root_step=600, max_steps=600)


# --------------------------------------------------------------------------
# E. hard import isolation
# --------------------------------------------------------------------------

_ISOLATION_SCRIPT = '''
import sys, importlib, types
sys.path.insert(0, @SRC_DIR@)
BLOCKED = [
    "torch", "yaml",
    "kmesh.logic.engine", "kmesh.logic.reference_engine",
    "kmesh.logic.proof_enumeration", "kmesh.logic.motif",
]
MSG = "T0015 blocked: "
class BlockFinder:
    def find_spec(self, fullname, path=None, target=None):
        for r in BLOCKED:
            if fullname == r or fullname.startswith(r + "."):
                raise ModuleNotFoundError(MSG + fullname)
        return None
mf = BlockFinder()
sys.meta_path.insert(0, mf)
try:
    import os
    from kmesh.logic.types import Atom, Clause
    from kmesh.logic.proof import ProofStep, verify_proof
    from kmesh.logic import proof_subtree
    src = os.path.realpath(sys.path[0])
    want = os.path.realpath(src + "/kmesh/logic/proof_subtree.py")
    assert os.path.realpath(proof_subtree.__file__) == want, \\
        "path: " + str(proof_subtree.__file__)
    for r in BLOCKED:
        try:
            importlib.import_module(r)
            print("UNBLOCKED-R:" + r); sys.exit(1)
        except ModuleNotFoundError as e:
            assert str(e) == MSG + r, "root wrong: " + repr(e)
            print("BLOCKED-R:" + r)
    for r in BLOCKED:
        mod = types.ModuleType(r); mod.__name__ = r
        mod.__path__ = []
        sys.modules[r] = mod
        try:
            importlib.import_module(r + ".t0015_probe")
            print("UNBLOCKED-S:" + r + ".t0015_probe"); sys.exit(1)
        except ModuleNotFoundError as e:
            assert str(e) == MSG + r + ".t0015_probe", "sub wrong: " + repr(e)
            print("BLOCKED-S:" + r + ".t0015_probe")
        finally:
            sys.modules.pop(r, None)
    def atom(pred, x, y):
        return Atom(pred, (x, y))
    def fact(pred, x, y):
        return Clause((), atom(pred, x, y))
    def rule(head, hx, hy, *body):
        return Clause(tuple(atom(b[0], b[1], b[2]) for b in body), atom(head, hx, hy))
    def step(ci, refs, pred, x, y):
        return ProofStep(ci, tuple(refs), atom(pred, x, y))
    wm = (
        rule("w", "?x", "?z", ("u", "?x", "?y"), ("v", "?y", "?z")),
        fact("q", "b", "c"),
        rule("u", "?x", "?y", ("p", "?x", "?y"),),
        fact("p", "a", "b"),
        rule("v", "?x", "?y", ("q", "?x", "?y"),),
    )
    qm = atom("w", "a", "c")
    pm = (
        step(3, (), "p", "a", "b"),
        step(1, (), "q", "b", "c"),
        step(2, (0,), "u", "a", "b"),
        step(4, (1,), "v", "b", "c"),
        step(0, (2, 3), "w", "a", "c"),
    )
    assert verify_proof(wm, qm, pm) is True
    sub = proof_subtree.extract_proof_subtree(wm, qm, pm, 3, max_steps=20)
    assert isinstance(sub, tuple) and len(sub) == 2, "len " + str(len(sub))
    assert sub[1].conclusion == atom("v", "b", "c")
    assert verify_proof(wm, sub[1].conclusion, sub) is True
    s = ProofStep(0, (), atom("p", "a", "b"))
    w2 = (fact("p", "a", "b"),
          rule("q", "?x", "?y", ("p", "?x", "?y"), ("p", "?x", "?y")))
    q2 = atom("q", "a", "b")
    p2 = (s, s, ProofStep(1, (0, 1), atom("q", "a", "b")))
    assert verify_proof(w2, q2, p2) is True
    sub2 = proof_subtree.extract_proof_subtree(w2, q2, p2, 2, max_steps=20)
    assert isinstance(sub2, tuple) and len(sub2) == 3, "len " + str(len(sub2))
    assert sub2[2].premise_steps == (0, 1)
    print("ISOLATION-OK")
    banned = set()
    for m in sys.modules:
        for r in BLOCKED:
            if m == r or m.startswith(r + "."):
                banned.add(m)
    if banned:
        print("BAD:" + ",".join(sorted(banned))); sys.exit(1)
finally:
    if mf in sys.meta_path:
        sys.meta_path.remove(mf)
'''

def test_hard_isolation():
    root = Path(__file__).resolve().parents[1]
    src_dir = str(root / "src")
    script = _ISOLATION_SCRIPT.replace("@SRC_DIR@", json.dumps(src_dir))
    env = dict(os.environ)
    env["PYTHONPATH"] = src_dir
    env["PYTHONHASHSEED"] = "0"
    env["CUDA_VISIBLE_DEVICES"] = ""
    r = subprocess.run([sys.executable, "-I", "-c", script],
                       capture_output=True, text=True, timeout=120, env=env)
    assert r.returncode == 0, "exit=%d\n%s\n%s" % (r.returncode, r.stdout, r.stderr)
    for tag in ("torch", "yaml", "kmesh.logic.engine",
                "kmesh.logic.reference_engine", "kmesh.logic.proof_enumeration",
                "kmesh.logic.motif"):
        assert "BLOCKED-R:" + tag in r.stdout, "missing " + tag
        assert "BLOCKED-S:" + tag + ".t0015_probe" in r.stdout, "missing sub " + tag
    assert "ISOLATION-OK" in r.stdout
    assert "BAD:" not in r.stdout
    assert "UNBLOCKED" not in r.stdout
