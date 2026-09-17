"""Review only: check the two strengthened generator diagnostic assertions."""
import json
from pathlib import Path
import types

from kmesh.logic.dependency import relation_topological_order

root = Path.cwd()
test_path = root / "tests/test_dependency.py"
submitted = types.ModuleType("_t0007_r2_submitted_tests")
submitted.__file__ = str(test_path)
exec(compile(test_path.read_text(), str(test_path), "exec"), submitted.__dict__)
submitted.test_generator_outer_not_consumed()
source = (root / "src/kmesh/logic/dependency.py").read_text()
anchor = "    if not isinstance(clauses, tuple):\n"
assert source.count(anchor) == 1
results = {"frozen_product": "PASS"}
for label, message in (
    ("missing_reason", "dependency.clauses: got generator"),
    ("missing_type", "dependency.clauses must be a tuple of Clause"),
):
    mutant = types.ModuleType("_t0007_r2_" + label)
    changed = source.replace(
        anchor,
        "    if type(clauses).__name__ == 'generator':\n"
        f"        raise LogicValidationError({message!r})\n" + anchor,
        1,
    )
    exec(compile(changed, "<in-memory-mutant>", "exec"), mutant.__dict__)
    submitted.relation_topological_order = mutant.relation_topological_order
    try:
        submitted.test_generator_outer_not_consumed()
    except AssertionError:
        results[label] = "rejected_by_submitted_test"
    else:
        raise AssertionError(f"incorrect diagnostic survived: {label}")
    finally:
        submitted.relation_topological_order = relation_topological_order
print("PASS: submitted generator test passes on frozen product")
print("PASS: missing-reason and missing-type mutants are each rejected by submitted assertions")
(root / "reports/T0007/review-r2-probes/findings.json").write_text(json.dumps(results, indent=2) + "\n")
