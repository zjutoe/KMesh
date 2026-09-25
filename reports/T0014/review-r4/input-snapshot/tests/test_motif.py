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
         rule("r", "?y", "?x", ("q", "?x", "?y")))
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
    pn = tuple((s.clause_index, s.premise_steps, _atom_plain(s.conclusion)) for s in p)
    raw = json.dumps([cl, qn, pn], ensure_ascii=False, sort_keys=True).encode("utf-8")
    return (cl, qn, pn, hashlib.sha256(raw).hexdigest())


def _key(w, q, p, **kw):
    return tolist(motif.canonical_motif_key(w, q, p, **kw))


# ---------- 组 A：完整手算锚点 ----------

def test_anchor_fact_literal():
    w, q, p = fact_proof("p", "a", "b")
    assert verify_proof(tuple(w), q, p) is True
    assert _key(w, q, p, max_steps=20, max_orientations=10) == FACT_KEY


def test_anchor_copy_literal():
    w, q, p = copy_proof("p", "q", "a", "b")
    assert verify_proof(tuple(w), q, p) is True
    assert _key(w, q, p, max_steps=20, max_orientations=10) == COPY_KEY


def test_anchor_join_literal():
    w, q, p = join_proof()
    assert verify_proof(tuple(w), q, p) is True
    assert _key(w, q, p, max_steps=20, max_orientations=10) == JOIN_KEY


def test_key_container_types():
    anchors = (fact_proof("p", "a", "b"), copy_proof("p", "q", "a", "b"), join_proof())
    keys = [motif.canonical_motif_key(*a) for a in anchors]
    assert all(type(k) is tuple and len(k) == 2 for k in keys)
    assert all(type(k[0]) is str and k[0] == "proof_motif_v1" for k in keys)
    for k in keys:
        stream = k[1]
        assert type(stream) is tuple
        for node in stream:
            assert type(node) is tuple and len(node) == 3
            ground, head, body = node
            assert type(ground) is tuple and len(ground) == 3
            assert all(type(g) is int and g >= 0 for g in ground)
            assert type(head) is tuple and len(head) == 3
            assert type(head[0]) is int and head[0] == ground[0]
            assert type(head[1]) is tuple and len(head[1]) == 2
            assert type(head[1][0]) is str and head[1][0] in ("c", "v")
            assert type(head[1][1]) is int and head[1][1] >= 0
            assert type(head[2]) is tuple and len(head[2]) == 2
            assert type(head[2][0]) is str and head[2][0] in ("c", "v")
            assert type(head[2][1]) is int and head[2][1] >= 0
            assert type(body) is tuple
            for b in body:
                assert type(b) is tuple and len(b) == 3
                assert type(b[0]) is int and b[0] >= 0
                assert type(b[1]) is tuple and len(b[1]) == 2
                assert type(b[1][0]) is str and b[1][0] in ("c", "v")
                assert type(b[1][1]) is int and b[1][1] >= 0
                assert type(b[2]) is tuple and len(b[2]) == 2
                assert type(b[2][0]) is str and b[2][0] in ("c", "v")
                assert type(b[2][1]) is int and b[2][1] >= 0
    assert len(set(keys)) == 3
    d = {k: i for i, k in enumerate(keys)}
    assert len(d) == 3


def test_namespace_collide():
    w1, q1, p1 = fact_proof("p", "p", "a")
    w2, q2, p2 = fact_proof("q", "u", "v")
    assert _key(w1, q1, p1) == _key(w2, q2, p2)


def test_anchor_selfref_diff():
    w1 = (fact("p", "a", "a"),)
    q1 = atom("p", "a", "a")
    p1 = (step(0, (), "p", "a", "a"),)
    w2 = (fact("p", "a", "b"),)
    q2 = atom("p", "a", "b")
    p2 = (step(0, (), "p", "a", "b"),)
    assert verify_proof(tuple(w1), q1, p1) is True
    assert verify_proof(tuple(w2), q2, p2) is True
    assert _key(w1, q1, p1) != _key(w2, q2, p2)


def test_anchor_unused_fact():
    w1, q1, p1 = fact_proof("p", "a", "b")
    k1 = _key(w1, q1, p1)
    w2 = (fact("p", "a", "b"), fact("U", "V", "W"))
    assert _key(w2, q1, p1) == k1


