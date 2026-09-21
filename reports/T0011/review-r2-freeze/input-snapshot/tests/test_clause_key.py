"""Tests for the T0011 single-clause content key (canonical_clause_key).

Fixtures are hand-built kmesh.logic.types objects (Atom/Clause) only. Group C
is an independent finite enumeration over all bijections from the clause's
variables to range(k) times all body orderings, encoding directly by the
explicit mapping (no product private helper, no first-occurrence mirror).
Group E runs a clean Python subprocess with PYTHONPATH=src and a blocking
meta-path finder to verify import isolation.
"""

from __future__ import annotations

import itertools
import os
import subprocess
import sys

import pytest

from kmesh.logic.clause_key import canonical_clause_key
from kmesh.logic.types import Atom, Clause, LogicValidationError

ROOT = os.path.abspath(os.path.dirname(__file__))
SRC_DIR = os.path.abspath(os.path.join(ROOT, "..", "src"))


def V(n):
    return ("v", n)


def C(s):
    return ("c", s)


def ak(pred, t0, t1):
    return (pred, t0, t1)


def kfull(head, *body):
    return ("clause_key_v1", head, tuple(body))


def fact_head(pred, a, b):
    return Clause((), Atom(pred, (a, b)))


# Clause fixtures (A–C).
K0 = Clause((), Atom("p", ("a", "b")))
K1 = Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y")))
K2 = Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?y", "?x")))
K3 = Clause((Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))), Atom("r", ("?x", "?z")))
K4 = Clause((Atom("p", ("?x", "?y")), Atom("q", ("?x", "?y"))), Atom("r", ("?x", "?y")))
K5 = Clause((Atom("p", ("?u", "?v")), Atom("q", ("?v", "?w"))), Atom("r", ("a", "b")))
K6 = Clause((Atom("p", ("?x", "x")),), Atom("q", ("?x", "x")))
K7 = Clause((Atom("p", ("a", "b")),), Atom("q", ("b", "a")))
K8 = Clause((Atom("p", ("?z", "?x")), Atom("p", ("?x", "?y"))), Atom("q", ("?x", "?x")))
K9 = Clause((Atom("p", ("?a", "?b")), Atom("q", ("?c", "?d"))), Atom("r", ("a", "b")))
K10 = Clause((Atom("p", ("?x", "?y")), Atom("p", ("?x", "?y"))), Atom("q", ("?x", "?y")))

K1_KEY = kfull(("q", V(0), V(1)), ak("p", V(0), V(1)))
K2_KEY = kfull(("q", V(0), V(1)), ak("p", V(1), V(0)))
K4_KEY = kfull(("r", V(0), V(1)), ak("p", V(0), V(1)), ak("q", V(0), V(1)))
K5_KEY = kfull(("r", C("a"), C("b")), ak("p", V(0), V(1)), ak("q", V(1), V(2)))
K7_KEY = kfull(("q", C("b"), C("a")), ak("p", C("a"), C("b")))
K8_KEY = kfull(("q", V(0), V(0)), ak("p", V(0), V(1)), ak("p", V(2), V(0)))
K9_KEY = kfull(("r", C("a"), C("b")), ak("p", V(0), V(1)), ak("q", V(2), V(3)))
K10_KEY = kfull(("q", V(0), V(1)), ak("p", V(0), V(1)), ak("p", V(0), V(1)))


def _err_msg(t):
    return "clause_key.clause must be a Clause; got " + t


# ---------- helpers for R1/R2 transformations, purity and types ----------

NEW_NAME_POOL = ("?z", "?a", "?m", "?b")
_KS = (K1, K2, K3, K4, K5, K6, K7, K8, K9, K10)

LOOP = Clause((Atom("p", ("?x", "?y")),), Atom("p", ("?x", "?y")))
LOOP_KEY = kfull(ak("p", V(0), V(1)), ak("p", V(0), V(1)))


def _var_names(clause):
    out = set()
    for atom in [clause.head] + list(clause.body):
        for t in atom.args:
            if t.startswith("?"):
                out.add(t)
    return out


def _rename_map(clause, mapping):
    def remap(term):
        return mapping[term] if term in mapping else term

    def remap_atom(a):
        return Atom(a.pred, (remap(a.args[0]), remap(a.args[1])))

    return Clause(tuple(remap_atom(a) for a in clause.body), remap_atom(clause.head))


