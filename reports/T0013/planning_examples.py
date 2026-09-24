"""Verify proposed count fixtures using accepted T0009/T0012 APIs only.

This is planning evidence, not the new count API or a Pi test dependency.
"""
import json
from pathlib import Path

from kmesh.logic.derivations import DerivationLimitError
from kmesh.logic.proof import verify_proof
from kmesh.logic.proof_enumeration import ProofEnumerationLimitError, enumerate_proofs
from kmesh.logic.proof_key import canonical_proof_key
from kmesh.logic.types import Atom, Clause, LogicValidationError

ROOT = Path(__file__).resolve().parents[2]


def a(pred, x, y):
    return Atom(pred, (x, y))


def fact(pred, x, y):
    return Clause((), a(pred, x, y))


def main():
    copy = Clause((a("p", "?x", "?y"),), a("q", "?x", "?y"))
    alpha_copy = Clause((a("p", "?u", "?v"),), a("q", "?u", "?v"))
    inv = Clause((a("p", "?x", "?y"),), a("q", "?y", "?x"))
    shared = (fact("p", "a", "a"), fact("s", "a", "a"),
              Clause((a("s", "?x", "?y"),), a("p", "?x", "?y")))
    nonsymmetric = Clause((a("p", "?z", "?x"), a("p", "?x", "?y")), a("q", "?x", "?x"))
    symmetric = Clause((a("p", "?x", "?y"), a("p", "?x", "?y")), a("q", "?x", "?y"))
    join_world = (fact("p", "a", "b"), fact("p", "a", "d"),
                  fact("q", "b", "c"), fact("q", "d", "c"),
                  Clause((a("p", "?x", "?y"), a("q", "?y", "?z")), a("r", "?x", "?z")))
    cases = (
        ("U0", (), a("p", "a", "b"), (1, 1, 1), 0, 0),
        ("U1", (fact("p", "a", "b"),), a("p", "a", "b"), (1, 1, 1), 1, 1),
        ("U2", (fact("p", "a", "b"), fact("p", "a", "b")), a("p", "a", "b"), (1, 2, 2), 2, 1),
        ("U3", (fact("p", "a", "b"), fact("p", "a", "b"), copy, alpha_copy), a("q", "a", "b"), (2, 4, 10), 4, 1),
        ("U4", (fact("p", "a", "a"), copy, inv), a("q", "a", "a"), (2, 3, 5), 2, 2),
        ("U5", (*shared, nonsymmetric), a("q", "a", "a"), (3, 4, 20), 4, 4),
        ("U6", (*shared, symmetric), a("q", "a", "a"), (3, 4, 20), 4, 3),
        ("U7", join_world, a("r", "a", "c"), (6, 6, 10), 2, 2),
        ("U8", (fact("p", "a", "b"), copy), a("missing", "a", "b"), (1, 2, 1), 0, 0),
    )
    rows = []
    for name, world, query, (c, d, s), raw, distinct in cases:
        proofs = enumerate_proofs(world, query, max_fact_checks=c, max_derivations=d, max_proof_steps=s)
        assert len(proofs) == raw, name
        assert all(verify_proof(world, query, proof, max_steps=s) is True for proof in proofs), name
        keys = {canonical_proof_key(world, query, proof, max_steps=s) for proof in proofs}
        assert len(keys) == distinct, (name, len(keys))
        rows.append(dict(name=name, budgets=dict(C=c, D=d, S=s), raw=raw,
                         canonical=distinct, returned_lengths=[len(p) for p in proofs]))
    budgets = dict(max_fact_checks=3, max_derivations=4, max_proof_steps=20)
    boundaries = []
    for field, error in (("max_fact_checks", DerivationLimitError),
                         ("max_derivations", DerivationLimitError),
                         ("max_proof_steps", ProofEnumerationLimitError)):
        reduced = budgets | {field: budgets[field] - 1}
        try:
            enumerate_proofs((*shared, symmetric), a("q", "a", "a"), **reduced)
        except error as exc:
            boundaries.append(dict(field=field, exception=type(exc).__name__, message=str(exc)))
        else:
            raise AssertionError((field, "expected exhaustion"))
    cyclic = (fact("p", "a", "b"), Clause((a("r", "?x", "?y"),), a("r", "?x", "?y")))
    for query in (a("p", "a", "b"), a("missing", "a", "b")):
        try:
            enumerate_proofs(cyclic, query)
        except LogicValidationError as exc:
            assert str(exc) == "dependency.clauses: cyclic predicate dependency"
        else:
            raise AssertionError("cycle must precede fact/absent query result")
    out = ROOT / "reports/T0013/planning-examples/examples.json"
    with out.open("x") as stream:
        stream.write(json.dumps(dict(result="PASS", fixtures=rows, budget_failures=boundaries,
                                     unrelated_cycle_rejections=2, product_implemented=False), indent=2) + "\n")
    print("PASS: 9 hand-counted fixtures, 3 exact budget failures, 2 unrelated-cycle cases")


if __name__ == "__main__":
    main()