# ---------- 组 B：真实变换与纯度 ----------

def _join_renamed(rel, ent, var):
    w = (fact(rel[0], ent[0], ent[1]), fact(rel[1], ent[1], ent[2]),
         rule(rel[2], var[0], var[2], (rel[0], var[0], var[1]), (rel[1], var[1], var[2])))
    q = atom(rel[2], ent[0], ent[2])
    p2 = (step(0, (), rel[0], ent[0], ent[1]), step(1, (), rel[1], ent[1], ent[2]),
          step(2, (0, 1), rel[2], ent[0], ent[2]))
    return w, q, p2


def test_join_rename_invariant():
    base = join_proof()
    k0 = _key(base[0], base[1], base[2])
    cases = [
        (["z", "a", "m"], ["a", "b", "c"], ["?x", "?y", "?z"]),
        (["p", "q", "r"], ["V", "U", "T"], ["?x", "?y", "?z"]),
        (["p", "q", "r"], ["a", "b", "c"], ["?u", "?v", "?w"]),
        (["z", "a", "m"], ["V", "U", "T"], ["?u", "?v", "?w"]),
    ]
    for rel, ent, var in cases:
        rn = _join_renamed(rel, ent, var)
        assert verify_proof(tuple(rn[0]), rn[1], rn[2]) is True
        assert _key(rn[0], rn[1], rn[2]) == k0
        assert rn[0] != base[0]


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


def _join_step_swap(w, q, p):
    # world unchanged; swap independent facts (steps 0 and 1); re-map rule refs (0,1)->(1,0)
    s0 = ProofStep(p[1].clause_index, (), p[1].conclusion)
    s1 = ProofStep(p[0].clause_index, (), p[0].conclusion)
    s2 = ProofStep(p[2].clause_index, (1, 0), p[2].conclusion)
    return w, q, (s0, s1, s2)


def test_join_world_step_swap():
    w, q, p = join_proof()
    k0 = _key(w, q, p)
    sw = _join_world_swap(w, q, p)
    assert verify_proof(tuple(sw[0]), sw[1], sw[2]) is True
    assert _key(sw[0], sw[1], sw[2]) == k0
    assert sw[2][-1].conclusion == p[-1].conclusion and sw[2][-1].premise_steps == p[-1].premise_steps
    ss = _join_step_swap(w, q, p)
    assert verify_proof(tuple(ss[0]), ss[1], ss[2]) is True
    assert _key(ss[0], ss[1], ss[2]) == k0
    assert ss[0] == w and ss[2][-1].premise_steps != p[-1].premise_steps


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
    assert verify_proof(tuple(w1), q1, p1) is True
    assert verify_proof(tuple(w2), q2, p2) is True
    assert _key(w1, q1, p1) != _key(w2, q2, p2)


def test_m3_three_step():
    w1, q1, p1 = m3_extend()
    w2, q2, p2 = m3_extend_inv()
    assert verify_proof(tuple(w1), q1, p1) is True
    assert verify_proof(tuple(w2), q2, p2) is True
    assert _key(w1, q1, p1) != _key(w2, q2, p2)


def test_m5_ab_ba():
    w1, q1, p1 = m5_ab()
    w2, q2, p2 = m5_ba()
    assert verify_proof(tuple(w1), q1, p1) is True
    assert verify_proof(tuple(w2), q2, p2) is True
    k1 = _key(w1, q1, p1)
    k2 = _key(w2, q2, p2)
    assert k1 != k2
    sw1 = _join_swap_body_refs(w1, q1, p1)
    assert verify_proof(tuple(sw1[0]), sw1[1], sw1[2]) is True
    assert _key(sw1[0], sw1[1], sw1[2]) == k1
    sw2 = _join_swap_body_refs(w2, q2, p2)
    assert verify_proof(tuple(sw2[0]), sw2[1], sw2[2]) is True
    assert _key(sw2[0], sw2[1], sw2[2]) == k2
    assert w2[-1].body != sw2[0][-1].body and p2[-1].premise_steps != sw2[2][-1].premise_steps
    assert k2 != k1


