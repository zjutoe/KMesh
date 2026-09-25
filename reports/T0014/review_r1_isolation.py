"""Codex independent runtime isolation probe in a clean process."""
import importlib
import importlib.abc
import os
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
import kmesh.logic

ROOTS = ('torch', 'yaml', 'kmesh.logic.engine', 'kmesh.logic.reference_engine', 'kmesh.logic.proof_enumeration')


def blocked(name):
    return any(name == r or name.startswith(r + '.') for r in ROOTS)


class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if blocked(fullname):
            raise ImportError('T0014_review_blocked: ' + fullname)
        return None


assert not any(blocked(n) for n in sys.modules)
guard = Blocker()
sys.meta_path.insert(0, guard)
for root in ROOTS:
    try:
        importlib.import_module(root)
    except ImportError as exc:
        assert str(exc) == 'T0014_review_blocked: ' + root
    else:
        raise AssertionError(root)
    package = types.ModuleType(root)
    package.__path__ = []
    assert root not in sys.modules
    sys.modules[root] = package
    try:
        name = root + '._t0014_probe'
        try:
            importlib.import_module(name)
        except ImportError as exc:
            assert str(exc) == 'T0014_review_blocked: ' + name
        else:
            raise AssertionError(name)
    finally:
        del sys.modules[root]

from kmesh.logic import motif
from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep
assert Path(motif.__file__).resolve() == (ROOT / 'src/kmesh/logic/motif.py').resolve()
a = lambda p, x, y: Atom(p, (x, y))
fact = Clause((), a('p', 'a', 'b'))
assert motif.canonical_motif_key((fact,), fact.head, (ProofStep(0, (), fact.head),))[0] == 'proof_motif_v1'
clauses = (fact, Clause((), a('q', 'b', 'c')),
           Clause((a('p', '?x', '?y'), a('q', '?y', '?z')), a('r', '?x', '?z')))
proof = (ProofStep(0, (), clauses[0].head), ProofStep(1, (), clauses[1].head), ProofStep(2, (0, 1), a('r', 'a', 'c')))
assert len(motif.canonical_motif_key(clauses, proof[-1].conclusion, proof)[1]) == 3
assert sys.meta_path[0] is guard
assert not any(blocked(n) for n in sys.modules)
print('PASS: five actual root + submodule ImportError guards; guard stayed active through exact-source import, fact, JOIN and final sys.modules scan')