def _fresh_mapping(clause):
    mapping = {}
    for atom in [clause.head] + list(clause.body):
        for t in atom.args:
            if t.startswith("?") and t not in mapping:
                mapping[t] = "?w" + str(len(mapping))
    return mapping


def _reverse_body(clause):
    return Clause(clause.body[::-1], clause.head)


def _clause_terms(clause):
    out = [(clause.head.pred, clause.head.args[0], clause.head.args[1])]
    for atom in clause.body:
        out.append((atom.pred, atom.args[0], atom.args[1]))
    return tuple(out)


def _structural_copy(clause):
    def copy_atom(a):
        return Atom(a.pred, (a.args[0], a.args[1]))

    body = tuple(copy_atom(a) for a in clause.body)
    head = Atom(clause.head.pred, (clause.head.args[0], clause.head.args[1]))
    return Clause(body, head)


def _check_atom_terms(atom, where):
    assert type(atom) is tuple and len(atom) == 3, where
    assert type(atom[0]) is str and len(atom[0]) > 0, where
    for term in (atom[1], atom[2]):
        assert type(term) is tuple and len(term) == 2, (where, term)
        label, val = term
        assert type(label) is str and label in ("v", "c"), (where, term)
        if label == "c":
            assert type(val) is str, (where, term)
        else:
            assert type(val) is int, (where, term)
            assert val >= 0, (where, term)


def _check_key_types(key):
    assert type(key) is tuple
    assert key[0] == "clause_key_v1" and type(key[0]) is str
    _check_atom_terms(key[1], "head")
    body = key[2]
    assert type(body) is tuple
    for atom in body:
        _check_atom_terms(atom, "body")


# ---------------- Group A: hand-calculated anchors ----------------
def test_A_anchors():
    assert canonical_clause_key(K0) == (
        "clause_key_v1",
        ("p", ("c", "a"), ("c", "b")),
        (),
    )
    assert canonical_clause_key(K3) == (
        "clause_key_v1",
        ("r", ("v", 0), ("v", 1)),
        (("p", ("v", 0), ("v", 2)), ("q", ("v", 2), ("v", 1))),
    )
    assert canonical_clause_key(K6) == (
        "clause_key_v1",
        ("q", ("v", 0), ("c", "x")),
        (("p", ("v", 0), ("c", "x")),),
    )
    for clause, key in [
        (K1, K1_KEY),
        (K2, K2_KEY),
        (K4, K4_KEY),
        (K5, K5_KEY),
        (K7, K7_KEY),
        (K8, K8_KEY),
        (K9, K9_KEY),
        (K10, K10_KEY),
    ]:
        assert canonical_clause_key(clause) == key


def test_A_K8_min_from_reverse():
    # K8's minimum comes from the reversed premise ordering.
    assert canonical_clause_key(K8) == K8_KEY


def test_A_K8a_same_as_K8():
    K8a = Clause(
        (Atom("p", ("?a", "?z")), Atom("p", ("?z", "?b"))),
        Atom("q", ("?z", "?z")),
    )
    assert K8a != K8
    assert canonical_clause_key(K8a) == K8_KEY


# ---------------- Group B: equivalence / inequivalence / purity ----------
def test_B_directions_not_equal():
    assert canonical_clause_key(K1) != canonical_clause_key(K2)


def test_B_premise_size_not_equal():
    assert canonical_clause_key(K1) != canonical_clause_key(K10)


def test_B_shared_vs_separated_bridge():
    separated = Clause(
        (Atom("p", ("?x", "?y")), Atom("q", ("?w", "?z"))),
        Atom("r", ("?x", "?z")),
    )
    assert canonical_clause_key(K3) != canonical_clause_key(separated)


def test_B_variable_vs_same_named_constant():
    constant = Clause((Atom("p", ("x", "?y")),), Atom("q", ("x", "?y")))
    assert canonical_clause_key(K1) != canonical_clause_key(constant)


def test_B_case_insensitive_changes():
    assert canonical_clause_key(fact_head("p", "a", "b")) != canonical_clause_key(
        fact_head("P", "a", "b")
    )
    assert canonical_clause_key(fact_head("p", "a", "b")) != canonical_clause_key(
        fact_head("p", "A", "b")
    )
    assert canonical_clause_key(fact_head("p", "a", "b")) != canonical_clause_key(
        fact_head("p", "b", "a")
    )


