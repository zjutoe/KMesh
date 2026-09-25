"""Codex independent contract probes, using explicit fixtures, not Pi tests."""
import ast
import copy
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from kmesh.logic import motif
from kmesh.logic.proof import ProofStep, ProofLimitError, verify_proof
from kmesh.logic.types import Atom, Clause, LogicValidationError

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / sys.argv[1]
checks = []


def A(p, x, y):
    return Atom(p, (x, y))


def F(p, x, y):
    return Clause((), A(p, x, y))


def R(body, head):
    return Clause(tuple(A(*a) for a in body), A(*head))


def S(i, refs, p, x, y):
    return ProofStep(i, refs, A(p, x, y))


def key(data, **kwargs):
    assert verify_proof(*data, max_steps=max(1, len(data[2]))) is True
    return motif.canonical_motif_key(*data, **kwargs)


def rename(data, relations=None, entities=None, variables=None):
    relations, entities, variables = relations or {}, entities or {}, variables or {}
    def atom(a):
        return A(relations.get(a.pred, a.pred), *(variables.get(t, t) if t.startswith('?') else entities.get(t, t) for t in a.args))
    c, q, p = data
    return tuple(Clause(tuple(atom(a) for a in r.body), atom(r.head)) for r in c), atom(q), tuple(ProofStep(s.clause_index, s.premise_steps, atom(s.conclusion)) for s in p)


x, y, z = '?x', '?y', '?z'
fact = ((F('p', 'a', 'b'),), A('p', 'a', 'b'), (S(0, (), 'p', 'a', 'b'),))
cp = ((fact[0][0], R((('p', x, y),), ('q', x, y))), A('q', 'a', 'b'), (fact[2][0], S(1, (0,), 'q', 'a', 'b')))
join = ((F('p', 'a', 'b'), F('q', 'b', 'c'), R((('p', x, y), ('q', y, z)), ('r', x, z))),
        A('r', 'a', 'c'), (S(0, (), 'p', 'a', 'b'), S(1, (), 'q', 'b', 'c'), S(2, (0, 1), 'r', 'a', 'c')))
literal_blocks = re.findall(r'```python\n(.*?)```', (ROOT / 'docs/motif_identity_v1.md').read_text(), re.S)
assert len(literal_blocks) == 3
for data, literal in zip((fact, cp, join), literal_blocks):
    assert key(data) == ast.literal_eval(literal)
checks.append('three frozen spec literals exactly match; no claimed spec typo')
collision = rename(fact, entities={'a': 'p', 'b': 'a'})
assert key(collision) == key(fact) == key(rename(fact, relations={'p': 'q'}, entities={'a': 'u', 'b': 'v'}))
checks.append('actual p(p,a) namespace collision')

world6 = (F('f', 'a', 'b'), F('g', 'b', 'c'), F('f', 'a', 'd'), F('g', 'd', 'c'),
          R((('f', x, y), ('g', y, z)), ('p', x, z)), R((('p', x, z), ('p', x, z)), ('r', x, z)))
aa = (world6, A('r', 'a', 'c'), (S(0, (), 'f', 'a', 'b'), S(1, (), 'g', 'b', 'c'), S(4, (0, 1), 'p', 'a', 'c'),
      S(0, (), 'f', 'a', 'b'), S(1, (), 'g', 'b', 'c'), S(4, (3, 4), 'p', 'a', 'c'), S(5, (2, 5), 'r', 'a', 'c')))
ab = (world6, aa[1], aa[2][:3] + (S(2, (), 'f', 'a', 'd'), S(3, (), 'g', 'd', 'c')) + aa[2][5:])
assert key(aa) != key(ab)
ab2 = rename(ab, {'f': 'z', 'g': 'a', 'p': 'm', 'r': 'n'}, {'a': 'W', 'b': 'V', 'c': 'U', 'd': 'T'})
assert ab2 != ab and key(ab2) == key(ab)
checks.append('M6 full shared entities and dense bits after lexical reversal')

world5 = (F('p', 'a', 'a'), F('s', 'a', 'a'), R((('s', x, y),), ('p', x, y)), R((('p', z, x), ('p', x, y)), ('q', x, x)))
m5a = (world5, A('q', 'a', 'a'), (S(0, (), 'p', 'a', 'a'), S(1, (), 's', 'a', 'a'), S(2, (1,), 'p', 'a', 'a'), S(3, (0, 2), 'q', 'a', 'a')))
m5b = (world5, m5a[1], (S(1, (), 's', 'a', 'a'), S(2, (0,), 'p', 'a', 'a'), S(0, (), 'p', 'a', 'a'), S(3, (1, 2), 'q', 'a', 'a')))
assert key(m5a) != key(m5b)
for data in (join, m5a, m5b):
    c, q, p = data
    flipped = (c[:-1] + (Clause(c[-1].body[::-1], c[-1].head),), q,
               p[:-1] + (ProofStep(p[-1].clause_index, p[-1].premise_steps[::-1], p[-1].conclusion),))
    assert flipped[0][-1].body != c[-1].body and flipped[2][-1].premise_steps != p[-1].premise_steps
    assert key(flipped) == key(data)
