"""T0014 单棵证明 motif 键：完整行为、身份、预算、长链与硬隔离。

覆盖契约 §2–4 与任务 A–F：三个完整手算锚点、关系／实体独立命名空间、
真实变换与纯度、六类支持区分、委托／预算／错误、长链与硬隔离。

只导入允许白名单（标准库 + kmesh.logic.types / kmesh.logic.proof_key /
kmesh.logic.proof 验证），不导入求解、枚举、torch、YAML、文件、缓存或递归。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from kmesh.logic.types import Atom, Clause, LogicValidationError
from kmesh.logic.proof import ProofStep, ProofLimitError, verify_proof
import kmesh.logic.motif as motif
from kmesh.logic.proof_key import canonical_proof_key


# 契约 §4 完整手算锚点（不可由产品 / 其它 canonical 函数派生）。
FACT_KEY = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("c", 0), ("c", 1)), ()),
))
COPY_KEY = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)), ((1, ("v", 0), ("v", 1)),)),
    ((1, 0, 1), (1, ("c", 0), ("c", 1)), ()),
))
JOIN_KEY = ("proof_motif_v1", (
    ((0, 0, 1), (0, ("v", 0), ("v", 1)),
     ((1, ("v", 0), ("v", 2)), (2, ("v", 2), ("v", 1)))),
    ((1, 0, 2), (1, ("c", 0), ("c", 2)), ()),
    ((2, 2, 1), (2, ("c", 2), ("c", 1)), ()),
))


def tolist(x):
    if isinstance(x, tuple):
        return tuple(tolist(v) for v in x)
    return x


def atom(p, x, y):
    return Atom(p, (x, y))


def fact(p, x, y):
    return Clause((), atom(p, x, y))


def rule(h, hx, hy, *body):
    return Clause(tuple(atom(b[0], b[1], b[2]) for b in body), atom(h, hx, hy))


def step(ci, refs, p, x, y):
    return ProofStep(ci, tuple(refs), atom(p, x, y))


def _mk(w, q, p):
    return w, q, p


def fact_proof(p, a, b):
    w = (fact(p, a, b),)
    q = atom(p, a, b)
    p2 = (step(0, (), p, a, b),)
    return w, q, p2


def copy_proof(p, q, a, b):
    w = (fact(p, a, b), rule(q, "?x", "?y", (p, "?x", "?y")))
    qn = atom(q, a, b)
    p2 = (step(0, (), p, a, b), step(1, (0,), q, a, b))
    return w, qn, p2


def inv_proof(p, q, a, b):
    w = (fact(p, a, b), rule(q, "?y", "?x", (p, "?x", "?y")))
    qn = atom(q, a, b)
    p2 = (step(0, (), p, a, b), step(1, (0,), q, a, b))
    return w, qn, p2


def join_proof():
    w = (fact("p", "a", "b"), fact("q", "b", "c"),
         rule("r", "?x", "?z", ("p", "?x", "?y"), ("q", "?y", "?z")))
    q = atom("r", "a", "c")
    p2 = (step(0, (), "p", "a", "b"), step(1, (), "q", "b", "c"),
          step(2, (0, 1), "r", "a", "c"))
    return w, q, p2


def m3_copy():
    w = (fact("p", "a", "a"), rule("q", "?x", "?y", ("p", "?x", "?y")))
    q = atom("q", "a", "a")
    p2 = (step(0, (), "p", "a", "a"), step(1, (0,), "q", "a", "a"))
    return w, q, p2


def m3_inv():
    w = (fact("p", "a", "a"), rule("q", "?y", "?x", ("p", "?x", "?y")))
    q = atom("q", "a", "a")
    p2 = (step(0, (), "p", "a", "a"), step(1, (0,), "q", "a", "a"))
    return w, q, p2


def m3_extend():
    w = (fact("p", "a", "a"), rule("q", "?x", "?y", ("p", "?x", "?y")),
         rule("r", "?x", "?y", ("q", "?x", "?y")))
    q = atom("r", "a", "a")
    p2 = (step(0, (), "p", "a", "a"), step(1, (0,), "q", "a", "a"),
          step(2, (1,), "r", "a", "a"))
    return w, q, p2


def m3_extend_inv():
    w = (fact("p", "a", "a"), rule("q", "?y", "?x", ("p", "?x", "?y")),
         rule("r", "?x", "?y", ("q", "?x", "?y")))
    q = atom("r", "a", "a")
    p2 = (step(0, (), "p", "a", "a"), step(1, (0,), "q", "a", "a"),
          step(2, (1,), "r", "a", "a"))
    return w, q, p2


def m5_ab():
    w = (fact("p", "a", "a"), fact("s", "a", "a"),
         rule("p", "?x", "?y", ("s", "?x", "?y")),
         rule("q", "?x", "?x", ("p", "?z", "?x"), ("p", "?x", "?y")))
    q = atom("q", "a", "a")
    p2 = (step(0, (), "p", "a", "a"), step(1, (), "s", "a", "a"),
          step(2, (1,), "p", "a", "a"), step(3, (0, 2), "q", "a", "a"))
    return w, q, p2


def m5_ba():
    w = (fact("p", "a", "a"), fact("s", "a", "a"),
         rule("p", "?x", "?y", ("s", "?x", "?y")),
         rule("q", "?x", "?x", ("p", "?z", "?x"), ("p", "?x", "?y")))
    q = atom("q", "a", "a")
    p2 = (step(1, (), "s", "a", "a"), step(2, (0,), "p", "a", "a"),
          step(0, (), "p", "a", "a"), step(3, (1, 2), "q", "a", "a"))
    return w, q, p2


def m6_aa():
    w = (fact("f", "a", "b"), fact("g", "b", "c"), fact("f", "a", "d"),
         fact("g", "d", "c"),
         rule("p", "?x", "?z", ("f", "?x", "?y"), ("g", "?y", "?z")),
         rule("r", "?x", "?z", ("p", "?x", "?z"), ("p", "?x", "?z")))
    q = atom("r", "a", "c")
    p2 = (step(0, (), "f", "a", "b"), step(1, (), "g", "b", "c"),
          step(4, (0, 1), "p", "a", "c"), step(0, (), "f", "a", "b"),
          step(1, (), "g", "b", "c"), step(4, (3, 4), "p", "a", "c"),
          step(5, (2, 5), "r", "a", "c"))
    return w, q, p2


def m6_ab():
    w = (fact("f", "a", "b"), fact("g", "b", "c"), fact("f", "a", "d"),
         fact("g", "d", "c"),
         rule("p", "?x", "?z", ("f", "?x", "?y"), ("g", "?y", "?z")),
         rule("r", "?x", "?z", ("p", "?x", "?z"), ("p", "?x", "?z")))
    q = atom("r", "a", "c")
    p2 = (step(0, (), "f", "a", "b"), step(1, (), "g", "b", "c"),
          step(4, (0, 1), "p", "a", "c"), step(2, (), "f", "a", "d"),
          step(3, (), "g", "d", "c"), step(4, (3, 4), "p", "a", "c"),
          step(5, (2, 5), "r", "a", "c"))
    return w, q, p2


def m7_cyclic():
    w = (fact("p", "a", "b"), rule("q", "?x", "?y", ("p", "?x", "?y")),
         rule("p", "?x", "?y", ("q", "?x", "?y")))
    q = atom("p", "a", "b")
    p2 = (step(0, (), "p", "a", "b"), step(1, (0,), "q", "a", "b"),
          step(2, (1,), "p", "a", "b"))
    return w, q, p2


def m7_variant():
    w = (fact("p", "a", "b"), rule("q", "?x", "?y", ("p", "?x", "?y")),
         rule("r", "?x", "?y", ("q", "?x", "?y")))
    q = atom("r", "a", "b")
    p2 = (step(0, (), "p", "a", "b"), step(1, (0,), "q", "a", "b"),
          step(2, (1,), "r", "a", "b"))
    return w, q, p2


def m8_var():
    w = (fact("p", "a", "b"), rule("q", "?x", "?y", ("p", "?x", "?y")))
    q = atom("q", "a", "b")
    p2 = (step(0, (), "p", "a", "b"), step(1, (0,), "q", "a", "b"))
    return w, q, p2


def m8_const():
    w = (fact("p", "a", "b"), rule("q", "a", "?y", ("p", "a", "?y")))
    q = atom("q", "a", "b")
    p2 = (step(0, (), "p", "a", "b"), step(1, (0,), "q", "a", "b"))
    return w, q, p2


def m9():
    w = (fact("p", "a", "b"),
         rule("q", "?x", "?y", ("p", "?x", "?y"), ("p", "?x", "?y")))
    q = atom("q", "a", "b")
    p2 = (step(0, (), "p", "a", "b"), step(0, (), "p", "a", "b"),
          step(1, (0, 1), "q", "a", "b"))
    return w, q, p2


def long_chain():
    w = (fact("p0", "a", "b"),)
    for i in range(1, 1201):
        w = w + (rule("p%d" % i, "?x", "?y", ("p%d" % (i - 1), "?x", "?y")),)
    q = atom("p1200", "a", "b")
    p2 = [step(0, (), "p0", "a", "b")]
    for i in range(1, 1201):
        p2.append(step(i, (i - 1,), "p%d" % i, "a", "b"))
    return w, q, tuple(p2)


def _atom_plain(a):
    return (a.pred, a.args)

def _clause_plain(c):
    return (tuple(_atom_plain(x) for x in c.body), _atom_plain(c.head))

def _snapshot(w, q, p):
    cl = tuple(_clause_plain(c) for c in w)
    qn = _atom_plain(q)
    pn = tuple((_atom_plain(s.conclusion),) for s in p)
    raw = json.dumps([cl, qn, pn], ensure_ascii=False, sort_keys=True).encode("utf-8")
    return (cl, qn, pn, hashlib.sha256(raw).hexdigest())


def _key(w, q, p, **kw):
    return tolist(motif.canonical_motif_key(w, q, p, **kw))


# ---------- 组 A：完整手算锚点 ----------

def test_anchor_fact_literal():
    w, q, p = fact_proof("p", "a", "b")
    verify_proof(tuple(w), q, p)
    assert _key(w, q, p, max_steps=20, max_orientations=10) == FACT_KEY


def test_anchor_copy_literal():
    w, q, p = copy_proof("p", "q", "a", "b")
    verify_proof(tuple(w), q, p)
    assert _key(w, q, p, max_steps=20, max_orientations=10) == COPY_KEY


def test_anchor_join_literal():
    w, q, p = join_proof()
    verify_proof(tuple(w), q, p)
    assert _key(w, q, p, max_steps=20, max_orientations=10) == JOIN_KEY


def test_key_container_types():
    w, q, p = fact_proof("p", "a", "b")
    key = tolist(motif.canonical_motif_key(w, q, p))
    assert key[0] == "proof_motif_v1"
    assert isinstance(key[1], tuple)
    def _check_term(t):
        assert isinstance(t, tuple) and len(t) == 2
        assert t[0] in ("c", "v") and isinstance(t[1], int) and t[1] >= 0 and not isinstance(t[1], bool)
    def _check_atom(a):
        assert isinstance(a, tuple) and len(a) == 3
        assert isinstance(a[0], int) and a[0] >= 0
        _check_term(a[1])
        _check_term(a[2])
    for node in key[1]:
        assert isinstance(node, tuple) and len(node) == 3
        ground, head, body = node
        assert len(ground) == 3
        assert all(isinstance(x, int) and x >= 0 and not isinstance(x, bool) for x in ground)
        assert head[0] == ground[0]
        _check_atom(head)
        assert isinstance(body, tuple)
        for a in body:
            _check_atom(a)
    assert len({key}) == 1


def test_namespace_collide():
    w1, q1, p1 = fact_proof("p", "p", "a")
    w2, q2, p2 = fact_proof("q", "u", "v")
    assert _key(w1, q1, p1) == _key(w2, q2, p2)


# ---------- 组 B：真实变换与纯度 ----------

def _join_renamed():
    w = (fact("z", "V", "U"), fact("a", "U", "T"),
         rule("m", "?x", "?z", ("z", "?x", "?y"), ("a", "?y", "?z")))
    q = atom("m", "V", "T")
    p2 = (step(0, (), "z", "V", "U"), step(1, (), "a", "U", "T"),
          step(2, (0, 1), "m", "V", "T"))
    return w, q, p2


def test_join_rename_invariant():
    base = join_proof()
    k0 = _key(base[0], base[1], base[2])
    rn = _join_renamed()
    assert _key(rn[0], rn[1], rn[2]) == k0
    assert tuple(base[0]) != tuple(rn[0]) and base[1] != rn[1] and tuple(base[2]) != tuple(rn[2])


def _join_swap_body_refs(w, q, p):
    clauses = list(w)
    proof = list(p)
    body = list(clauses[-1].body)
    body.reverse()
    clauses[-1] = Clause(tuple(body), clauses[-1].head)
    refs = list(proof[-1].premise_steps)
    refs.reverse()
    proof[-1] = ProofStep(proof[-1].clause_index, tuple(refs), proof[-1].conclusion)
    return tuple(clauses), q, tuple(proof)


def test_join_body_refs_joint_swap():
    w, q, p = join_proof()
    k0 = _key(w, q, p)
    sw = _join_swap_body_refs(w, q, p)
    assert _key(sw[0], sw[1], sw[2]) == k0
    assert w[-1].body != sw[0][-1].body and p[-1].premise_steps != sw[2][-1].premise_steps


def _join_world_swap(w, q, p):
    clauses = list(w)
    clauses[0], clauses[1] = clauses[1], clauses[0]
    p0 = ProofStep(1, p[0].premise_steps, p[0].conclusion)
    p1 = ProofStep(0, p[1].premise_steps, p[1].conclusion)
    p2 = ProofStep(2, p[2].premise_steps, p[2].conclusion)
    return tuple(clauses), q, (p0, p1, p2)


def test_join_world_step_swap():
    w, q, p = join_proof()
    k0 = _key(w, q, p)
    sw = _join_world_swap(w, q, p)
    assert _key(sw[0], sw[1], sw[2]) == k0
    assert sw[2][-1].conclusion == p[-1].conclusion and sw[2][-1].premise_steps == p[-1].premise_steps


def test_purity():
    wj, qj, pj = join_proof()
    wf, qf, pf = fact_proof("p", "a", "b")
    wm, qm, pm = m6_aa()
    sj = _snapshot(wj, qj, pj)
    sf = _snapshot(wf, qf, pf)
    sm = _snapshot(wm, qm, pm)
    k1 = motif.canonical_motif_key(wj, qj, pj)
    motif.canonical_motif_key(wf, qf, pf)
    motif.canonical_motif_key(wm, qm, pm)
    k2 = motif.canonical_motif_key(wj, qj, pj)
    assert tolist(k1) == tolist(k2)
    assert _snapshot(wj, qj, pj) == sj
    assert _snapshot(wf, qf, pf) == sf
    assert _snapshot(wm, qm, pm) == sm


def test_purity_m6_full():
    wm, qm, pm = m6_aa()
    sm = _snapshot(wm, qm, pm)
    motif.canonical_motif_key(wm, qm, pm, max_steps=20, max_orientations=100)
    assert _snapshot(wm, qm, pm) == sm


# ---------- 组 C：六类支持区分 ----------

def test_m3_two_step():
    w1, q1, p1 = m3_copy()
    w2, q2, p2 = m3_inv()
    verify_proof(tuple(w1), q1, p1)
    verify_proof(tuple(w2), q2, p2)
    assert _key(w1, q1, p1) != _key(w2, q2, p2)


def test_m3_three_step():
    w1, q1, p1 = m3_extend()
    w2, q2, p2 = m3_extend_inv()
    verify_proof(tuple(w1), q1, p1)
    verify_proof(tuple(w2), q2, p2)
    assert _key(w1, q1, p1) != _key(w2, q2, p2)


def test_m5_ab_ba():
    w1, q1, p1 = m5_ab()
    w2, q2, p2 = m5_ba()
    verify_proof(tuple(w1), q1, p1)
    verify_proof(tuple(w2), q2, p2)
    k1 = _key(w1, q1, p1)
    k2 = _key(w2, q2, p2)
    assert k1 != k2
    sw = _join_swap_body_refs(w1, q1, p1)
    assert _key(sw[0], sw[1], sw[2]) == k1


def test_m6_ab():
    w1, q1, p1 = m6_aa()
    w2, q2, p2 = m6_ab()
    verify_proof(tuple(w1), q1, p1)
    verify_proof(tuple(w2), q2, p2)
    k1 = _key(w1, q1, p1)
    k2 = _key(w2, q2, p2)
    assert k1 != k2
    w3 = (fact("z", "a", "b"), fact("a", "b", "c"), fact("z", "a", "d"),
          fact("a", "d", "c"),
          rule("m", "?x", "?z", ("z", "?x", "?y"), ("a", "?y", "?z")),
          rule("n", "?x", "?z", ("m", "?x", "?z"), ("m", "?x", "?z")))
    q3 = atom("n", "a", "c")
    p3 = (step(0, (), "z", "a", "b"), step(1, (), "a", "b", "c"),
          step(4, (0, 1), "m", "a", "c"), step(2, (), "z", "a", "d"),
          step(3, (), "a", "d", "c"), step(4, (3, 4), "m", "a", "c"),
          step(5, (2, 5), "n", "a", "c"))
    assert _key(w3, q3, p3) == k2


def test_m7_relation_reuse():
    w1, q1, p1 = m7_cyclic()
    w2, q2, p2 = m7_variant()
    verify_proof(tuple(w1), q1, p1)
    verify_proof(tuple(w2), q2, p2)
    assert _key(w1, q1, p1) != _key(w2, q2, p2)


def test_m8_schema_constant():
    w1, q1, p1 = m8_var()
    w2, q2, p2 = m8_const()
    verify_proof(tuple(w1), q1, p1)
    verify_proof(tuple(w2), q2, p2)
    assert _key(w1, q1, p1) != _key(w2, q2, p2)


def test_m9_repeated():
    w1, q1, p1 = m9()
    verify_proof(tuple(w1), q1, p1)
    w2, q2, p2 = copy_proof("p", "q", "a", "b")
    verify_proof(tuple(w2), q2, p2)
    assert _key(w1, q1, p1) != _key(w2, q2, p2)
    assert len(_key(w1, q1, p1)[1]) == 3


def test_m9_shared_refs_rejected():
    w = (fact("p", "a", "b"), rule("q", "?x", "?y", ("p", "?x", "?y"), ("p", "?x", "?y")))
    p = (step(0, (), "p", "a", "b"), step(1, (0, 0), "q", "a", "b"))
    with pytest.raises(LogicValidationError):
        canonical_proof_key(tuple(w), atom("q", "a", "b"), p, max_steps=20)


# ---------- 组 D：委托／预算／错误 ----------

def test_delegation_once_identity():
    w, q, p = fact_proof("p", "a", "b")
    calls = []
    orig = motif.canonical_proof_key
    def spy(*a, **kw):
        calls.append((a, kw))
        return orig(*a, **kw)
    motif.canonical_proof_key = spy
    try:
        motif.canonical_motif_key(w, q, p, max_steps=7, max_orientations=10)
    finally:
        motif.canonical_proof_key = orig
    assert len(calls) == 1
    args, kw = calls[0]
    assert tolist(args[0]) == tolist(tuple(w)) and args[1] is q and tolist(args[2]) == tolist(tuple(p))
    assert kw["max_steps"] == 7


def test_delegation_default_steps():
    w, q, p = fact_proof("p", "a", "b")
    calls = []
    orig = motif.canonical_proof_key
    def spy(*a, **kw):
        calls.append((a, kw))
        return orig(*a, **kw)
    motif.canonical_proof_key = spy
    try:
        motif.canonical_motif_key(w, q, p)
    finally:
        motif.canonical_proof_key = orig
    assert len(calls) == 1
    kw = calls[0][1]
    assert kw.get("max_steps") in (None, 10000)


def test_sentinel_identity():
    w, q, p = fact_proof("p", "a", "b")
    orig = motif.canonical_proof_key
    for msg in ("s0", "s1"):
        sentinel = LogicValidationError(msg + "-sentinel")
        def raiser(*a, _sentinel=sentinel, **kw):
            raise _sentinel
        motif.canonical_proof_key = raiser
        try:
            with pytest.raises(LogicValidationError) as exc:
                motif.canonical_motif_key(w, q, p, max_steps=100, max_orientations=10)
            assert exc.value is sentinel
        finally:
            motif.canonical_proof_key = orig


def test_delegate_before_O():
    w, q, p = fact_proof("p", "a", "b")
    orig = motif.canonical_proof_key
    sentinel = LogicValidationError("t0012-fail")
    def raiser(*a, _sentinel=sentinel, **kw):
        raise _sentinel
    motif.canonical_proof_key = raiser
    try:
        with pytest.raises(LogicValidationError) as exc:
            motif.canonical_motif_key(w, q, p, max_steps=100, max_orientations=-1)
        assert exc.value is sentinel
    finally:
        motif.canonical_proof_key = orig


def test_empty_proof_error():
    w, q, p = fact_proof("p", "a", "b")
    with pytest.raises((LogicValidationError, ProofLimitError)):
        motif.canonical_motif_key(w, q, (), max_steps=10, max_orientations=1)


def test_all_budget_errors():
    w, q, p = fact_proof("p", "a", "b")
    for bad in (None, True, False, 0, -1, 1.5, "10", 10.0):
        with pytest.raises(LogicValidationError):
            motif.canonical_motif_key(w, q, p, max_steps=10, max_orientations=bad)
    with pytest.raises(LogicValidationError) as exc:
        motif.canonical_motif_key(w, q, p, max_steps=10, max_orientations=-10**5000)
    assert "must be a non-bool positive integer" in str(exc.value)


def test_positive_giant_budget():
    w, q, p = fact_proof("p", "a", "b")
    motif.canonical_motif_key(w, q, p, max_steps=10, max_orientations=10**5000)


def test_generator_consumed():
    wf = (fact("p", "a", "b"),)
    q = atom("p", "a", "b")
    def gen():
        yield step(0, (), "p", "a", "b")
    g = gen()
    with pytest.raises(LogicValidationError):
        motif.canonical_motif_key(wf, q, g, max_steps=10, max_orientations=1)
    # 正确版在 verify_proof 中先检查类型再迭代，不消费生成器；mutant 会先 tuple() 消耗。assert list(g) != []
    assert list(g) != []


def test_signature_type():
    w, q, p = fact_proof("p", "a", "b")
    with pytest.raises(TypeError):
        motif.canonical_motif_key(w, q, p, max_steps=10, max_orientations=1, extra=1)


def test_all():
    assert motif.__all__ == ["canonical_motif_key", "MotifLimitError"]


# ---------- 组 D 预算边界 ----------

def test_budget_boundaries():
    wj, qj, pj = join_proof()
    wf, qf, pf = fact_proof("p", "a", "b")
    wm, qm, pm = m6_aa()
    assert _key(wf, qf, pf, max_steps=10, max_orientations=1) == _key(wf, qf, pf)
    assert _key(wj, qj, pj, max_steps=10, max_orientations=2) == _key(wj, qj, pj)
    with pytest.raises(motif.MotifLimitError) as exc:
        motif.canonical_motif_key(wj, qj, pj, max_steps=10, max_orientations=1)
    assert str(exc.value) == "motif.max_orientations insufficient for complete canonicalization"
    k_full = _key(wm, qm, pm, max_steps=10, max_orientations=8)
    assert _key(wm, qm, pm) == k_full
    with pytest.raises(motif.MotifLimitError):
        motif.canonical_motif_key(wm, qm, pm, max_steps=10, max_orientations=7)


# ---------- 组 E：长链 ----------

def test_long_chain():
    w, q, p = long_chain()
    verify_proof(tuple(w), q, p)
    stream = tolist(motif.canonical_motif_key(w, q, p, max_steps=1201, max_orientations=1))[1]
    assert len(stream) == 1201
    for i in range(1200):
        node = stream[i]
        assert node[0] == (i, 0, 1)
        assert node[1] == (i, ("v", 0), ("v", 1))
        assert node[2] == ((i + 1, ("v", 0), ("v", 1)),)
    leaf = stream[1200]
    assert leaf[0] == (1200, 0, 1)
    assert leaf[1] == (1200, ("c", 0), ("c", 1))
    assert leaf[2] == ()


# ---------- 组 F：硬隔离 ----------

_ISOLATION_SCRIPT = '''
import sys, importlib, json
sys.path.insert(0, @SRC_DIR@)  # injected path, before any banned import
BLOCKED = [
    "torch", "yaml",
    "kmesh.logic.engine", "kmesh.logic.reference_engine", "kmesh.logic.proof_enumeration",
]
class BlockFinder:
    def __init__(self, roots):
        self.roots = roots
    def find_spec(self, fullname, path=None, target=None):
        for r in self.roots:
            if fullname == r or fullname.startswith(r + "."):
                raise ModuleNotFoundError("t0014-blocked: " + fullname, fullname)
        return None
finder = BlockFinder(BLOCKED)
sys.meta_path.insert(0, finder)
try:
    for r in BLOCKED:
        try:
            importlib.import_module(r)
            print("UNBLOCKED-R:" + r)
            sys.exit(1)
        except ModuleNotFoundError as e:
            assert "t0014-blocked" in str(e), str(e)
            print("BLOCKED-R:" + r)
    for r in BLOCKED:
        try:
            importlib.import_module(r + ".submod")
            print("UNBLOCKED-S:" + r + ".submod")
            sys.exit(1)
        except ModuleNotFoundError as e:
            assert "t0014-blocked" in str(e), str(e)
            print("BLOCKED-S:" + r + ".submod")
    from kmesh.logic.types import Atom, Clause
    from kmesh.logic.proof import ProofStep
    from kmesh.logic import motif
    def atom(p, x, y):
        return Atom(p, (x, y))
    def fact(p, x, y):
        return Clause((), atom(p, x, y))
    def rule(h, hx, hy, *body):
        return Clause(tuple(atom(b[0], b[1], b[2]) for b in body), atom(h, hx, hy))
    def step(ci, refs, p, x, y):
        return ProofStep(ci, tuple(refs), atom(p, x, y))
    w1 = (fact("p", "a", "b"),)
    q1 = atom("p", "a", "b")
    p1 = (step(0, (), "p", "a", "b"),)
    motif.canonical_motif_key(tuple(w1), q1, p1, max_steps=20, max_orientations=100)
    w2 = (fact("p", "a", "b"), fact("q", "b", "c"),
          rule("r", "?x", "?z", ("p", "?x", "?y"), ("q", "?y", "?z")))
    q2 = atom("r", "a", "c")
    p2 = (step(0, (), "p", "a", "b"), step(1, (), "q", "b", "c"),
          step(2, (0, 1), "r", "a", "c"))
    motif.canonical_motif_key(tuple(w2), q2, p2, max_steps=20, max_orientations=100)
    banned = set()
    for m in sys.modules:
        for r in BLOCKED:
            if m == r or m.startswith(r + "."):
                banned.add(m)
    if banned:
        print("BAD:" + ",".join(sorted(banned)))
        sys.exit(1)
    print("ISOLATION-OK")
finally:
    if finder in sys.meta_path:
        sys.meta_path.remove(finder)
'''

def test_hard_isolation():
    root = Path(__file__).resolve().parents[2]
    src_dir = str(root / "src")
    script = _ISOLATION_SCRIPT.replace("@SRC_DIR@", json.dumps(src_dir))
    env = dict(os.environ)
    env["PYTHONPATH"] = src_dir
    env["PYTHONHASHSEED"] = "0"
    env["CUDA_VISIBLE_DEVICES"] = ""
    r = subprocess.run([sys.executable, "-c", script],
                       capture_output=True, text=True, timeout=120, env=env)
    assert r.returncode == 0, "exit=%d\n%s\n%s" % (r.returncode, r.stdout, r.stderr)
    assert "BLOCKED-R:torch" in r.stdout
    assert "BLOCKED-S:torch.submod" in r.stdout
    assert "ISOLATION-OK" in r.stdout
    assert "BAD:" not in r.stdout
    assert "UNBLOCKED" not in r.stdout