def _m6_ab_ent():
    # full-tree consistent entity rename: a->V, b->U, c->T, d->S; relations/vars/query synced
    w = (fact("f", "V", "U"), fact("g", "U", "T"), fact("f", "V", "S"),
         fact("g", "S", "T"),
         rule("p", "?x", "?z", ("f", "?x", "?y"), ("g", "?y", "?z")),
         rule("r", "?x", "?z", ("p", "?x", "?z"), ("p", "?x", "?z")))
    q = atom("r", "V", "T")
    p2 = (step(0, (), "f", "V", "U"), step(1, (), "g", "U", "T"),
          step(4, (0, 1), "p", "V", "T"), step(2, (), "f", "V", "S"),
          step(3, (), "g", "S", "T"), step(4, (3, 4), "p", "V", "T"),
          step(5, (2, 5), "r", "V", "T"))
    return w, q, p2


def test_m6_ab():
    w1, q1, p1 = m6_aa()
    w2, q2, p2 = m6_ab()
    assert verify_proof(tuple(w1), q1, p1) is True
    assert verify_proof(tuple(w2), q2, p2) is True
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
    assert verify_proof(tuple(w3), q3, p3) is True
    assert _key(w3, q3, p3) == k2
    we, qe, pe = _m6_ab_ent()
    assert verify_proof(tuple(we), qe, pe) is True
    assert _key(we, qe, pe) == k2


def test_m7_relation_reuse():
    w1, q1, p1 = m7_cyclic()
    w2, q2, p2 = m7_variant()
    assert verify_proof(tuple(w1), q1, p1) is True
    assert verify_proof(tuple(w2), q2, p2) is True
    assert _key(w1, q1, p1) != _key(w2, q2, p2)


def test_m8_schema_constant():
    w1, q1, p1 = m8_var()
    w2, q2, p2 = m8_const()
    assert verify_proof(tuple(w1), q1, p1) is True
    assert verify_proof(tuple(w2), q2, p2) is True
    assert _key(w1, q1, p1) != _key(w2, q2, p2)


def test_m9_repeated():
    w1, q1, p1 = m9()
    assert verify_proof(tuple(w1), q1, p1) is True
    w2, q2, p2 = copy_proof("p", "q", "a", "b")
    assert verify_proof(tuple(w2), q2, p2) is True
    assert _key(w1, q1, p1) != _key(w2, q2, p2)
    assert len(_key(w1, q1, p1)[1]) == 3


def test_m9_shared_refs_rejected():
    w = (fact("p", "a", "b"), rule("q", "?x", "?y", ("p", "?x", "?y"), ("p", "?x", "?y")))
    p = (step(0, (), "p", "a", "b"), step(1, (0, 0), "q", "a", "b"))
    q = atom("q", "a", "b")
    assert verify_proof(tuple(w), q, p) is True
    with pytest.raises(LogicValidationError) as exc:
        motif.canonical_motif_key(tuple(w), q, p, max_steps=20)
    assert type(exc.value) is LogicValidationError
    assert str(exc.value) == "proof_key.proof must be a single occurrence tree"


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
    a, kw = calls[0]
    assert a[0] is w and a[1] is q and a[2] is p
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
    a, kw = calls[0]
    assert a[0] is w and a[1] is q and a[2] is p
    assert kw["max_steps"] == 10000


def test_sentinel_identity():
    w, q, p = fact_proof("p", "a", "b")
    calls = []
    orig = motif.canonical_proof_key
    sentinel = LogicValidationError("t0012-logic-sentinel")
    def raiser(*a, **kw):
        calls.append((a, kw))
        raise sentinel
    for o in (10, -1):
        calls.clear()
        motif.canonical_proof_key = raiser
        try:
            with pytest.raises(LogicValidationError) as exc:
                motif.canonical_motif_key(w, q, p, max_steps=100, max_orientations=o)
            assert exc.value is sentinel
            assert type(exc.value) is LogicValidationError
            assert str(exc.value) == "t0012-logic-sentinel"
        finally:
            motif.canonical_proof_key = orig
        assert len(calls) == 1


def test_delegate_before_O():
    w, q, p = fact_proof("p", "a", "b")
    calls = []
    orig = motif.canonical_proof_key
    sentinel = ProofLimitError("t0012-limit-sentinel")
    def raiser(*a, **kw):
        calls.append((a, kw))
        raise sentinel
    motif.canonical_proof_key = raiser
    try:
        with pytest.raises(ProofLimitError) as exc:
            motif.canonical_motif_key(w, q, p, max_steps=100, max_orientations=-1)
        assert exc.value is sentinel
        assert type(exc.value) is ProofLimitError
        assert str(exc.value) == "t0012-limit-sentinel"
    finally:
        motif.canonical_proof_key = orig
    assert len(calls) == 1


