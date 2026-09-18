"""Independent T0008 review probes; product and submitted tests stay frozen."""
from collections import Counter
import ast
import hashlib
from itertools import product
import json
from pathlib import Path
import random
import subprocess
import sys

from kmesh.logic.derivations import GroundDerivation, enumerate_derivations
from kmesh.logic.reference_engine import reference_closure
from kmesh.logic.types import Atom, Clause

ROOT = Path.cwd()
OUT = ROOT / "reports/T0008/review-r1-probes"
SOURCE = ROOT / "src/kmesh/logic/derivations.py"
TESTS = ROOT / "tests/test_derivations.py"
source = SOURCE.read_text()
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE, TESTS)}


def atom(pred, x, y):
    return Atom(pred, (x, y))


def all_applications(clauses):
    """Independent binding-domain oracle, using the accepted reference closure."""
    closure = reference_closure(clauses, max_rule_evaluations=1_000_000)
    domain = sorted({v for c in clauses for a in (*c.body, c.head)
                     for v in a.args if not v.startswith("?")})
    expected = []
    for index, clause in enumerate(clauses):
        variables = sorted({v for a in clause.body for v in a.args
                            if v.startswith("?")})
        for values in product(domain, repeat=len(variables)):
            binding = dict(zip(variables, values))

            def ground(a):
                return Atom(a.pred, tuple(binding[v] if v.startswith("?") else v
                                         for v in a.args))

            premises = tuple(ground(a) for a in clause.body)
            if all(a in closure for a in premises):
                expected.append(GroundDerivation(index, premises, ground(clause.head)))
    return closure, Counter(expected)


rng = random.Random(20260918)
predicates = ("z", "A", "m", "b")
constants = ("a", "b", "c")
worlds = []
for _ in range(128):
    clauses = []
    for pred in predicates:
        clauses.extend(Clause((), atom(pred, x, y))
                       for x, y in product(constants, repeat=2)
                       if rng.random() < 0.24)
    for rank in range(1, len(predicates)):
        for _ in range(rng.randrange(1, 5)):
            body = tuple(atom(rng.choice(predicates[:rank]),
                              rng.choice((*constants, "?x", "?y", "?z")),
                              rng.choice((*constants, "?x", "?y", "?z")))
                         for _ in range(rng.choice((1, 2))))
            variables = sorted({v for a in body for v in a.variables})
            choices = (*constants, *variables)
            clauses.append(Clause(body, atom(predicates[rank],
                                            rng.choice(choices), rng.choice(choices))))
    if clauses:
        clauses.append(rng.choice(clauses))
    rng.shuffle(clauses)
    worlds.append(tuple(clauses))

records_checked = 0
for index, clauses in enumerate(worlds):
    closure, expected = all_applications(clauses)
    actual = enumerate_derivations(clauses)
    assert type(actual) is tuple
    assert Counter(actual) == expected, (index, Counter(actual) - expected, expected - Counter(actual))
    assert frozenset(d.conclusion for d in actual) == closure
    records_checked += len(actual)
print(f"PASS: 128 fixed-seed DAG worlds; {records_checked} complete direct records match binding-domain oracle")


def run_child(name, script):
    completed = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                               capture_output=True, text=True, timeout=60)
    (OUT / f"{name}.stdout").write_text(completed.stdout)
    (OUT / f"{name}.stderr").write_text(completed.stderr)
    return completed


mutations = {
    "drop_ground_double": (
        ("if _match(first, outer_candidate, partial) is None:",
         "if not _match(first, outer_candidate, partial):"),
        ("if _match(second, inner_candidate, binding) is not None:",
         "if _match(second, inner_candidate, binding):"),
    ),
    "share_inner_binding": (("binding = dict(partial)", "binding = partial"),),
}
mutation_results = {}
for name, replacements in mutations.items():
    altered = source
    for old, new in replacements:
        assert altered.count(old) == 1
        altered = altered.replace(old, new)
    script = (
        "import kmesh.logic.derivations as module\n"
        f"exec(compile({altered!r}, '<review-mutant>', 'exec'), module.__dict__)\n"
        "import pytest\n"
        f"raise SystemExit(pytest.main(['-q','tests/test_derivations.py','--basetemp',"
        f"{str(OUT / 'pytest-tmp' / name)!r}]))\n"
    )
    completed = run_child(name, script)
    mutation_results[name] = {"exit_code": completed.returncode,
                              "summary": completed.stdout.splitlines()[-1:]}
    assert completed.returncode == 0, (name, completed.stdout, completed.stderr)
    print(f"GAP: {name} incorrect in-memory implementation passes submitted focused suite")

# Read the submitted subprocess script without executing the test module.
tree = ast.parse(TESTS.read_text())
isolation = next(ast.literal_eval(n.value) for n in tree.body
                 if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "ISOLATION_SCRIPT"
                         for t in n.targets))
leak = "import types\nsys.modules['kmesh.logic.engine.review_hidden'] = types.ModuleType('kmesh.logic.engine.review_hidden')\n"
modified = isolation.replace('print("ISOLATION_OK")', leak + 'print("ISOLATION_OK")')
completed = run_child("isolation_hidden_submodule", modified)
assert completed.returncode == 0 and "ISOLATION_OK" in completed.stdout
print("GAP: submitted isolation accepts a forbidden submodule in sys.modules")

# Actual frozen product succeeds on both missing discriminating fixtures.
ground_world = (Clause((), atom("p", "a", "b")), Clause((), atom("q", "c", "d")),
                Clause((atom("p", "a", "b"), atom("q", "c", "d")), atom("r", "e", "f")))
inner_world = (Clause((), atom("p", "a", "b")), Clause((), atom("q", "b", "c")),
               Clause((), atom("q", "b", "d")),
               Clause((atom("p", "?x", "?y"), atom("q", "?y", "?z")), atom("r", "?x", "?z")))
assert len(enumerate_derivations(ground_world, max_fact_checks=2, max_derivations=3)) == 3
assert len(enumerate_derivations(inner_world, max_fact_checks=3, max_derivations=5)) == 5
assert {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE, TESTS)} == before
result = {"product_oracle": "PASS", "seed": 20260918, "worlds": 128,
          "records_checked": records_checked, "mutation_results": mutation_results,
          "isolation_hidden_submodule": "not detected by submitted script",
          "frozen_product_missing_fixtures": "PASS", "product_and_test_sha256_unchanged": before}
(OUT / "findings.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