checks.append('JOIN and both M5 trees true joint flips')

cyclic = ((F('p', 'a', 'b'), R((('p', x, y),), ('q', x, y)), R((('q', x, y),), ('p', x, y))),
          A('p', 'a', 'b'), (S(0, (), 'p', 'a', 'b'), S(1, (0,), 'q', 'a', 'b'), S(2, (1,), 'p', 'a', 'b')))
linear = (cyclic[0][:-1] + (R((('q', x, y),), ('r', x, y)),), A('r', 'a', 'b'), cyclic[2][:-1] + (S(2, (1,), 'r', 'a', 'b'),))
assert key(cyclic) != key(linear)
checks.append('M7 actual p-q-p versus p-q-r')

saved = copy.deepcopy((join, fact, ab))
hashes = tuple(hash(data) for data in (join, fact, ab))
first = key(join)
key(fact)
key(ab)
assert key(join) == first and (join, fact, ab) == saved
assert tuple(hash(data) for data in (join, fact, ab)) == hashes
checks.append('three complete before/after input snapshots and interleaved calls')

real = motif.canonical_proof_key
try:
    for exc in (LogicValidationError('sentinel logic'), ProofLimitError('sentinel limit')):
        calls = []
        def fail(c, q, p, *, max_steps):
            assert c is fact[0] and q is fact[1] and p is fact[2] and max_steps == 7
            calls.append(True)
            raise exc
        motif.canonical_proof_key = fail
        try:
            motif.canonical_motif_key(*fact, max_steps=7, max_orientations=None)
        except (LogicValidationError, ProofLimitError) as got:
            assert got is exc and calls == [True]
        else:
            raise AssertionError('must propagate')
finally:
    motif.canonical_proof_key = real
checks.append('original exception identity and delegate-before-O priority')
consumed = []
def generator():
    consumed.append(True)
    yield fact[2][0]
try:
    motif.canonical_motif_key(fact[0], fact[1], generator())
except LogicValidationError as exc:
    assert str(exc) == 'verify.proof must be a tuple of ProofStep, got generator'
else:
    raise AssertionError('generator accepted')
assert consumed == []
checks.append('true outer generator never consumed')

old_limit = sys.get_int_max_str_digits()
try:
    sys.set_int_max_str_digits(4300)
    assert key(fact, max_orientations=10**5000) == key(fact)
    try:
        key(fact, max_orientations=-(10**5000))
    except LogicValidationError as exc:
        assert str(exc) == 'motif.max_orientations must be a non-bool positive integer; got int'
    else:
        raise AssertionError('negative huge O accepted')
finally:
    sys.set_int_max_str_digits(old_limit)
for data, budget in ((join, 2), (aa, 8), (ab, 8)):
    assert key(data, max_orientations=budget) == key(data)
    try:
        key(data, max_orientations=budget-1)
    except motif.MotifLimitError as exc:
        assert type(exc) is motif.MotifLimitError and str(exc) == 'motif.max_orientations insufficient for complete canonicalization'
    else:
        raise AssertionError('orientation underflow accepted')
checks.append('exact orientation boundaries and pinned giant integer diagnostics')

c = (F('p0', 'a', 'b'),) + tuple(R(((f'p{i-1}', x, y),), (f'p{i}', x, y)) for i in range(1, 1201))
p = (S(0, (), 'p0', 'a', 'b'),) + tuple(S(i, (i-1,), f'p{i}', 'a', 'b') for i in range(1, 1201))
V0, V1, C0, C1 = ('v', 0), ('v', 1), ('c', 0), ('c', 1)
expected = ('proof_motif_v1', tuple(((i, 0, 1), (i, V0, V1), ((i+1, V0, V1),)) for i in range(1200)) + (((1200, 0, 1), (1200, C0, C1), ()),))
actual = key((c, A('p1200', 'a', 'b'), p), max_steps=1201, max_orientations=1)
assert actual == expected and hash(actual) == hash(expected) and not (actual < expected or expected < actual)
checks.append('all 1201 long-chain headers including full body atoms, hash and ordering')

readme = (ROOT / 'README.md').read_text().split('证明结构签名（T0014', 1)[1]
example = re.search(r'```python\n(.*?)```', readme, re.S).group(1)
run = subprocess.run([sys.executable, '-c', example], cwd=ROOT, capture_output=True, text=True, timeout=10)
(OUT / 'readme.stdout.txt').write_text(run.stdout)
(OUT / 'readme.stderr.txt').write_text(run.stderr)
assert run.returncode == 0
checks.append('README COPY runs unchanged')
result = dict(result='PASS', scope='bounded independent contract probes; no claim of exhaustive correctness', checks=checks)
(OUT / 'probe.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
