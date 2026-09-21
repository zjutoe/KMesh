"""Tests for ``kmesh.logic.dependency.relation_topological_order``.

All expectations are hand-computed from the graph definition in the
T0007 handoff: vertices are every head/body predicate; every body atom
adds an edge to the clause head; duplicate edges count once; the order
always picks the lexicographically smallest ready predicate.  No
solver or the function under test generated an expectation.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from kmesh.logic.dependency import relation_topological_order
from kmesh.logic.types import Atom, Clause, LogicValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]

_VALID = Clause((), Atom("p", ("a", "b")))


def _cycle(world):
    with pytest.raises(LogicValidationError) as excinfo:
        relation_topological_order(world)
    message = str(excinfo.value)
    assert "dependency.clauses" in message
    assert "cyclic predicate dependency" in message
    assert message == "dependency.clauses: cyclic predicate dependency"


# ---------------------------------------------------------------------
# Deterministic ordering on the hand-computed table scenarios.
# ---------------------------------------------------------------------

def test_empty_input_returns_empty_tuple():
    assert relation_topological_order(()) == ()


def test_facts_only_with_duplicates():
    world = (
        Clause((), Atom("z", ("a", "b"))),
        Clause((), Atom("p", ("a", "b"))),
        Clause((), Atom("p", ("a", "b"))),
    )
    assert relation_topological_order(world) == ("p", "z")


def test_body_only_nodes_without_facts():
    world = (Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),)
    assert relation_topological_order(world) == ("p", "q")


def test_plan_main_example():
    world = (
        Clause((), Atom("r1", ("a", "b"))),
        Clause((), Atom("r2", ("c", "d"))),
        Clause((Atom("r1", ("?x", "?y")), Atom("r2", ("?y", "?z"))),
               Atom("r3", ("?x", "?z"))),
        Clause((Atom("r3", ("?x", "?y")),), Atom("r4", ("?y", "?x"))),
    )
    assert relation_topological_order(world) == ("r1", "r2", "r3", "r4")


def test_dependency_direction_over_names():
    world = (Clause((Atom("z", ("a", "b")),), Atom("a", ("c", "c"))),)
    assert relation_topological_order(world) == ("z", "a")


def test_newly_ready_node_participates_immediately():
    # FIFO would emit ("a", "z", "b"); heap selection must emit "b".
    world = (
        Clause((), Atom("a", ("a", "b"))),
        Clause((), Atom("z", ("a", "b"))),
        Clause((Atom("a", ("?x", "?y")),), Atom("b", ("?x", "?y"))),
    )
    assert relation_topological_order(world) == ("a", "b", "z")


def test_both_premises_contribute_edges():
    world = (
        Clause((Atom("z", ("?x", "?y")), Atom("p", ("?y", "?z"))),
               Atom("a", ("?x", "?z"))),
    )
    assert relation_topological_order(world) == ("p", "z", "a")


def test_duplicate_predicate_edges_counted_once():
    join = Clause((Atom("p", ("?x", "?y")), Atom("p", ("?y", "?z"))),
                  Atom("q", ("?x", "?z")))
    world = (join, join, Clause((Atom("p", ("?x", "?y")),),
                                Atom("q", ("?x", "?y"))))
    assert relation_topological_order(world) == ("p", "q")


def test_case_preserved_order():
    world = (
        Clause((), Atom("A", ("a", "b"))),
        Clause((), Atom("a", ("a", "b"))),
        Clause((), Atom("z", ("a", "b"))),
    )
    assert relation_topological_order(world) == ("A", "a", "z")


# ---------------------------------------------------------------------
# Cycles: every form must be rejected even when no fact can start it.
# ---------------------------------------------------------------------

def test_self_loop_rejected():
    _cycle((Clause((Atom("p", ("?x", "?y")),), Atom("p", ("?x", "?y"))),))


def test_two_cycle_without_facts():
    _cycle((
        Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
        Clause((Atom("q", ("?x", "?y")),), Atom("p", ("?x", "?y"))),
    ))


def test_three_node_cycle():
    _cycle((
        Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
        Clause((Atom("q", ("?x", "?y")),), Atom("r", ("?x", "?y"))),
        Clause((Atom("r", ("?x", "?y")),), Atom("p", ("?x", "?y"))),
    ))


def test_disconnected_cycle_component_rejected():
    _cycle((
        Clause((Atom("a", ("?x", "?y")),), Atom("b", ("?x", "?y"))),
        Clause((Atom("q", ("?x", "?y")),), Atom("r", ("?x", "?y"))),
        Clause((Atom("r", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
    ))


def test_cycle_with_downstream_node_rejected():
    # "z" is downstream of the cycle, not on it; the message must not
    # claim every leftover node is on the cycle (it names no nodes).
    _cycle((
        Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
        Clause((Atom("q", ("?x", "?y")),), Atom("p", ("?x", "?y"))),
        Clause((Atom("q", ("?x", "?y")),), Atom("z", ("?x", "?y"))),
    ))


def test_second_premise_self_loop_rejected():
    # An implementation that only checked the first premise would
    # wrongly accept this clause.
    _cycle((
        Clause((Atom("p", ("?x", "?y")), Atom("q", ("?x", "?y"))),
               Atom("q", ("?x", "?y"))),
    ))


def test_second_premise_head_change_acyclic():
    world = (
        Clause((Atom("p", ("?x", "?y")), Atom("q", ("?x", "?y"))),
               Atom("r", ("?x", "?y"))),
    )
    assert relation_topological_order(world) == ("p", "q", "r")


def test_ground_rules_cycle_rejected_without_facts():
    # Reachability must not replace the DAG check: these rules can
    # never start a derivation, yet p -> q -> p is cyclic.
    _cycle((
        Clause((Atom("p", ("a", "a")),), Atom("q", ("b", "b"))),
        Clause((Atom("q", ("c", "c")),), Atom("p", ("d", "d"))),
    ))


# ---------------------------------------------------------------------
# Transformations and purity.
# ---------------------------------------------------------------------

def _heap_world():
    return (
        Clause((), Atom("a", ("a", "b"))),
        Clause((), Atom("z", ("a", "b"))),
        Clause((Atom("a", ("?x", "?y")),), Atom("b", ("?x", "?y"))),
    )


def test_clause_reordering_invariant():
    world = _heap_world()
    assert relation_topological_order(world[::-1]) == ("a", "b", "z")


def test_premise_swap_invariant():
    world = (
        Clause((Atom("z", ("?x", "?y")), Atom("p", ("?y", "?z"))),
               Atom("a", ("?x", "?z"))),
    )
    swapped = (
        Clause((Atom("p", ("?y", "?z")), Atom("z", ("?x", "?y"))),
               Atom("a", ("?x", "?z"))),
    )
    assert relation_topological_order(swapped) == ("p", "z", "a")
    assert relation_topological_order(world) == ("p", "z", "a")


def test_duplicate_rules_and_facts_invariant():
    world = _heap_world()
    doubled = (*world, *world)
    assert relation_topological_order(doubled) == ("a", "b", "z")


def test_input_and_order_preserved():
    world = _heap_world()
    relation_topological_order(world)
    assert world == _heap_world()


def test_cycle_failure_does_not_pollinate_subsequent_calls():
    cyclic = (Clause((Atom("p", ("?x", "?y")),), Atom("p", ("?x", "?y"))),)
    _cycle(cyclic)
    assert relation_topological_order(_heap_world()) == ("a", "b", "z")
    _cycle(cyclic)


def test_entity_variable_rename_invariant():
    world = (
        Clause((), Atom("a", ("m", "n"))),
        Clause((), Atom("z", ("m", "n"))),
        Clause((Atom("a", ("?u", "?v")),), Atom("b", ("?u", "?v"))),
    )
    assert relation_topological_order(world) == ("a", "b", "z")


def test_predicate_bijection_rename_new_order():
    # Rename predicate "a" to "m"; hand-computed new order for edges
    # m -> b plus isolated z.  Not a position-wise mapping of the
    # original ("a", "b", "z").
    world = (
        Clause((), Atom("m", ("a", "b"))),
        Clause((), Atom("z", ("a", "b"))),
        Clause((Atom("m", ("?x", "?y")),), Atom("b", ("?x", "?y"))),
    )
    assert relation_topological_order(world) == ("m", "b", "z")


def test_long_chain_1200_nodes():
    # p0000 -> p0001 -> ... -> p1199 (1199 one-premise COPY clauses,
    # no facts): an implementation must cover every vertex iteratively.
    world = tuple(
        Clause((Atom(f"p{i:04d}", ("?x", "?y")),),
               Atom(f"p{i + 1:04d}", ("?x", "?y")))
        for i in range(1199)
    )
    assert relation_topological_order(world) == tuple(
        f"p{i:04d}" for i in range(1200))


# ---------------------------------------------------------------------
# Input boundary: types are checked before any graph work.
# ---------------------------------------------------------------------

@pytest.mark.parametrize("outer", [
    pytest.param([_VALID], id="list"),
    pytest.param({"x": _VALID}, id="dict"),
    pytest.param({_VALID}, id="set"),
    pytest.param(iter([_VALID]), id="iterator"),
    pytest.param(None, id="none"),
    pytest.param(123, id="int"),
])
def test_non_tuple_outer_rejected(outer):
    with pytest.raises(LogicValidationError) as excinfo:
        relation_topological_order(outer)
    message = str(excinfo.value)
    assert "dependency.clauses" in message
    assert "must be a tuple of Clause" in message
    assert type(outer).__name__ in message


def test_generator_outer_not_consumed():
    def gen():
        yield _VALID

    gen_obj = gen()
    with pytest.raises(LogicValidationError) as excinfo:
        relation_topological_order(gen_obj)
    assert "dependency.clauses" in str(excinfo.value)
    assert next(gen_obj) is _VALID


@pytest.mark.parametrize("member, name", [
    pytest.param(Atom("p", ("a", "b")), "Atom", id="atom"),
    pytest.param(None, "NoneType", id="none"),
    pytest.param([_VALID], "list", id="list"),
    pytest.param(True, "bool", id="bool"),
    pytest.param(7, "int", id="int"),
])
def test_non_clause_member_rejected(member, name):
    with pytest.raises(LogicValidationError) as excinfo:
        relation_topological_order((member,))
    message = str(excinfo.value)
    assert "dependency.clauses[0]" in message
    assert "must be a Clause" in message
    assert name in message


def test_member_error_precedes_cycle():
    self_loop = Clause((Atom("p", ("?x", "?y")),), Atom("p", ("?x", "?y")))
    with pytest.raises(LogicValidationError) as excinfo:
        relation_topological_order((self_loop, 42))
    message = str(excinfo.value)
    assert "dependency.clauses[1]" in message
    assert "must be a Clause" in message
    assert "cyclic" not in message


def test_missing_argument_is_type_error():
    with pytest.raises(TypeError):
        relation_topological_order()


def test_extra_keyword_is_type_error():
    with pytest.raises(TypeError):
        relation_topological_order((), bogus=1)


# ---------------------------------------------------------------------
# Huge integer diagnostics: type-name only, no value formatting.
# ---------------------------------------------------------------------

def _huge_int():
    return 10**5000


@pytest.fixture
def int_limit_4300():
    set_limit = getattr(sys, "set_int_max_str_digits", None)
    old = sys.get_int_max_str_digits() if set_limit else None
    if set_limit:
        set_limit(4300)
    try:
        yield
    finally:
        if set_limit and old is not None:
            set_limit(old)


@pytest.mark.parametrize("kind", ["outer", "member"])
def test_huge_int_diagnostic(int_limit_4300, kind):
    value = _huge_int()
    if kind == "outer":
        with pytest.raises(LogicValidationError) as excinfo:
            relation_topological_order(value)
        assert "dependency.clauses" in str(excinfo.value)
        assert "must be a tuple of Clause" in str(excinfo.value)
    else:
        with pytest.raises(LogicValidationError) as excinfo:
            relation_topological_order((value,))
        assert "dependency.clauses[0]" in str(excinfo.value)
        assert "must be a Clause" in str(excinfo.value)
    assert "int" in str(excinfo.value)


# ---------------------------------------------------------------------
# Import isolation in a clean subprocess.
# ---------------------------------------------------------------------

_ISO_SNIPPET = r'''
import importlib
import sys

_BLOCKED_ROOTS = (
    "torch",
    "yaml",
    "kmesh.logic.engine",
    "kmesh.logic.reference_engine",
    "kmesh.logic.proof",
)


def _is_blocked(fullname):
    return any(
        fullname == root or fullname.startswith(root + ".")
        for root in _BLOCKED_ROOTS
    )


class _Guard:
    def find_spec(self, fullname, path=None, target=None):
        if _is_blocked(fullname):
            raise ImportError("blocked import: " + fullname)
        return None


sys.meta_path.insert(0, _Guard())

# The guard must really refuse every blocked root right now.
for root in _BLOCKED_ROOTS:
    try:
        importlib.import_module(root)
    except ImportError:
        pass
    else:
        raise SystemExit(f"guard failed to block {root}")

from kmesh.logic.dependency import relation_topological_order
from kmesh.logic.types import Atom, Clause

assert relation_topological_order(()) == ()
world = (
    Clause((Atom("a", ("?x", "?y")),), Atom("b", ("?x", "?y"))),
    Clause((), Atom("z", ("a", "a"))),
)
assert relation_topological_order(world) == ("a", "b", "z")

# No blocked root or submodule may have loaded.
leaked = [name for name in sys.modules if _is_blocked(name)]
assert not leaked, leaked
print("T0007-ISO-OK")
'''


class TestIsolation:
    def test_dependency_module_isolation_in_clean_subprocess(self):
        result = subprocess.run(
            [sys.executable, "-c", _ISO_SNIPPET],
            capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
        )
        assert result.returncode == 0, result.stderr[-2000:]
        assert "T0007-ISO-OK" in result.stdout

    def test_logic_package_init_has_no_imports(self):
        init_path = REPO_ROOT / "src" / "kmesh" / "logic" / "__init__.py"
        for line in init_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            assert not stripped.startswith("import "), stripped
            assert not stripped.startswith("from "), stripped
