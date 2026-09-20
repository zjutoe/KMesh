"""Independently check missing contract boundaries on the frozen product."""
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
from unittest.mock import patch

from kmesh.logic import depth as dm
from kmesh.logic.derivations import DerivationLimitError
from kmesh.logic.proof import verify_proof
from kmesh.logic.proof_enumeration import enumerate_proofs
from kmesh.logic.types import Atom, Clause, LogicValidationError

ROOT = Path.cwd()
OUT = Path("reports/T0010/review-r1-probes")


def expected_error(action, error_type, message):
    try:
        action()
    except error_type as exc:
        assert str(exc) == message
    else:
        raise AssertionError("expected error")


def transform(world, query, mode):
    def atom(a, index):
        pred = "Renamed" + a.pred if mode == "predicates" else a.pred
        args = tuple((f"?v{index}_{t[1:]}" if mode == "variables" else t) if t.startswith("?")
                     else ("Renamed" + t if mode == "entities" else t) for t in a.args)
        return Atom(pred, args)
    result = tuple(Clause(tuple(atom(a, i) for a in (c.body[::-1] if mode == "premises" else c.body)),
                          atom(c.head, i)) for i, c in enumerate(world))
    return (result[::-1] if mode == "clauses" else result), atom(query, 0)


def main():
    examples = runpy.run_path("reports/T0010/planning_examples.py")["EXAMPLES"]
    for name, clauses, query, want, c, d, _ in examples:
        kwargs = dict(max_fact_checks=max(1, c), max_derivations=max(1, d))
        actual = dm.minimum_proof_depth(clauses, query, **kwargs)
        assert actual is None if want is None else type(actual) is int and actual == want
        for key, cost in (("max_fact_checks", c), ("max_derivations", d)):
            if cost > 1:
                expected_error(lambda: dm.minimum_proof_depth(clauses, query, **(kwargs | {key: cost - 1})),
                               DerivationLimitError, f"enumerate.{key} exhausted before enumeration completed")
        if name in ("H5", "H8", "H12"):
            for mode in ("clauses", "premises", "entities", "predicates", "variables"):
                w, q = transform(clauses, query, mode)
                assert dm.minimum_proof_depth(w, q) == want, (name, mode)
    a = Atom("p", ("a", "b"))
    world = (Clause((), a),)
    cycle = (Clause((Atom("z", ("?x", "?y")),), Atom("z", ("?x", "?y"))),)
    expected_error(lambda: dm.minimum_proof_depth(world + cycle, Atom("missing", ("a", "b"))),
                   LogicValidationError, "dependency.clauses: cyclic predicate dependency")
    expected_error(lambda: dm.minimum_proof_depth(cycle, a, max_derivations=0),
                   LogicValidationError, "depth.max_derivations must be a non-bool positive integer; got int")
    old = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        large = 10**5000
        invalid = [
            ((large, a), {}, "depth.clauses must be a tuple of Clause; got int"),
            (((large,), a), {}, "depth.clauses[0] must be a Clause; got int"),
            ((world, large), {}, "depth.query must be an Atom; got int"),
            ((world, a), {"max_fact_checks": -large}, "depth.max_fact_checks must be a non-bool positive integer; got int"),
            ((world, a), {"max_derivations": -large}, "depth.max_derivations must be a non-bool positive integer; got int"),
        ]
        with patch.object(dm, "enumerate_derivations", side_effect=AssertionError("invalid input reached T0008")) as mock:
            for args, kwargs, message in invalid:
                expected_error(lambda: dm.minimum_proof_depth(*args, **kwargs), LogicValidationError, message)
            assert mock.call_count == 0
        assert dm.minimum_proof_depth(world, a, max_fact_checks=large, max_derivations=large) == 0
    finally:
        sys.set_int_max_str_digits(old)
    for exc in (LogicValidationError("sentinel"), DerivationLimitError("sentinel")):
        with patch.object(dm, "enumerate_derivations", side_effect=exc):
            try:
                dm.minimum_proof_depth(world, a)
            except type(exc) as actual:
                assert actual is exc
            else:
                raise AssertionError("exception swallowed")
    code = '''import importlib, importlib.abc, sys
banned = ("torch", "yaml", "kmesh.logic.engine", "kmesh.logic.reference_engine", "kmesh.logic.proof", "kmesh.logic.proof_enumeration")
def blocked(name):
    return any(name == root or name.startswith(root + ".") for root in banned)
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if blocked(fullname): raise ImportError(fullname)
sys.meta_path.insert(0, Guard())
for root in banned:
    try: importlib.import_module(root)
    except ImportError: pass
    else: raise AssertionError(root)
from kmesh.logic.depth import minimum_proof_depth
from kmesh.logic.types import Atom, Clause
p = Atom("p", ("a", "b")); q = Atom("q", ("b", "c"))
world = (Clause((),p), Clause((),q), Clause((Atom("p",("?x","?y")),),Atom("s",("?x","?y"))), Clause((Atom("s",("?x","?y")),Atom("q",("?y","?z"))),Atom("r",("?x","?z"))))
assert minimum_proof_depth(world,p) == 0
assert minimum_proof_depth(world,Atom("s",("a","b"))) == 1
assert minimum_proof_depth(world,Atom("r",("a","c"))) == 2
assert not any(blocked(name) for name in sys.modules)
print("ISOLATION GUARDS AND CALLS PASS")
'''
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=20)
    (OUT / "isolation.stdout").write_bytes(p.stdout)
    (OUT / "isolation.stderr").write_bytes(p.stderr)
    assert p.returncode == 0, p.stderr
    # Count actual proofs in the submitted F matrix, and execute its README example.
    spec = importlib.util.spec_from_file_location("submitted_depth_tests", ROOT / "tests/test_depth.py")
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    proof_count = 0
    for mask in range(16):
        for query in tests.QUERIES:
            w = tests.world_for_mask(mask)
            proofs = enumerate_proofs(w, query, max_fact_checks=1000, max_derivations=100, max_proof_steps=100000)
            assert all(verify_proof(w, query, proof) for proof in proofs)
            proof_count += len(proofs)
    readme = Path("README.md").read_text().split("单查询最短证明深度（T0010）：", 1)[1]
    exec(compile(readme.split("```python\n", 1)[1].split("```", 1)[0], "README T0010", "exec"), {})
    result = dict(result="PASS", hand_queries=18, transformation_checks=15,
                  giant_integer_paths=6, exception_identity_checks=2,
                  isolation="hard finder + 6 root self-checks + fact/COPY/JOIN calls + prefix scan",
                  frozen_matrix_proof_count=proof_count, readme_example="PASS",
                  conclusion="No product counterexample found; submitted tests lack required guards")
    (OUT / "findings.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
