"""Hand-authored fixtures checked against accepted T0008/T0009/T0006.

This does not implement minimum_proof_depth. Only individual supplied proof
sequences are measured, after independent verification; expected worlds,
depths, raw-proof heights and direct-enumeration budgets are written explicitly.
"""
from kmesh.logic.derivations import DerivationLimitError, enumerate_derivations
from kmesh.logic.proof import verify_proof
from kmesh.logic.proof_enumeration import enumerate_proofs
from kmesh.logic.types import Atom, Clause


def atom(pred, x="a", y="b"):
    return Atom(pred, (x, y))


def fact(pred, x="a", y="b"):
    return Clause((), atom(pred, x, y))


def rule(body, head):
    return Clause(tuple(atom(p, "?x", "?y") for p in body), atom(head, "?x", "?y"))


shortcut = (fact("p"), rule(("p",), "m"), rule(("m",), "q"), rule(("p",), "q"))
join = (
    fact("p"), fact("p", "b", "c"),
    Clause((atom("p", "?x", "?y"), atom("p", "?y", "?z")), atom("r", "?x", "?z")),
)
irrelevant = (fact("q"), fact("p"), rule(("p",), "u"), rule(("u",), "v"), rule(("v",), "z"))
balanced = (
    fact("a"), fact("b"), fact("c"), fact("d"),
    rule(("a",), "m"), rule(("m",), "n"), rule(("n",), "z"),
    rule(("a", "b"), "u"), rule(("c", "d"), "v"), rule(("u", "v"), "z"),
)
# name, clauses, query, expected minimum, actual C, actual D, raw-proof heights
EXAMPLES = (
    ("H0", (), atom("q"), None, 0, 0, ()),
    ("H1", (fact("p"),), atom("p"), 0, 0, 1, (0,)),
    ("H1-reversed", (fact("p"),), atom("p", "b", "a"), None, 0, 1, ()),
    ("H2", (fact("p"), rule(("p",), "q")), atom("q"), 1, 1, 2, (1,)),
    ("H3", (fact("p"), fact("t"), rule(("p",), "u"), rule(("u",), "v"),
            rule(("t",), "w"), rule(("v", "w"), "z")), atom("z"), 3, 5, 6, (3,)),
    ("H4", shortcut, atom("q"), 1, 3, 4, (2, 1)),
    ("H5", shortcut + (rule(("q",), "z"),), atom("z"), 2, 4, 5, (3, 2)),
    ("H6-rule-first", (fact("p"), rule(("p",), "q"), fact("q")), atom("q"), 0, 1, 3, (1, 0)),
    ("H6-fact-first", (fact("p"), fact("q"), rule(("p",), "q")), atom("q"), 0, 1, 3, (0, 1)),
    ("H7", (fact("p"), rule(("p", "p"), "q")), atom("q"), 1, 2, 2, (1,)),
    ("H8", join, atom("r", "a", "c"), 1, 6, 3, (1,)),
    ("H8-reversed", join, atom("r", "c", "a"), None, 6, 3, ()),
    ("H9-a", (fact("q"), fact("p", "c", "d"), rule(("p",), "q")), atom("q"), 0, 1, 3, (0,)),
    ("H9-c", (fact("q"), fact("p", "c", "d"), rule(("p",), "q")), atom("q", "c", "d"), 1, 1, 3, (1,)),
    ("H10", (rule(("p",), "q"),), atom("q"), None, 0, 0, ()),
    ("H11", irrelevant, atom("q"), 0, 3, 5, (0,)),
    ("H11-absent", irrelevant, atom("missing"), None, 3, 5, ()),
    ("H12", balanced, atom("z"), 2, 9, 10, (3, 2)),
)


def checked_height(clauses, query, proof):
    assert verify_proof(clauses, query, proof)
    heights = []
    for step in proof:
        heights.append(0 if not step.premise_steps else 1 + max(heights[i] for i in step.premise_steps))
    return heights[-1]


def main():
    for name, clauses, query, minimum, c, d, expected in EXAMPLES:
        budgets = dict(max_fact_checks=max(1, c), max_derivations=max(1, d))
        records = enumerate_derivations(clauses, **budgets)
        assert len(records) == d, name
        for key, cost in (("max_fact_checks", c), ("max_derivations", d)):
            if cost < 2:
                continue
            try:
                enumerate_derivations(clauses, **(budgets | {key: cost - 1}))
            except DerivationLimitError as exc:
                assert str(exc) == f"enumerate.{key} exhausted before enumeration completed", name
            else:
                raise AssertionError((name, key, "expected exhaustion"))
        proofs = enumerate_proofs(clauses, query, **budgets)
        observed = tuple(checked_height(clauses, query, proof) for proof in proofs)
        assert observed == expected, (name, observed, expected)
        assert (min(expected) if expected else None) == minimum, name
        if name == "H12":
            assert tuple(map(len, proofs)) == (4, 7)
        print(f"{name}: C={c}, D={d}, verified raw heights={observed}, hand minimum={minimum}")
    print("PASS: 18 hand-authored query fixtures; new depth API remains unimplemented")


if __name__ == "__main__":
    main()
