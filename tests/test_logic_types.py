"""Unit tests for kmesh.logic.types (Atom / Clause static validation).

All tests use hand-built objects only: no data files, no solver, no model.
Error messages are asserted by field path and concrete reason, not by
message-equality.
"""

import dataclasses
import subprocess
import sys
import textwrap

import pytest
import sys

from dataclasses import FrozenInstanceError

from kmesh.logic.types import Atom, Clause, LogicValidationError


def make_fact() -> Clause:
    return Clause((), Atom("p", ("a", "b")))


def make_join() -> Clause:
    return Clause((Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))),
                  Atom("r", ("?x", "?z")))


# ---------------------------------------------------------------------------
# 1. Positive examples and structural behaviour
# ---------------------------------------------------------------------------

def test_contract_positive_example_fact():
    clause = make_fact()
    assert clause.body == ()
    assert clause.head == Atom("p", ("a", "b"))
    assert clause.head.is_ground


def test_contract_positive_example_copy():
    clause = Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y")))
    assert clause.body == (Atom("p", ("?x", "?y")),)
    assert clause.head == Atom("q", ("?x", "?y"))


def test_contract_positive_example_invert():
    clause = Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?y", "?x")))
    assert clause.head.args == ("?y", "?x")


def test_contract_positive_example_join():
    clause = make_join()
    assert clause.body == (Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z")))
    assert clause.head == Atom("r", ("?x", "?z"))
    # body-only variable ?y (not in head) is legal here
    body_vars = set().union(*(atom.variables for atom in clause.body))
    assert body_vars == frozenset({"?x", "?y", "?z"})
    assert clause.head.variables == frozenset({"?x", "?z"})


def test_contract_positive_example_intersect():
    clause = Clause((Atom("p", ("?x", "?y")), Atom("q", ("?x", "?y"))),
                    Atom("r", ("?x", "?y")))
    # different predicates over the same shared argument pair
    assert clause.body[0].pred == "p"
    assert clause.body[1].pred == "q"
    assert clause.body[0].args == clause.body[1].args == clause.head.args
    assert clause.head.pred == "r"


def test_repeated_variables_and_constants_are_legal():
    assert Atom("p", ("a", "a")) == Atom("p", ("a", "a"))
    atom = Atom("p", ("?x", "?x"))
    assert atom.variables == frozenset({"?x"})
    assert not atom.is_ground


def test_non_fixed_symbol_names_are_supported():
    atom = Atom("relation_long_name", ("Entity_1", "?join_mid"))
    assert atom.pred == "relation_long_name"
    assert atom.args == ("Entity_1", "?join_mid")
    assert atom.variables == frozenset({"?join_mid"})


def test_case_is_preserved_and_distinct():
    atom = Atom("p", ("A", "Ab_c"))
    assert atom.args == ("A", "Ab_c")
    assert atom != Atom("p", ("a", "ab_c"))
    assert Atom("P", ("a", "b")) != Atom("p", ("a", "b"))


def test_variables_and_is_ground_for_mixed_and_ground_atoms():
    mixed = Atom("r", ("a", "?x"))
    assert mixed.variables == frozenset({"?x"})
    assert not mixed.is_ground
    ground = Atom("r", ("a", "b"))
    assert ground.variables == frozenset()
    assert ground.is_ground


def test_nonempty_rule_with_ground_head_is_legal():
    clause = Clause((Atom("p", ("?x", "?y")),), Atom("r", ("a", "b")))
    assert clause.head.is_ground
    assert len(clause.body) == 1


def test_rule_with_mixed_constant_args_is_legal():
    clause = Clause((Atom("p", ("?x", "a")),), Atom("q", ("?x", "b")))
    assert clause.body[0].variables == frozenset({"?x"})
    assert clause.head == Atom("q", ("?x", "b"))


# ---------------------------------------------------------------------------
# 2. Invalid Atom fields: type, lexical, container, arity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pred,why", [
    (123, "int"),
    (None, "NoneType"),
    (b"p", "bytes"),
    ("", "identifier"),
    ("9lives", "identifier"),
    ("?p", "'?'"),
    ("a b", "identifier"),
    ("a\nb", "identifier"),
    ("f(a)", "identifier"),
])
def test_atom_invalid_pred(pred, why):
    with pytest.raises(LogicValidationError) as ei:
        Atom(pred, ("a", "b"))
    msg = str(ei.value)
    assert "atom.pred" in msg
    assert why in msg


