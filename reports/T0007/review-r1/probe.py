"""Review-only exhaustive graph oracle and one diagnostic-test mutation."""
import itertools
import json
from pathlib import Path
import re
import types

from kmesh.logic.dependency import relation_topological_order
from kmesh.logic.types import Atom, Clause, LogicValidationError

root = Path.cwd()
names = ("a", "b", "c")
possible_edges = tuple(itertools.product(names, repeat=2))
orders = tuple(itertools.permutations(names))
dag_count = cycle_count = 0
for mask in range(1 << len(possible_edges)):
    edges = tuple(edge for i, edge in enumerate(possible_edges) if mask & (1 << i))
    valid_orders = [p for p in orders if all(p.index(u) < p.index(v) for u, v in edges)]
    world = tuple(Clause((), Atom(p, ("x", "y"))) for p in names) + tuple(
        Clause((Atom(u, ("?x", "?y")),), Atom(v, ("?x", "?y"))) for u, v in edges
    )
    if valid_orders:
        actual = relation_topological_order(world)
        assert type(actual) is tuple and actual == min(valid_orders), (mask, actual)
        dag_count += 1
    else:
        try:
            relation_topological_order(world)
        except LogicValidationError as exc:
            assert "cyclic predicate dependency" in str(exc)
        else:
            raise AssertionError(("cycle accepted", mask))
        cycle_count += 1
assert (dag_count, cycle_count) == (25, 487)
print("PASS: all 512 directed graphs on three named vertices agree with exhaustive permutation oracle (25 DAG, 487 cyclic)")

test_path = root / "tests/test_dependency.py"
submitted = types.ModuleType("_review_t0007_tests")
submitted.__file__ = str(test_path)
exec(compile(test_path.read_text(), str(test_path), "exec"), submitted.__dict__)
submitted.test_generator_outer_not_consumed()
source = (root / "src/kmesh/logic/dependency.py").read_text()
anchor = "    if not isinstance(clauses, tuple):\n"
assert source.count(anchor) == 1
changed = source.replace(anchor,
    "    if type(clauses).__name__ == 'generator':\n"
    "        raise LogicValidationError('dependency.clauses: rejected')\n" + anchor,
    1,
)
mutant = types.ModuleType("_review_t0007_bad_generator_diagnostic")
exec(compile(changed, "<in-memory-mutant>", "exec"), mutant.__dict__)
submitted.relation_topological_order = mutant.relation_topological_order
submitted.test_generator_outer_not_consumed()
print("CONFIRMED: submitted generator test passes even when its error lacks the required reason and type")
generator = (Clause((), Atom("p", ("a", "b"))) for _ in range(1))
try:
    mutant.relation_topological_order(generator)
except LogicValidationError as exc:
    bad_message = str(exc)
    assert "must be a tuple of Clause" not in bad_message
    assert "got generator" not in bad_message
else:
    raise AssertionError("diagnostic mutant failed to reject generator")
assert next(generator) == Clause((), Atom("p", ("a", "b")))
print("PASS: adding the two missing reason/type assertions would detect this mutant without product changes")

readme = (root / "README.md").read_text().split("关系依赖无环检查（T0007", 1)[1]
snippet = re.search(r"```python\n(.*?)```", readme, re.S).group(1)
exec(compile(snippet, "<README T0007 example>", "exec"), {})
print("PASS: submitted README T0007 example executes")
result = {
    "graph_oracle": {"total": 512, "dag": dag_count, "cyclic": cycle_count, "result": "PASS"},
    "submitted_generator_test_accepts_wrong_diagnostic": True,
    "wrong_diagnostic": bad_message,
    "readme_example": "PASS",
    "scope": "Review helper only; no product/test file changes",
}
(root / "reports/T0007/review-r1-probes/findings.json").write_text(json.dumps(result, indent=2) + "\n")
