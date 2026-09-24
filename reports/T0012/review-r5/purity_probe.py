"""Independent acceptance supplement: snapshot all three immutable inputs.

Pi's persistent regression snapshots K3 only. This retained review probe checks
the remaining K0/K5 inputs too; it does not modify the product or Pi tests.
"""
from copy import deepcopy
import json
from pathlib import Path

from kmesh.logic import proof_key
from kmesh.logic.proof import ProofStep
from kmesh.logic.types import Atom, Clause

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "reports/T0012/review-r5-purity/purity.json"


def atom(pred, a, b):
    return Atom(pred, (a, b))


def fact(pred, a, b):
    return Clause((), atom(pred, a, b))


def step(index, refs, pred, a, b):
    return ProofStep(index, refs, atom(pred, a, b))


def main():
    assert Path(proof_key.__file__).resolve() == ROOT / "src/kmesh/logic/proof_key.py"
    cases = {
        "K0": (
            (fact("p", "a", "b"),), atom("p", "a", "b"),
            (step(0, (), "p", "a", "b"),),
        ),
        "K3": (
            (fact("p", "a", "b"), fact("q", "b", "c"),
             Clause((atom("p", "?x", "?y"), atom("q", "?y", "?z")),
                    atom("r", "?x", "?z"))),
            atom("r", "a", "c"),
            (step(0, (), "p", "a", "b"), step(1, (), "q", "b", "c"),
             step(2, (0, 1), "r", "a", "c")),
        ),
        "K5": (
            (fact("p", "a", "a"), fact("s", "a", "a"),
             Clause((atom("s", "?x", "?y"),), atom("p", "?x", "?y")),
             Clause((atom("p", "?z", "?x"), atom("p", "?x", "?y")),
                    atom("q", "?x", "?x"))),
            atom("q", "a", "a"),
            (step(0, (), "p", "a", "a"), step(1, (), "s", "a", "a"),
             step(2, (1,), "p", "a", "a"), step(3, (0, 2), "q", "a", "a")),
        ),
    }
    before = deepcopy(cases)
    hashes = {name: hash(value) for name, value in cases.items()}
    sequence = ("K3", "K0", "K5", "K3")
    keys = []
    for name in sequence:
        keys.append(proof_key.canonical_proof_key(*cases[name]))
        for other, value in cases.items():
            assert value == before[other], (name, other, "structure mutated")
            assert hash(value) == hashes[other], (name, other, "hash changed")
    assert keys[0] == keys[-1]
    result = dict(result="PASS", sequence=sequence, snapshotted_inputs=list(cases),
                  all_structures_equal_after_each_call=True,
                  all_hashes_equal_after_each_call=True, first_last_key_equal=True,
                  scope="finite independent supplement; not a Pi test-suite result")
    assert not OUT.exists()
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: K0/K3/K5 complete pre-call snapshots unchanged after all four calls")


if __name__ == "__main__":
    main()