@pytest.mark.parametrize("args,why", [
    (["a", "b"], "tuple"),
    ("ab", "tuple"),
    (None, "tuple"),
    (("a",), "2"),
    (("a", "b", "c"), "2"),
    ((), "2"),
])
def test_atom_invalid_args_container(args, why):
    with pytest.raises(LogicValidationError) as ei:
        Atom("p", args)
    msg = str(ei.value)
    assert "atom.args" in msg
    assert why in msg


@pytest.mark.parametrize("args,index,why", [
    ((1, "b"), 0, "str"),
    ((True, "b"), 0, "str"),
    ((None, "b"), 0, "str"),
    (("a", 9), 1, "str"),
    (("a", ""), 1, "identifier"),
    (("a", "?"), 1, "variable"),
    (("a", "a b"), 1, "identifier"),
    (("a", "a\nb"), 1, "identifier"),
    (("a", "f(b)"), 1, "identifier"),
    (("a", "1x"), 1, "identifier"),
    (("a", "?9x"), 1, "variable"),
    (("a", "??x"), 1, "variable"),
])
def test_atom_invalid_arg_item(args, index, why):
    with pytest.raises(LogicValidationError) as ei:
        Atom("p", args)
    msg = str(ei.value)
    assert f"atom.args[{index}]" in msg
    # "str" also appears in type-name messages; keyword check is on the reason
    assert why in msg


def test_atom_constructor_mistakes_are_plain_type_errors():
    # missing required argument / unknown keyword -> ordinary TypeError,
    # NOT wrapped into LogicValidationError
    with pytest.raises(TypeError):
        Atom("p")
    with pytest.raises(TypeError):
        Atom("p", ("a", "b"), "extra")
    with pytest.raises(TypeError):
        Atom(pred="p", args=("a", "b"), surprise=1)


# ---------------------------------------------------------------------------
# 3. Invalid Clause fields: container, arity, members, head, range rule
# ---------------------------------------------------------------------------

def test_clause_body_must_be_tuple_not_list():
    with pytest.raises(LogicValidationError) as ei:
        Clause([Atom("p", ("a", "b"))], Atom("r", ("a", "b")))
    msg = str(ei.value)
    assert "clause.body" in msg
    assert "list" in msg


def test_clause_body_must_be_tuple_not_none():
    with pytest.raises(LogicValidationError) as ei:
        Clause(None, Atom("r", ("a", "b")))
    msg = str(ei.value)
    assert "clause.body" in msg
    assert "NoneType" in msg


def test_clause_body_rejects_three_premises():
    with pytest.raises(LogicValidationError) as ei:
        Clause((Atom("p", ("a", "b")), Atom("q", ("a", "b")),
                Atom("r", ("a", "b"))), Atom("s", ("a", "b")))
    msg = str(ei.value)
    assert "clause.body" in msg
    assert "0, 1, or 2" in msg


@pytest.mark.parametrize("bad_member,index", [
    ({"pred": "q", "args": ("a", "b")}, 0),
    ("not-an-atom", 0),
    (("q", ("a", "b")), 1),
])
def test_clause_body_member_must_be_atom(bad_member, index):
    first = Atom("p", ("a", "b"))
    body = (bad_member, first) if index == 0 else (first, bad_member)
    with pytest.raises(LogicValidationError) as ei:
        Clause(body, Atom("r", ("a", "b")))
    msg = str(ei.value)
    assert f"clause.body[{index}]" in msg
    assert "Atom" in msg


