"""Check hand-written clause keys using finite bijection enumeration.

Planning oracle only: deliberately enumerates all variable bijections;
does not implement or import the future head-first product algorithm.
"""
from itertools import permutations
import json

from kmesh.logic.types import Atom, Clause


def atom(pred, x, y):
    return Atom(pred, (x, y))


def v(index):
    return ("v", index)


def c(name):
    return ("c", name)


def a(pred, x, y):
    return (pred, x, y)


CASES = [
    ("K0", Clause((), atom("p", "a", "b")),
     a("p", c("a"), c("b")), ()),
    ("K1", Clause((atom("p", "?x", "?y"),), atom("q", "?x", "?y")),
     a("q", v(0), v(1)), (a("p", v(0), v(1)),)),
    ("K2", Clause((atom("p", "?x", "?y"),), atom("q", "?y", "?x")),
     a("q", v(0), v(1)), (a("p", v(1), v(0)),)),
    ("K3", Clause((atom("p", "?x", "?y"), atom("q", "?y", "?z")), atom("r", "?x", "?z")),
     a("r", v(0), v(1)), (a("p", v(0), v(2)), a("q", v(2), v(1)))),
    ("K4", Clause((atom("p", "?x", "?y"), atom("q", "?x", "?y")), atom("r", "?x", "?y")),
     a("r", v(0), v(1)), (a("p", v(0), v(1)), a("q", v(0), v(1)))),
    ("K5", Clause((atom("p", "?u", "?v"), atom("q", "?v", "?w")), atom("r", "a", "b")),
     a("r", c("a"), c("b")), (a("p", v(0), v(1)), a("q", v(1), v(2)))),
    ("K6", Clause((atom("p", "?x", "x"),), atom("q", "?x", "x")),
     a("q", v(0), c("x")), (a("p", v(0), c("x")),)),
    ("K7", Clause((atom("p", "a", "b"),), atom("q", "b", "a")),
     a("q", c("b"), c("a")), (a("p", c("a"), c("b")),)),
    ("K8", Clause((atom("p", "?z", "?x"), atom("p", "?x", "?y")), atom("q", "?x", "?x")),
     a("q", v(0), v(0)), (a("p", v(0), v(1)), a("p", v(2), v(0)))),
    ("K9", Clause((atom("p", "?a", "?b"), atom("q", "?c", "?d")), atom("r", "a", "b")),
     a("r", c("a"), c("b")), (a("p", v(0), v(1)), a("q", v(2), v(3)))),
    ("K10", Clause((atom("p", "?x", "?y"), atom("p", "?x", "?y")), atom("q", "?x", "?y")),
     a("q", v(0), v(1)), (a("p", v(0), v(1)), a("p", v(0), v(1)))),
]


def finite_oracle(clause):
    variables = sorted(set().union(clause.head.variables, *(b.variables for b in clause.body)))
    candidates = []
    for indexes in permutations(range(len(variables))):
        assignment = dict(zip(variables, indexes))

        def encode(value):
            terms = tuple(v(assignment[t]) if t.startswith("?") else c(t) for t in value.args)
            return (value.pred, *terms)

        for body in permutations(clause.body):
            candidates.append(("clause_key_v1", encode(clause.head), tuple(encode(b) for b in body)))
    return min(candidates), len(candidates)


def main():
    output = []
    keys = {}
    for name, clause, head, body in CASES:
        actual, count = finite_oracle(clause)
        expected = ("clause_key_v1", head, body)
        assert actual == expected, (name, actual, expected)
        keys[name] = actual
        output.append(dict(case=name, expected_key=expected, enumerated_candidates=count))
    assert keys["K1"] != keys["K2"] and keys["K1"] != keys["K10"]
    disconnected = Clause((atom("p", "?x", "?u"), atom("q", "?v", "?z")), atom("r", "?x", "?z"))
    assert keys["K3"] != finite_oracle(disconnected)[0]
    k8a = Clause((atom("p", "?a", "?z"), atom("p", "?z", "?b")), atom("q", "?z", "?z"))
    assert finite_oracle(k8a)[0] == keys["K8"]
    symmetric = Clause((atom("p", "a", "a"), atom("p", "b", "b")), atom("q", "c", "c"))
    assert finite_oracle(symmetric)[0] == finite_oracle(Clause(tuple(reversed(symmetric.body)), symmetric.head))[0]
    print(json.dumps(dict(result="PASS", hand_written_cases=output,
                         extra_cases=["K8a alpha variant", "symmetric ground premise swap"],
                         implementation="not_run; no new product module imported"), indent=2))


if __name__ == "__main__":
    main()
