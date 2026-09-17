"""Bounded review probes for the two submitted R3 regression fixtures."""
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import types

from kmesh.logic.proof import ProofLimitError, ProofStep, verify_proof


root = Path.cwd()
test_path = root / "tests/test_proof.py"
product_source = (root / "src/kmesh/logic/proof.py").read_text()
submitted = types.ModuleType("_review_r3_submitted_tests")
submitted.__file__ = str(test_path)
exec(compile(test_path.read_text(), str(test_path), "exec"), submitted.__dict__)
limit_context = contextmanager(submitted.int_limit_4300.__wrapped__)
count_test = submitted.TestLogicalCounterexamples().test_rule_with_too_few_premise_references_is_false
reference_test = submitted.TestHugeIntAtDigitLimit4300().test_positive_huge_premise_reference_verifies_false
results = {}


def make_mutant(name, old, new):
    assert product_source.count(old) == 1
    module = types.ModuleType(name)
    sys.modules[name] = module
    try:
        exec(compile(product_source.replace(old, new, 1), "<review-mutant>", "exec"), module.__dict__)
    finally:
        del sys.modules[name]
    module.ProofStep = ProofStep
    module.ProofLimitError = ProofLimitError
    return module.verify_proof


def exercise(label, verifier, call, expected_exception=None):
    trace = []

    def observed(*args, **kwargs):
        try:
            value = verifier(*args, **kwargs)
        except ValueError:
            trace.append("ValueError")
            raise
        trace.append(value)
        return value

    submitted.verify_proof = observed
    try:
        call()
    except (AssertionError, ValueError) as exc:
        if expected_exception is None or type(exc) is not expected_exception:
            raise
        outcome = type(exc).__name__
    else:
        assert expected_exception is None, "wrong verifier survived the submitted test"
        outcome = "PASS"
    finally:
        submitted.verify_proof = verify_proof
    results[label] = {"outcome": outcome, "trace": trace}
    return trace


saved_limit = sys.get_int_max_str_digits()
with limit_context():
    assert sys.get_int_max_str_digits() == 4300
    assert exercise("real_count_fixture", verify_proof, count_test) == [True, False]
    assert exercise("real_huge_reference_fixture", verify_proof, lambda: reference_test(None)) == [True, False]
    missing_reference = make_mutant(
        "_review_r3_missing_ref",
        "        if len(step.premise_steps) != len(clause.body):\n",
        "        if len(step.premise_steps) > len(clause.body):\n",
    )
    assert exercise("count_mutant_rejected", missing_reference, count_test, AssertionError) == [True, True]
    stringify_reference = make_mutant(
        "_review_r3_stringify_ref",
        "            if ref >= i:\n",
        "            str(ref)\n            if ref >= i:\n",
    )
    assert exercise("huge_reference_mutant_rejected", stringify_reference, lambda: reference_test(None), ValueError) == [True, "ValueError"]
assert sys.get_int_max_str_digits() == saved_limit
results["integer_limit_restored"] = True
out = root / "reports/T0006/review-r3-probes/findings.json"
out.write_text(json.dumps(results, indent=2) + "\n")
print("PASS: both submitted fixtures return [True, False] on the frozen product")
print("PASS: submitted count test rejects zip truncation; trace [True, True]")
print("PASS: submitted huge-reference test rejects premature string conversion; trace [True, ValueError]")
print("PASS: submitted 4300 fixture restores the previous limit; no source/test files edited")