def test_empty_proof_error():
    w, q, p = fact_proof("p", "a", "b")
    with pytest.raises(LogicValidationError) as exc:
        motif.canonical_motif_key(w, q, (), max_steps=10, max_orientations=1)
    assert type(exc.value) is LogicValidationError
    assert str(exc.value) == "proof_key.proof must be a valid proof of query"


def test_all_budget_errors():
    import sys
    w, q, p = fact_proof("p", "a", "b")
    g = getattr(sys, "get_int_max_str_digits", None)
    s = getattr(sys, "set_int_max_str_digits", None)
    assert g is not None and s is not None, "int str digits control required"
    old = g()
    s(4300)
    try:
        assert g() == 4300
        # illegal O: precise class and full text
        for bad, tname in ((None, "NoneType"), (True, "bool"), (False, "bool"),
                            (0, "int"), (-1, "int"), (1.5, "float"),
                            ("10", "str"), (10.0, "float")):
            with pytest.raises(LogicValidationError) as exc:
                motif.canonical_motif_key(w, q, p, max_steps=10, max_orientations=bad)
            assert type(exc.value) is LogicValidationError
            assert str(exc.value) == "motif.max_orientations must be a non-bool positive integer; got " + tname
        # +ve giant budgets (fact, B=0): full key equals fact literal; tests int str-digits path
        assert motif.canonical_motif_key(w, q, p, max_steps=10, max_orientations=10**4300) == FACT_KEY
        assert motif.canonical_motif_key(w, q, p, max_steps=10, max_orientations=10**5000) == FACT_KEY
        # -ve giant: illegal -> precise class/text, product never echoes the number
        with pytest.raises(LogicValidationError) as exc:
            motif.canonical_motif_key(w, q, p, max_steps=10, max_orientations=-10**5000)
        assert type(exc.value) is LogicValidationError
        assert str(exc.value) == "motif.max_orientations must be a non-bool positive integer; got int"
    finally:
        s(old)


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
        motif.canonical_motif_key(w, q)
    with pytest.raises(TypeError):
        motif.canonical_motif_key(w, q, p, 99, max_steps=10, max_orientations=1)
    with pytest.raises(TypeError):
        motif.canonical_motif_key(w, q, p, max_steps=10, max_orientations=1, extra=1)


def test_all():
    assert motif.__all__ == ["canonical_motif_key", "MotifLimitError"]


# ---------- 组 D 预算边界 ----------

def test_budget_boundaries():
    wj, qj, pj = join_proof()
    wf, qf, pf = fact_proof("p", "a", "b")
    wn, qn, pn = m9()
    m6s = (m6_aa(), m6_ab())
    assert _key(wf, qf, pf, max_steps=10, max_orientations=1) == _key(wf, qf, pf)
    assert _key(wj, qj, pj, max_steps=10, max_orientations=2) == _key(wj, qj, pj)
    # M9 (B=1, 2^1=2): 2 succeeds, 1 fails
    assert _key(wn, qn, pn, max_steps=10, max_orientations=2) == _key(wn, qn, pn)
    with pytest.raises(motif.MotifLimitError) as exc:
        motif.canonical_motif_key(wn, qn, pn, max_steps=10, max_orientations=1)
    assert type(exc.value) is motif.MotifLimitError
    assert str(exc.value) == "motif.max_orientations insufficient for complete canonicalization"
    with pytest.raises(motif.MotifLimitError) as exc:
        motif.canonical_motif_key(wj, qj, pj, max_steps=10, max_orientations=1)
    assert type(exc.value) is motif.MotifLimitError
    assert str(exc.value) == "motif.max_orientations insufficient for complete canonicalization"
    # M6 AA/AB (B=3, 2^3=8): 8 succeeds, 7 fails, both variants
    for wm, qm, pm in m6s:
        assert _key(wm, qm, pm, max_steps=10, max_orientations=8) == _key(wm, qm, pm)
        with pytest.raises(motif.MotifLimitError) as exc:
            motif.canonical_motif_key(wm, qm, pm, max_steps=10, max_orientations=7)
        assert type(exc.value) is motif.MotifLimitError
        assert str(exc.value) == "motif.max_orientations insufficient for complete canonicalization"