def test_B_duplicate_vs_independent_vars():
    dup = Clause((Atom("p", ("?x", "?x")),), Atom("q", ("?x", "?x")))
    assert canonical_clause_key(dup) != canonical_clause_key(K1)


def test_B_pred_and_constant_same_spelling():
    a = fact_head("p", "a", "p")
    b = fact_head("p", "a", "x")
    assert canonical_clause_key(a) != canonical_clause_key(b)


def test_B_symmetric_reverse_equal():
    a = Clause(
        (Atom("p", ("a", "a")), Atom("p", ("b", "b"))),
        Atom("q", ("c", "c")),
    )
    b = Clause(
        (Atom("p", ("b", "b")), Atom("p", ("a", "a"))),
        Atom("q", ("c", "c")),
    )
    assert a != b
    assert canonical_clause_key(a) == canonical_clause_key(b)


def test_B_self_loop_legal():
    loop = Clause((Atom("p", ("?x", "?y")),), Atom("p", ("?x", "?y")))
    key = canonical_clause_key(loop)
    assert key[0] == "clause_key_v1" and len(key[1]) == 3 and len(key[2]) == 1


def test_B_structural_equal_same_key():
    b = Clause(
        (Atom("p", ("?x", "?y")), Atom("q", ("?y", "?z"))),
        Atom("r", ("?x", "?z")),
    )
    assert K3 == b and canonical_clause_key(K3) == canonical_clause_key(b)


def test_B_purity_no_state_leak():
    key = canonical_clause_key(K3)
    assert K3.body == K3.body and isinstance(key, tuple)
    d = {key: "k3"}
    assert d[key] == "k3"
    key2 = canonical_clause_key(K0)
    key3 = canonical_clause_key(K8)
    k3a = canonical_clause_key(K3)
    k3b = canonical_clause_key(K3)
    assert k3a == k3b and key != key3


# ---------------- Group B2 (R1): transformation matrix and bijections ---
@pytest.mark.parametrize("clause", _KS)
def test_R1_alpha_reverse_combination_invariant(clause):
    base = canonical_clause_key(clause)
    renamed = _rename_map(clause, _fresh_mapping(clause))
    rev = _reverse_body(clause)
    both = _reverse_body(renamed)
    if _var_names(clause):
        assert _var_names(renamed) != _var_names(clause), "rename is a no-op"
    assert canonical_clause_key(renamed) == base
    assert canonical_clause_key(rev) == base
    assert canonical_clause_key(both) == base


def test_R1_readme_u_v_example():
    uv = Clause((Atom("p", ("?u", "?v")),), Atom("q", ("?u", "?v")))
    assert uv != K1
    assert _var_names(uv) != _var_names(K1)
    assert canonical_clause_key(uv) == canonical_clause_key(K1)
    assert canonical_clause_key(uv) == K1_KEY


@pytest.mark.parametrize("clause", [K3, K8])
def test_R1_K3_K8_body_and_vars_changed(clause):
    base = canonical_clause_key(clause)
    rev = _reverse_body(clause)
    assert clause.body != rev.body, "body reversal is a no-op"
    assert canonical_clause_key(rev) == base
    renamed = _rename_map(clause, _fresh_mapping(clause))
    assert _var_names(clause) != _var_names(renamed), "rename is a no-op"
    assert canonical_clause_key(renamed) == base
    assert canonical_clause_key(_reverse_body(renamed)) == base


# ---------------- Group B3 (R2): purity and key type structure ----------
def test_R2_purity_snapshot():
    for clause in (K3, K10, K6, K5, LOOP):
        pre_head = clause.head
        pre_body = clause.body
        pre_terms = _clause_terms(clause)
        pre_hash = hash(pre_terms)
        for _ in range(5):
            canonical_clause_key(clause)
        assert clause.head is pre_head
        assert clause.body is pre_body
        assert _clause_terms(clause) == pre_terms
        assert hash(_clause_terms(clause)) == pre_hash
        copy = _structural_copy(clause)
        assert canonical_clause_key(copy) == canonical_clause_key(clause)


def test_R2_key_stable_K3_K0_K8_K3():
    first = canonical_clause_key(K3)
    canonical_clause_key(K0)
    canonical_clause_key(K8)
    assert canonical_clause_key(K3) == first


