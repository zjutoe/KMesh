"""Codex R1 review probes; no changes to submitted product or test files."""
import ast
import dataclasses
import json
from pathlib import Path
import subprocess
import sys
import types

from kmesh.logic.proof import ProofLimitError, ProofStep, verify_proof
from kmesh.logic.types import Atom, Clause, LogicValidationError

ROOT = Path.cwd()
OUT = ROOT / "reports/T0006/review-r1-probes"
findings = {}
source = (ROOT / "tests/test_proof.py").read_text()
tree = ast.parse(source)
snippet = next(ast.literal_eval(node.value) for node in tree.body
               if isinstance(node, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "_ISO_SNIPPET"
                       for t in node.targets))
ns = {}
exec(snippet.split("sys.meta_path.insert")[0], ns)
guard = ns["_Guard"]()
solver_names = ("kmesh.logic.engine", "kmesh.logic.reference_engine")
assert all(guard.find_spec(n) is None
           for root in solver_names for n in (root, root + ".child"))
assert all(guard.find_spec(n) is not None for n in ("torch", "yaml", "torch.child"))
fixture = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
               and n.name == "_forbid_solver_and_blocked_imports")
guard_node = next(n for n in fixture.body if isinstance(n, ast.ClassDef))
top_ns = {}
exec(compile(ast.Module(body=[guard_node], type_ignores=[]), "<guard>", "exec"), top_ns)
assert all(top_ns["_Guard"]().find_spec(n, None) is None for n in solver_names)
findings["submitted_solver_guards_return_none"] = True
print("CONFIRMED: both submitted guards allow both solver roots and subprocess guard allows their submodules")

# Load submitted test definitions without invoking pytest/autouse fixtures.
test_module = types.ModuleType("_codex_review_submitted_test")
test_module.__file__ = str(ROOT / "tests/test_proof.py")
exec(compile(source, test_module.__file__, "exec"), test_module.__dict__)
wrong = test_module.TestNoAnswerPeeking()
captured = {}
real_verify = test_module.verify_proof

def capture(world, query, proof, **kwargs):
    captured.update(world=world, query=query, proof=proof)
    return real_verify(world, query, proof, **kwargs)

test_module.verify_proof = capture
wrong.test_wrong_alternative_path_is_false()
w, q, p = (captured[k] for k in ("world", "query", "proof"))
assert w[p[1].clause_index].head != p[1].conclusion
assert not w[p[2].clause_index].body
fixed = (p[0], dataclasses.replace(p[1], clause_index=2),
         dataclasses.replace(p[2], clause_index=3))
assert verify_proof(w, q, fixed) is False
valid = (p[0], ProofStep(1, (), w[1].head), ProofStep(3, (0, 1), q))
assert verify_proof(w, q, valid) is True
findings["wrong_path_has_forged_fact_and_fact_as_join"] = True
print("CONFIRMED: submitted alternative-path negative fails before JOIN; correctly indexed good/bad JOIN behave True/False")

# This intentionally faulty verifier recognizes valid prefix facts, then
# disregards all rule evidence. The purported no-answer-peeking test accepts it.
def prefix_only(world, query, proof, **kwargs):
    for step in proof:
        if step.clause_index >= len(world):
            return False
        clause = world[step.clause_index]
        if clause.body:
            break
        if step.premise_steps or clause.head != step.conclusion:
            return False
    return True

test_module.verify_proof = prefix_only
wrong.test_alternative_premise_path_is_true()
wrong.test_wrong_alternative_path_is_false()
findings["submitted_pair_accepts_prefix_only_mutant"] = True
print("CONFIRMED: submitted good/bad pair passes a verifier that ignores all rule evidence")

# Reordering the length/member checks violates A4, but all submitted
# TestStepLimit tests still pass.
def members_before_limit(clauses, query, proof, **kwargs):
    for i, step in enumerate(proof):
        if not isinstance(step, ProofStep):
            raise LogicValidationError(f"verify.proof[{i}] must be a ProofStep")
    return real_verify(clauses, query, proof, **kwargs)

test_module.verify_proof = members_before_limit
budget_tests = test_module.TestStepLimit()
budget_names = [name for name in dir(budget_tests) if name.startswith("test_")]
for name in budget_names:
    getattr(budget_tests, name)()
findings["submitted_budget_tests_accept_wrong_priority"] = budget_names
print("CONFIRMED: all", len(budget_names), "submitted budget tests pass with member checks incorrectly before the limit")

checks = []
def raises(label, cls, field, reason, callback):
    try:
        callback()
    except cls as exc:
        text = str(exc)
        assert field in text and reason in text, (label, text)
        checks.append(label)
    else:
        raise AssertionError(label + ": did not raise expected exception")

