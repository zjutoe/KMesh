"""Review only: execute bounded probes and in-memory mutants."""
import ast
import json
from pathlib import Path
import sys
import types

from kmesh.logic.proof import ProofLimitError, ProofStep, verify_proof
from kmesh.logic.types import Atom, Clause

ROOT = Path.cwd()
OUT = ROOT / "reports/T0006/review-r2-probes"
test_source = (ROOT / "tests/test_proof.py").read_text()
product_source = (ROOT / "src/kmesh/logic/proof.py").read_text()
module = types.ModuleType("_review_r2_tests")
module.__file__ = str(ROOT / "tests/test_proof.py")
exec(compile(test_source, module.__file__, "exec"), module.__dict__)
results = {}

def mutant(name, old, new):
    assert product_source.count(old) == 1
    changed = product_source.replace(old, new, 1)
    m = types.ModuleType(name)
    sys.modules[name] = m
    exec(compile(changed, "<in-memory-mutant>", "exec"), m.__dict__)
    # Keep the submitted input and exception classes; mutate behavior only.
    m.ProofStep = ProofStep
    m.ProofLimitError = ProofLimitError
    return m.verify_proof

# Both actual guards now block all four roots and every dotted child.
prefix = module._ISO_SNIPPET.split("sys.meta_path.insert")[0]
ns = {}
exec(prefix, ns)
for label, guard in (("module", module._Guard()), ("subprocess", ns["_Guard"]())):
    for root in module._BLOCKED_ROOTS:
        for name in (root, root + ".child"):
            try:
                guard.find_spec(name)
            except ImportError:
                pass
            else:
                raise AssertionError((label, name))
    assert guard.find_spec("kmesh.logic.engineering") is None
results["all_guard_roots_and_children_blocked"] = True
print("PASS: both guards block all four roots and children, without prefix collision")

# Exercise actual fixture restoration with an existing sentinel module.
sentinel_name = "kmesh.logic.engine"
prior = sys.modules.get(sentinel_name)
sentinel = types.ModuleType(sentinel_name)
sys.modules[sentinel_name] = sentinel
meta_before = sys.meta_path
fixture = module._forbid_solver_and_blocked_imports.__wrapped__()
try:
    next(fixture)
    assert sentinel_name not in sys.modules
    assert sys.meta_path is not meta_before
finally:
    try:
        next(fixture)
    except StopIteration:
        pass
assert sys.meta_path is meta_before
assert sys.modules[sentinel_name] is sentinel
if prior is None:
    del sys.modules[sentinel_name]
else:
    sys.modules[sentinel_name] = prior
results["autouse_restoration_passed"] = True

module.TestNoAnswerPeeking().test_alternative_premise_path_is_true()
module.TestNoAnswerPeeking().test_wrong_alternative_path_is_false()
module.TestNoAnswerPeeking().test_guard_probe_lazy_fact_checker_is_insufficient()
module.TestStructuralInvariance().test_renamed_predicates_entities_and_variables_is_true()
priority = module.TestErrorPriority()
for name in dir(priority):
    if name.startswith("test_"):
        getattr(priority, name)()
results["repaired_join_rename_priority_passed"] = True
print("PASS: repaired JOIN, rename and all three priority tests")

# Accepts too-few references and silently truncates via zip. Existing test
# still succeeds because its claimed head is wrong even without that check.
skip_missing = mutant("_review_missing_ref",
    "        if len(step.premise_steps) != len(clause.body):\n",
    "        if len(step.premise_steps) > len(clause.body):\n")
module.verify_proof = skip_missing
module.TestLogicalCounterexamples().test_rule_with_too_few_premise_references_is_false()
results["submitted_missing_reference_test_accepts_wrong_verifier"] = True
print("CONFIRMED: current too-few-reference test passes when missing references are allowed")

p, q, goal = Atom("p", ("a", "b")), Atom("q", ("b", "c")), Atom("r", ("a", "b"))
w = (Clause((), p), Clause((), q),
     Clause((Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))),
            Atom("r", ("?x", "?y"))))
good = (ProofStep(0, (), p), ProofStep(1, (), q), ProofStep(2, (0, 1), goal))
bad = good[:2] + (ProofStep(2, (0,), goal),)
assert verify_proof(w, goal, good) is True
assert verify_proof(w, goal, bad) is False
assert skip_missing(w, goal, bad) is True
results["corrected_count_fixture_discriminates"] = True
print("PASS: complete-good/single-reference-deletion fixture catches the wrong verifier")

# A numeric-conversion bug before range checking is invisible to the
# submitted huge-ref test because its fact/reference arity is already wrong.
stringify_ref = mutant("_review_stringify_ref",
    "            if ref >= i:\n",
    "            str(ref)\n            if ref >= i:\n")
saved = sys.get_int_max_str_digits()
try:
    sys.set_int_max_str_digits(4300)
    module.verify_proof = stringify_ref
    module.TestHugeIntAtDigitLimit4300().test_positive_huge_premise_reference_verifies_false(None)
    results["submitted_huge_ref_test_accepts_stringification_bug"] = True
    large = 10**5000
    copied = Atom("q", ("a", "b"))
    copy_world = (Clause((), p), Clause((Atom("p", ("?x", "?y")),),
                                      Atom("q", ("?x", "?y"))))
    prefix = (ProofStep(0, (), p),)
    assert verify_proof(copy_world, copied, prefix + (ProofStep(1, (0,), copied),)) is True
    large_ref = prefix + (ProofStep(1, (large,), copied),)
    assert verify_proof(copy_world, copied, large_ref) is False
    try:
        stringify_ref(copy_world, copied, large_ref)
    except ValueError:
        results["corrected_huge_ref_fixture_discriminates"] = True
    else:
        raise AssertionError("bad huge-ref verifier unexpectedly survived")
finally:
    sys.set_int_max_str_digits(saved)
    module.verify_proof = verify_proof
print("CONFIRMED: current huge-ref test passes a stringification bug; correct COPY fixture catches it")
print("PASS: original product passes both corrected fixture pairs; product/test files not modified")

# New provenance is also checked, rather than relying on README-only hygiene.
prov = ROOT / "reports/T0006/pi-r2-full/provenance.md"
import re
broken = []
for target in re.findall(r"\]\(([^)]+)\)", prov.read_text()):
    if "://" not in target and not (prov.parent / target).exists():
        broken.append(target)
results["new_provenance_broken_links"] = broken
results["new_provenance_claims_wrong_root"] = "kmesh.utils.environment" in prov.read_text()
print("CONFIRMED: new provenance broken local links:", broken)
(OUT / "findings.json").write_text(json.dumps(results, indent=2) + "\n")
