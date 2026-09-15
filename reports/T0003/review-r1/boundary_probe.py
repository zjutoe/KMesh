"""Codex review probes for T0003; synthetic inputs, no product edits."""
import json
import sys

from kmesh.logic.types import Atom, Clause, LogicValidationError


results = []


def check(name, operation):
    try:
        operation()
    except Exception as exc:
        results.append({"name": name, "result": "FAIL", "exception": type(exc).__name__,
                        "message": str(exc)})
    else:
        results.append({"name": name, "result": "PASS"})


def reject(operation, path, reason):
    try:
        operation()
    except LogicValidationError as exc:
        assert path in str(exc) and reason in str(exc), str(exc)
    else:
        raise AssertionError("invalid input accepted")


def positive_structure():
    symbol = "Relation_" + "a" * 512
    item = Atom(symbol, ("?Name_1", "?Name_1"))
    duplicate = Clause((item, item), item)
    assert duplicate.body == (item, item) and len(duplicate.body) == 2
    assert duplicate.head.pred == symbol
    assert len({duplicate, Clause((item, item), item)}) == 1
    assert {duplicate: "value"}[Clause((item, item), item)] == "value"
    renamed = Atom(symbol, ("?Other", "?Other"))
    assert duplicate != Clause((renamed, renamed), renamed)


check("duplicates_long_symbols_clause_hash_alpha_identity", positive_structure)
for bad in ("p\n", " p", "p ", "_p", "关系", "p０", "p\x00"):
    check("pred_lexical_" + repr(bad),
          lambda bad=bad: reject(lambda: Atom(bad, ("a", "b")), "atom.pred", "identifier"))
for bad in ("?x\n", "?_x", "?变量"):
    check("variable_lexical_" + repr(bad),
          lambda bad=bad: reject(lambda: Atom("p", ("a", bad)), "atom.args[1]", "variable"))
check("case_sensitive_scope", lambda: reject(
    lambda: Clause((Atom("p", ("?X", "a")),), Atom("q", ("?x", "a"))),
    "clause.head", "?x"))

# A normal built-in int (about 2 KiB), not a custom object or forged dataclass.
# The rejection path must not fail while formatting the illegal field value.
large = 10 ** 5000
ground = Atom("p", ("a", "b"))
for name, operation, path, reason in (
    ("large_int_pred", lambda: Atom(large, ("a", "b")), "atom.pred", "string"),
    ("large_int_arg", lambda: Atom("p", ("a", large)), "atom.args[1]", "string"),
    ("large_int_args_container", lambda: Atom("p", large), "atom.args", "tuple"),
    ("large_int_body", lambda: Clause(large, ground), "clause.body", "tuple"),
    ("large_int_body_member", lambda: Clause((large,), ground), "clause.body[0]", "Atom"),
    ("large_int_head", lambda: Clause((), large), "clause.head", "Atom"),
):
    check(name, lambda operation=operation, path=path, reason=reason: reject(operation, path, reason))

print(json.dumps({"int_max_str_digits": sys.get_int_max_str_digits(), "results": results},
                 ensure_ascii=False, indent=2))
raise SystemExit(1 if any(row["result"] == "FAIL" for row in results) else 0)