a = Atom("p", ("a", "b"))
c = (Clause((), a),)
s = ProofStep(0, (), a)
raises("limit_before_bad_member", ProofLimitError, "verify.max_steps", "exceeds",
       lambda: verify_proof(c, a, (s, object()), max_steps=1))
raises("within_limit_bad_member", LogicValidationError, "verify.proof[1]", "ProofStep",
       lambda: verify_proof(c, a, (s, object()), max_steps=2))
raises("query_validation_before_limit", LogicValidationError, "verify.query", "Atom",
       lambda: verify_proof(c, None, (s, object()), max_steps=1))
raises("clauses_validation_before_limit", LogicValidationError, "verify.clauses[0]", "Clause",
       lambda: verify_proof((object(),), a, (s, object()), max_steps=1))
raises("budget_validation_before_limit", LogicValidationError, "verify.max_steps", "non-bool positive integer",
       lambda: verify_proof(c, a, (s, object()), max_steps=False))
raises("length_before_premise_members", LogicValidationError, "proof_step.premise_steps", "at most 2",
       lambda: ProofStep(0, (None, None, None), a))

saved = sys.get_int_max_str_digits()
try:
    sys.set_int_max_str_digits(4300)
    large = 10**5000
    raises("huge_negative_clause", LogicValidationError, "proof_step.clause_index", "non-bool non-negative integer",
           lambda: ProofStep(-large, (), a))
    raises("huge_negative_premise", LogicValidationError, "proof_step.premise_steps[0]", "non-bool non-negative integer",
           lambda: ProofStep(0, (-large,), a))
    raises("huge_conclusion", LogicValidationError, "proof_step.conclusion", "Atom",
           lambda: ProofStep(0, (), large))
    raises("huge_clause_member", LogicValidationError, "verify.clauses[0]", "Clause",
           lambda: verify_proof((large,), a, (s,)))
    raises("huge_query", LogicValidationError, "verify.query", "Atom",
           lambda: verify_proof(c, large, (s,)))
    raises("huge_proof_member", LogicValidationError, "verify.proof[0]", "ProofStep",
           lambda: verify_proof(c, a, (large,)))
    raises("huge_negative_budget", LogicValidationError, "verify.max_steps", "non-bool positive integer",
           lambda: verify_proof(c, a, (s,), max_steps=-large))
    assert verify_proof(c, a, (ProofStep(large, (), a),)) is False
    rule = Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y")))
    assert verify_proof(c+(rule,), Atom("q", ("a", "b")),
                        (s, ProofStep(1, (large,), Atom("q", ("a", "b"))))) is False
    assert verify_proof(c, a, (s,), max_steps=large) is True
    checks.extend(["huge_positive_clause", "huge_positive_premise", "huge_positive_budget"])
    try:
        sys.set_int_max_str_digits(100)
    except ValueError:
        findings["int_limit_100_invalid_in_actual_python"] = True
    else:
        raise AssertionError("100 unexpectedly accepted")
finally:
    sys.set_int_max_str_digits(saved)
assert sys.get_int_max_str_digits() == saved
findings["product_boundary_checks_passed"] = checks
print("PASS:", len(checks), "independent product boundary cases; conversion limit pinned to 4300 and restored")

isolated = r'''
import importlib.abc
import sys
blocked = ("torch", "yaml", "kmesh.logic.engine", "kmesh.logic.reference_engine")
def forbidden(name):
    return any(name == root or name.startswith(root + ".") for root in blocked)
assert not any(forbidden(name) for name in sys.modules)
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if forbidden(fullname):
            raise ImportError("blocked " + fullname)
guard = Guard()
for root in blocked:
    for name in (root, root + ".child"):
        try:
            guard.find_spec(name)
        except ImportError:
            pass
        else:
            raise AssertionError(name)
sys.meta_path.insert(0, guard)
from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep, verify_proof
a, b = Atom("p", ("a", "b")), Atom("q", ("a", "b"))
w = (Clause((), a), Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))))
assert verify_proof(w, a, (ProofStep(0, (), a),)) is True
assert verify_proof(w, b, (ProofStep(0, (), a), ProofStep(1, (0,), b))) is True
assert not any(forbidden(name) for name in sys.modules)
print("PASS independent import isolation: all four roots and their submodules")
'''
p = subprocess.run([sys.executable, "-c", isolated], capture_output=True, text=True, timeout=30)
(OUT/"isolation.stdout").write_text(p.stdout)
(OUT/"isolation.stderr").write_text(p.stderr)
assert p.returncode == 0, p.stderr
print(p.stdout.strip())
findings["product_independent_isolation_passed"] = True
readme = (ROOT/"README.md").read_text()
start = readme.index("from kmesh.logic.proof import")
stop = readme.index(chr(96)*3, start)
exec(compile(readme[start:stop], "README-proof-example", "exec"), {})
findings["readme_example_passed"] = True
print("PASS README proof example")
(OUT/"findings.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2)+"\n")