def test_R2_key_type_structure():
    for clause in (K3, K0, K5, K10, LOOP, K2, K7, K8, K9):
        _check_key_types(canonical_clause_key(clause))


def test_R2_self_loop_full_key():
    assert canonical_clause_key(LOOP) == LOOP_KEY


def test_R2_key_hashable_usable():
    keys = tuple(canonical_clause_key(c) for c in (K1, K3, K5, K8))
    assert len(set(keys)) == len(keys)
    d = {k: 1 for k in keys}
    for k in keys:
        assert d[k] == 1


# ---------------- Group C: independent finite enumeration ---------------
def _term(term, var_map):
    if term.startswith("?"):
        return ("v", var_map[term[1:]])
    return ("c", term)


def _independent_min(clause):
    names = sorted(
        {
            t[1:]
            for atom in [clause.head] + list(clause.body)
            for t in atom.args
            if t.startswith("?")
        }
    )
    orderings = [clause.body]
    if len(clause.body) == 2:
        orderings.append(clause.body[::-1])
    best = None
    for perm in itertools.permutations(range(len(names))):
        var_map = {v: p for v, p in zip(names, perm)}
        head = clause.head
        h = (head.pred, _term(head.args[0], var_map), _term(head.args[1], var_map))
        for order in orderings:
            body_keys = tuple(
                (a.pred, _term(a.args[0], var_map), _term(a.args[1], var_map))
                for a in order
            )
            key = ("clause_key_v1", h, body_keys)
            if best is None or key < best:
                best = key
    return best


@pytest.mark.parametrize("clause", [K1, K2, K3, K5, K8, K9])
def test_C_independent_enumeration(clause):
    assert canonical_clause_key(clause) == _independent_min(clause)


def _rename_clause(clause):
    mapping = {}

    def new_name(v):
        if v not in mapping:
            mapping[v] = "?w" + str(len(mapping))
        return mapping[v]

    def remap(atom):
        args = tuple(new_name(t[1:]) if t.startswith("?") else t for t in atom.args)
        return Atom(atom.pred, args)

    return Clause(tuple(remap(a) for a in clause.body), remap(clause.head))


@pytest.mark.parametrize("clause", [K1, K2, K3, K5, K8, K9])
def test_C_rename_spellings_invariant(clause):
    assert canonical_clause_key(_rename_clause(clause)) == canonical_clause_key(clause)


# ---------------- Group C2 (R1): each bijection to actual names --------
@pytest.mark.parametrize("clause", [K1, K2, K3, K5, K8, K9])
def test_R1_each_bijection_actual_names(clause):
    base = canonical_clause_key(clause)
    orig_vars = sorted(_var_names(clause))
    k = len(orig_vars)
    for perm in itertools.permutations(NEW_NAME_POOL, k):
        mapping = {orig_vars[i]: perm[i] for i in range(k)}
        renamed = _rename_map(clause, mapping)
        assert canonical_clause_key(renamed) == base, mapping


# ---------------- Group D: input boundaries ----------------------------
@pytest.mark.parametrize(
    "obj",
    [None, True, 42, "nope", Atom("p", ("a", "b")), ("a", "b"), ["a"], {"k": "v"}],
)
def test_D_non_clause_diagnostic(obj):
    with pytest.raises(LogicValidationError) as excinfo:
        canonical_clause_key(obj)
    assert str(excinfo.value) == _err_msg(type(obj).__name__)


class _BadRepr:
    def __repr__(self):
        raise ValueError("no")

    def __str__(self):
        raise ValueError("no")


def test_D_generator_not_consumed():
    state = {"consumed": False}

    def gen():
        state["consumed"] = True
        yield "x"

    g = gen()
    with pytest.raises(LogicValidationError) as excinfo:
        canonical_clause_key(g)
    assert str(excinfo.value) == _err_msg("generator")
    assert not state["consumed"]


def test_D_bad_repr_still_diagnoses():
    with pytest.raises(LogicValidationError) as excinfo:
        canonical_clause_key(_BadRepr())
    assert str(excinfo.value) == _err_msg("_BadRepr")