@pytest.mark.parametrize("bad_head", [
    {"pred": "r", "args": ("a", "b")},
    "r(a,b)",
    None,
])
def test_clause_head_must_be_atom(bad_head):
    with pytest.raises(LogicValidationError) as ei:
        Clause((), bad_head)
    msg = str(ei.value)
    assert "clause.head" in msg
    assert "Atom" in msg


def test_fact_with_head_variable_is_rejected():
    with pytest.raises(LogicValidationError) as ei:
        Clause((), Atom("p", ("?x", "a")))
    msg = str(ei.value)
    assert "clause.head" in msg
    assert "'?x'" in msg


def test_head_variable_missing_from_body_is_rejected_by_name():
    with pytest.raises(LogicValidationError) as ei:
        Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?z")))
    msg = str(ei.value)
    assert "clause.head" in msg
    assert "'?z'" in msg


def test_multiple_unbound_head_variables_are_all_reported():
    with pytest.raises(LogicValidationError) as ei:
        Clause((), Atom("p", ("?x", "?y")))
    msg = str(ei.value)
    assert "clause.head" in msg
    assert "'?x'" in msg and "'?y'" in msg


# ---------------------------------------------------------------------------
# 4. Immutability, hashability, structural equality
# ---------------------------------------------------------------------------

def test_atom_assignment_raises_frozen_instance_error():
    atom = Atom("p", ("a", "b"))
    with pytest.raises(FrozenInstanceError):
        atom.pred = "q"
    with pytest.raises(FrozenInstanceError):
        atom.args = ("c", "d")


def test_clause_assignment_raises_frozen_instance_error():
    clause = make_fact()
    with pytest.raises(FrozenInstanceError):
        clause.head = Atom("r", ("a", "b"))
    with pytest.raises(FrozenInstanceError):
        clause.body = (Atom("p", ("a", "b")),)


def test_internal_containers_are_tuples_and_frozensets():
    atom = Atom("p", ("a", "?x"))
    clause = make_join()
    assert type(atom.args) is tuple
    assert type(clause.body) is tuple
    assert type(atom.variables) is frozenset
    # frozen containers cannot be mutated directly either
    with pytest.raises(TypeError):
        atom.args[0] = "z"
    with pytest.raises(AttributeError):
        atom.variables.pop()


def test_equal_structures_are_equal_and_hash_equal():
    atom_a = Atom("p", ("a", "b"))
    atom_b = Atom("p", ("a", "b"))
    assert atom_a == atom_b
    assert hash(atom_a) == hash(atom_b)
    clause_a = make_join()
    clause_b = Clause((Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))),
                      Atom("r", ("?x", "?z")))
    assert clause_a == clause_b
    assert hash(clause_a) == hash(clause_b)


def test_objects_deduplicate_in_sets_and_dicts():
    items = {Atom("p", ("a", "b")), Atom("p", ("a", "b"))}
    assert len(items) == 1
    key_a, key_b = Atom("p", ("a", "b")), Atom("p", ("a", "b"))
    table = {key_a: 1}
    assert table[key_b] == 1