# ---------- 组 E：长链 ----------

def test_long_chain():
    w, q, p = long_chain()
    assert verify_proof(tuple(w), q, p) is True
    key = motif.canonical_motif_key(w, q, p, max_steps=1201, max_orientations=1)
    assert isinstance(key, tuple) and len(key) == 2 and key[0] == "proof_motif_v1"
    stream = key[1]
    assert isinstance(stream, tuple) and len(stream) == 1201
    # hashable & stable
    h = hash(key)
    assert isinstance(h, int)
    assert hash(key) == h
    # independent formula expectation
    expected = []
    for i in range(1200):
        expected.append(((i, 0, 1), (i, ("v", 0), ("v", 1)),
                         ((i + 1, ("v", 0), ("v", 1)),)))
    expected.append(((1200, 0, 1), (1200, ("c", 0), ("c", 1)), ()))
    expected = tuple(expected)
    assert stream == expected
    # sort order: root-first preorder = increasing node (relation) id
    assert [n[0][0] for n in stream] == list(range(1201))
    # per-header checks (kept)
    for i in range(1200):
        node = stream[i]
        assert node == ((i, 0, 1), (i, ("v", 0), ("v", 1)), ((i + 1, ("v", 0), ("v", 1)),))
    leaf = stream[1200]
    assert leaf == ((1200, 0, 1), (1200, ("c", 0), ("c", 1)), ())


# ---------- 组 F：硬隔离 ----------

_ISOLATION_SCRIPT = '''
import sys, importlib, types, os
sys.path.insert(0, @SRC_DIR@)
BLOCKED = [
    "torch", "yaml",
    "kmesh.logic.engine", "kmesh.logic.reference_engine", "kmesh.logic.proof_enumeration",
]
MSG = "t0014-blocked: "
class BlockFinder:
    def __init__(self, roots):
        self.roots = roots
    def find_spec(self, fullname, path=None, target=None):
        for r in self.roots:
            if fullname == r or fullname.startswith(r + "."):
                raise ModuleNotFoundError(MSG + fullname)
        return None
mf = BlockFinder(BLOCKED)
sys.meta_path.insert(0, mf)
try:
    for r in BLOCKED:
        try:
            importlib.import_module(r)
            print("UNBLOCKED-R:" + r)
            sys.exit(1)
        except ModuleNotFoundError as e:
            assert str(e) == MSG + r, "root wrong: " + repr(e)
            print("BLOCKED-R:" + r)
    for r in BLOCKED:
        mod = types.ModuleType(r)
        mod.__name__ = r
        mod.__path__ = [BlockFinder(BLOCKED)]
        sys.modules[r] = mod
        try:
            importlib.import_module(r + ".t0014_probe")
            print("UNBLOCKED-S:" + r + ".t0014_probe")
            sys.exit(1)
        except ModuleNotFoundError as e:
            assert str(e) == MSG + r + ".t0014_probe", "sub wrong: " + repr(e)
            print("BLOCKED-S:" + r + ".t0014_probe")
        finally:
            sys.modules.pop(r, None)
    from kmesh.logic.types import Atom, Clause
    from kmesh.logic.proof import ProofStep
    from kmesh.logic import motif
    want = os.path.realpath(os.path.join(sys.path[0], "kmesh", "logic", "motif.py"))
    assert os.path.realpath(motif.__file__) == want, "motif path: " + str(motif.__file__)
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
    r = subprocess.run([sys.executable, "-c", script],
                       capture_output=True, text=True, timeout=120, env=env)
    assert r.returncode == 0, "exit=%d\n%s\n%s" % (r.returncode, r.stdout, r.stderr)
    for tag in ("torch", "yaml", "kmesh.logic.engine",
               "kmesh.logic.reference_engine", "kmesh.logic.proof_enumeration"):
        assert "BLOCKED-R:" + tag in r.stdout, "missing " + tag
        assert "BLOCKED-S:" + tag + ".t0014_probe" in r.stdout, "missing sub " + tag
    assert "ISOLATION-OK" in r.stdout
    assert "BAD:" not in r.stdout
    assert "UNBLOCKED" not in r.stdout