def test_D_huge_int_guard():
    prev = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        with pytest.raises(LogicValidationError) as excinfo:
            canonical_clause_key(10 ** 5000)
        assert str(excinfo.value) == _err_msg("int")
    finally:
        sys.set_int_max_str_digits(prev)


def test_D_signature_type_errors():
    with pytest.raises(TypeError):
        canonical_clause_key()
    with pytest.raises(TypeError):
        canonical_clause_key(K1, K2)
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        canonical_clause_key(clause=K1, extra=1)


# ---------------- Group E: hard import isolation -----------------------
_E_SCRIPT = (
    "import importlib\n"
    "import sys\n"
    "import types\n"
    "BLOCKED = [\n"
    '    "torch", "yaml", "kmesh.logic.engine", "kmesh.logic.reference_engine",\n'
    '    "kmesh.logic.proof", "kmesh.logic.dependency", "kmesh.logic.derivations",\n'
    '    "kmesh.logic.proof_enumeration", "kmesh.logic.depth",\n'
    "]\n"
    "def blocked(name):\n"
    "    if name in BLOCKED:\n"
    "        return True\n"
    "    for root in BLOCKED:\n"
    "        if name.startswith(root + '.'):\n"
    "            return True\n"
    "    return False\n"
    "class BlockFinder:\n"
    "    def find_spec(self, fullname, path=None, target=None):\n"
    "        if blocked(fullname):\n"
    "            raise ImportError('T0011_isolation_blocked: ' + fullname)\n"
    "        return None\n"
    "sys.meta_path.insert(0, BlockFinder())\n"
    "for name in BLOCKED:\n"
    "    try:\n"
    "        importlib.import_module(name)\n"
    "    except ImportError as e:\n"
    "        assert str(e) == 'T0011_isolation_blocked: ' + name, (name, str(e))\n"
    "    else:\n"
    "        raise AssertionError('expected ImportError for ' + name)\n"
    "for root in BLOCKED:\n"
    "    assert root not in sys.modules, 'pre-existing: ' + root\n"
    "    pkg = types.ModuleType(root)\n"
    "    pkg.__path__ = []\n"
    "    pkg.__package__ = ''\n"
    "    sys.modules[root] = pkg\n"
    "    target = root + '._t0011_probe'\n"
    "    assert target not in sys.modules, 'pre-existing sub: ' + target\n"
    "    try:\n"
    "        importlib.import_module(target)\n"
    "    except ImportError as e:\n"
    "        assert str(e) == 'T0011_isolation_blocked: ' + target, (target, str(e))\n"
    "    else:\n"
    "        raise AssertionError('expected ImportError for ' + target)\n"
    "    finally:\n"
    "        if sys.modules.get(root) is pkg:\n"
    "            del sys.modules[root]\n"
    "        if target in sys.modules:\n"
    "            del sys.modules[target]\n"
    "from kmesh.logic.types import Atom, Clause\n"
    "from kmesh.logic.clause_key import canonical_clause_key\n"
    "fact = Clause((), Atom('p', ('a', 'b')))\n"
    "join = Clause((Atom('p', ('?x', '?y')), Atom('q', ('?y', '?z'))), Atom('r', ('?x', '?z')))\n"
    "k8 = Clause((Atom('p', ('?z', '?x')), Atom('p', ('?x', '?y'))), Atom('q', ('?x', '?x')))\n"
    "assert canonical_clause_key(fact) == ('clause_key_v1', ('p', ('c', 'a'), ('c', 'b')), ())\n"
    "assert canonical_clause_key(join) == ('clause_key_v1', ('r', ('v', 0), ('v', 1)), (('p', ('v', 0), ('v', 2)), ('q', ('v', 2), ('v', 1))))\n"
    "assert canonical_clause_key(k8) == ('clause_key_v1', ('q', ('v', 0), ('v', 0)), (('p', ('v', 0), ('v', 1)), ('p', ('v', 2), ('v', 0))))\n"
    "for mod in list(sys.modules):\n"
    "    for root in BLOCKED:\n"
    "        if mod == root or mod.startswith(root + '.'):\n"
    "            raise AssertionError('forbidden in sys.modules: ' + mod)\n"
    "print('ISOLATION_OK')\n"
)


def test_E_hard_import_isolation():
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC_DIR
    proc = subprocess.run(
        [sys.executable, "-c", _E_SCRIPT],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ISOLATION_OK" in proc.stdout
