"""Check hand-authored T0009 examples against accepted T0006/T0008 only.

This is a planning check, not a proof enumerator or a product test oracle.
The expected proofs and intermediate-cache lengths below are explicit.
"""
import json
from pathlib import Path

from kmesh.logic.derivations import DerivationLimitError, enumerate_derivations
from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.types import Atom, Clause


def a(pred, x="a", y="b"):
    return Atom(pred, (x, y))


def fact(atom):
    return Clause((), atom)


def rule(body, head):
    return Clause(tuple(body), head)


def step(index, refs, atom):
    return ProofStep(index, refs, atom)


p = a("p")
q = a("q")
r = a("r")
s = a("s")
pv, qv, rv, sv = (a(name, "?x", "?y") for name in ("p", "q", "r", "s"))
p_ac, q_bc, q_bd = a("p", "a", "c"), a("q", "b", "c"), a("q", "b", "d")
r_ac, s_ca = a("r", "a", "c"), a("s", "c", "a")
q_ak, r_ak = a("q", "a", "k"), a("r", "a", "k")
join = rule((pv, a("q", "?y", "?z")), a("r", "?x", "?z"))
diamond = (fact(p), rule((pv,), qv), rule((pv,), rv), rule((qv, rv), sv))
double_diamond = (fact(p), fact(p), *diamond[1:])

# name, clauses, query, explicit proofs, C, D, intermediate-cache lengths
CASES = (
    ("P0", (), p, (), 0, 0, ()),
    ("P1", (fact(p),), p, ((step(0, (), p),),), 0, 1, (1,)),
    ("P2", (fact(p), rule((pv,), qv), rule((qv,), a("r", "?y", "?x"))),
     a("r", "b", "a"),
     ((step(0, (), p), step(1, (0,), q), step(2, (1,), a("r", "b", "a"))),),
     2, 3, (1, 2, 3)),
    ("P3", (fact(p), fact(q_bc), join, rule((rv,), a("s", "?y", "?x"))), s_ca,
     ((step(0, (), p), step(1, (), q_bc), step(2, (0, 1), r_ac), step(3, (2,), s_ca)),),
     3, 4, (1, 1, 3, 4)),
    ("P4", diamond, s,
     ((step(0, (), p), step(1, (0,), q), step(0, (), p), step(2, (2,), r), step(3, (1, 3), s)),),
     4, 4, (1, 2, 2, 5)),
    ("P5", (fact(p), fact(p_ac), rule((pv,), a("q", "?x", "k")),
             rule((a("q", "?x", "k"),), a("r", "?x", "k"))), r_ak,
     ((step(0, (), p), step(2, (0,), q_ak), step(3, (1,), r_ak)),
      (step(1, (), p_ac), step(2, (0,), q_ak), step(3, (1,), r_ak))),
     3, 5, (1, 1, 2, 2, 3, 3)),
    ("P6", (fact(p), fact(p), rule((pv, pv), qv)), q,
     tuple((step(u, (), p), step(v, (), p), step(2, (0, 1), q))
           for u, v in ((0, 0), (0, 1), (1, 0), (1, 1))),
     2, 3, (1, 1, 3, 3, 3, 3)),
    ("P7", double_diamond, s,
     tuple((step(u, (), p), step(2, (0,), q), step(v, (), p),
            step(3, (2,), r), step(4, (1, 3), s))
           for u, v in ((0, 0), (0, 1), (1, 0), (1, 1))),
     4, 5, (1, 1, 2, 2, 2, 2, 5, 5, 5, 5)),
    ("P8", (fact(q), fact(p), rule((pv,), qv)), q,
     ((step(0, (), q),), (step(1, (), p), step(2, (0,), q))),
     1, 3, (1, 1, 2)),
    ("P9", (fact(p), fact(a("q", "c", "d")),
             rule((p, a("q", "c", "d")), a("r", "e", "f"))), a("r", "e", "f"),
     ((step(0, (), p), step(1, (), a("q", "c", "d")), step(2, (0, 1), a("r", "e", "f"))),),
     2, 3, (1, 1, 3)),
    ("P10", (fact(p), fact(q_bc), fact(q_bd), join), r_ac,
     ((step(0, (), p), step(1, (), q_bc), step(3, (0, 1), r_ac)),),
     3, 5, (1, 1, 3)),
)


def main():
    assert not Path("src/kmesh/logic/proof_enumeration.py").exists()
    assert not Path("tests/test_proof_enumeration.py").exists()
    rows = []
    for name, clauses, query, proofs, checks, records, cache_lengths in CASES:
        actual = enumerate_derivations(clauses, max_fact_checks=max(1, checks),
                                       max_derivations=max(1, records))
        assert len(actual) == records, name
        for field, total in (("max_fact_checks", checks), ("max_derivations", records)):
            if total >= 2:
                budget = {"max_fact_checks": max(1, checks), "max_derivations": max(1, records)}
                budget[field] = total - 1
                try:
                    enumerate_derivations(clauses, **budget)
                except DerivationLimitError as exc:
                    assert str(exc) == f"enumerate.{field} exhausted before enumeration completed"
                else:
                    raise AssertionError((name, field, "budget did not exhaust"))
        for proof in proofs:
            assert verify_proof(clauses, query, proof, max_steps=len(proof)) is True, name
        rows.append(dict(case=name, C=checks, D=records, S=sum(cache_lengths),
                         output_lengths=[len(proof) for proof in proofs],
                         hand_authored_proofs_valid=True))
    valid = CASES[4][3][0]
    invalid = (*valid[:3], step(2, (1,), r), valid[4])
    assert verify_proof(diamond, s, invalid) is False
    result = {"result": "PASS", "cases": rows, "tampered_right_child_rejected": True,
              "long_chain_arithmetic": {"rules": 1200, "length": 1201, "S": 1201 * 1202 // 2},
              "limits": "Only accepted T0006/T0008 and explicit examples checked; T0009 unimplemented; S is hand-counted, not product-verified."}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