def test_argument_direction_is_part_of_identity():
    assert Atom("p", ("a", "b")) != Atom("p", ("b", "a"))
    join = make_join()
    swapped = Clause((Atom("q", ("?y", "?z")), Atom("p", ("?x", "?y"))),
                     join.head)
    # same head, same multiset of premises, different order -> not equal
    assert swapped != join
    assert join.body == (Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z")))
    # NOTE: deliberately no claim that unequal objects have different hashes.


# ---------------------------------------------------------------------------
# 5. Cross-clause variable isolation and absence of metadata fields
# ---------------------------------------------------------------------------

def test_no_variable_binding_state_leaks_between_clauses():
    # a clause that legitimately uses ?z in its body ...
    used = make_join()
    assert "?z" in used.body[1].variables
    # ... must not bind ?z for a different clause with an unbound head ?z
    with pytest.raises(LogicValidationError) as ei:
        Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?z")))
    assert "'?z'" in str(ei.value)
    # and a fact stays a fact afterwards
    assert make_fact().head.is_ground


def test_no_metadata_fields_exist_on_content_types():
    assert {field.name for field in dataclasses.fields(Atom)} == {"pred", "args"}
    assert {field.name for field in dataclasses.fields(Clause)} == {"body", "head"}


# ---------------------------------------------------------------------------
# 7. R1 regression: oversized integers keep the LogicValidationError contract
#
# Python 3.11+ refuses str()/repr() of ints longer than the 4300-digit limit
# with a plain ValueError.  Error reporting for rejected inputs must not
# itself raise: these paths must report the field path and expected/actual
# type or length without representing the offending value.  Parameters are
# factories with explicit short ids so pytest never has to format the large
# integer when building test ids.
# ---------------------------------------------------------------------------


@pytest.fixture()
def pinned_int_str_limit():
    previous = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    try:
        yield
    finally:
        sys.set_int_max_str_digits(previous)


def _r1_ground():
    return Atom("p", ("a", "b"))


@pytest.mark.parametrize(
    "build, field, expect",  # expect: fragments that must appear in the message
    [
        (lambda: Atom(10**5000, ("a", "b")),
         "atom.pred", ("string",)),
        (lambda: Atom("p", ("a", 10**5000)),
         "atom.args[1]", ("string",)),
        (lambda: Atom("p", 10**5000),
         "atom.args", ("tuple",)),
        (lambda: Atom("p", [10**5000, "b"]),
         "atom.args", ("tuple",)),
        (lambda: Atom("p", (10**5000,)),
         "atom.args", ("2",)),
        (lambda: Clause(10**5000, _r1_ground()),
         "clause.body", ("tuple",)),
        (lambda: Clause((10**5000,), _r1_ground()),
         "clause.body[0]", ("Atom",)),
        (lambda: Clause((), 10**5000),
         "clause.head", ("Atom",)),
    ],
    ids=[
        "pred-oversized-int",
        "args1-oversized-int",
        "args-oversized-int",
        "args-list-with-oversized-int",
        "args-one-item-oversized-int",
        "body-oversized-int",
        "body0-oversized-int",
        "head-oversized-int",
    ],
)
def test_oversized_int_inputs_keep_error_contract(
    pinned_int_str_limit, build, field, expect
):
    # The dedicated exception with the field path must be raised; a native
    # ValueError from int-to-str conversion would escape instead.
    with pytest.raises(LogicValidationError) as ei:
        build()
    message = str(ei.value)
    assert field in message
    for expected in expect:
        assert expected in message


# ---------------------------------------------------------------------------
# 8. Import isolation: new subprocess blocks torch and yaml
# ---------------------------------------------------------------------------

def test_import_isolation_blocks_torch_and_yaml():
    code = textwrap.dedent("""
        import sys

        class _BlocklistFinder:
            BLOCKED = ("torch", "yaml")

            def find_spec(self, fullname, path=None, target=None):
                root = fullname.split(".")[0]
                if root in self.BLOCKED:
                    raise ImportError(
                        f"import of {fullname!r} is blocked in this test")
                return None

        sys.meta_path.insert(0, _BlocklistFinder())
        from kmesh.logic.types import Atom, Clause

        fact = Clause((), Atom("p", ("a", "b")))
        join = Clause((Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))),
                      Atom("r", ("?x", "?z")))
        assert fact.head.pred == "p"
        assert fact.head.is_ground
        assert join.body[1].variables == frozenset({"?y", "?z"})
        leaked = [name for name in list(_BlocklistFinder.BLOCKED)
                  if name in sys.modules]
        assert not leaked, f"blocked modules leaked into sys.modules: {leaked}"
        print("ISOLATION-OK")
    """)
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert "ISOLATION-OK" in proc.stdout
