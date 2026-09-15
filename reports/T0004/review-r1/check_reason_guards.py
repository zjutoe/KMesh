"""Verify submitted diagnostic tests reject messages lacking their reasons.

Uses the actual parametrization data, so changing strings to tuples is
observable. Only a loaded test module's callable is patched, in memory.
Exit 1 means at least one submitted assertion falsely accepted the message.
"""
import importlib.util
from pathlib import Path

from kmesh.logic.types import LogicValidationError

root = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("t0004_reason_tests", root / "tests/test_reference_engine.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

missed = 0
checked = 0
for function_name in (
    "test_invalid_budget_rejected_with_field_and_reason",
    "test_oversized_int_inputs_keep_error_contract",
):
    function = getattr(module, function_name)
    marks = [mark for mark in function.pytestmark if mark.name == "parametrize"]
    assert len(marks) == 1
    names, rows = marks[0].args
    for row in rows:
        values = row.values if hasattr(row, "values") else row
        params = dict(zip(names, values))
        if "bad_budget" in params:
            value = params["bad_budget"]
            selected = (type(value) is int and value in (0, -1)) or type(value) in (float, str)
            if not selected:
                continue
            field = "reference.max_rule_evaluations"
        else:
            field = params["field"]
            params["pinned_int_str_limit"] = None  # Stubbed error needs no int conversion.

        message = f"{field}: invalid type or size"

        def missing_reason(*args, **kwargs):
            raise LogicValidationError(message)

        original = module.reference_closure
        module.reference_closure = missing_reason
        checked += 1
        try:
            function(**params)
        except AssertionError:
            print(f"PASS guard rejects incomplete reason: {function_name}, {field}")
        else:
            missed += 1
            print(f"FAIL guard accepted incomplete reason: {function_name}, {field}")
        finally:
            module.reference_closure = original

assert checked == 7, f"Expected seven targeted rows, got {checked}"
print(f"SUMMARY: {checked - missed}/{checked} diagnostic reason guards effective")
raise SystemExit(1 if missed else 0)
