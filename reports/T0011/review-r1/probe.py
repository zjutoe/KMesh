"""Independent finite oracle; synthetic clauses only, no submitted test helpers."""
import itertools
import json
from pathlib import Path
import random
import sys

from kmesh.logic.clause_key import canonical_clause_key
from kmesh.logic.types import Atom, Clause, LogicValidationError


def oracle(clause):
    names = sorted({t for a in (clause.head, *clause.body) for t in a.args if t.startswith("?")})
    candidates = []
    for numbers in itertools.permutations(range(len(names))):
        mapping = dict(zip(names, numbers))
        def atom_key(atom):
            return (atom.pred, *(('v', mapping[t]) if t in mapping else ('c', t) for t in atom.args))
        for body in itertools.permutations(clause.body):
            candidates.append(('clause_key_v1', atom_key(clause.head), tuple(map(atom_key, body))))
    return min(candidates)


def check(clause):
    before = (clause.head, clause.body, hash(clause))
    result = canonical_clause_key(clause)
    assert result == oracle(clause), clause
    assert type(result) is tuple and type(result[2]) is tuple
    for atom in (result[1], *result[2]):
        assert type(atom) is tuple and len(atom) == 3 and type(atom[0]) is str
        for term in atom[1:]:
            assert type(term) is tuple and len(term) == 2
            assert type(term[0]) is str
            assert (term[0] == 'v' and type(term[1]) is int and term[1] >= 0) or (term[0] == 'c' and type(term[1]) is str)
    assert before == (clause.head, clause.body, hash(clause))
    assert result in {result}
    return result


def main():
    out = Path(sys.argv[1])
    count = transformations = 0
    atoms = [Atom(p, terms) for p in ('p', 'P') for terms in itertools.product(('a', '?x', '?y'), repeat=2)]
    for size in (0, 1, 2):
        for body in itertools.product(atoms, repeat=size):
            allowed = sorted({'a', *(v for a in body for v in a.variables)})
            for args in itertools.product(allowed, repeat=2):
                clause = Clause(body, Atom('r', args))
                check(clause)
                count += 1
    rng = random.Random(20260921)
    for _ in range(600):
        body = tuple(Atom(rng.choice(('p', 'q', 'P')), tuple(rng.choice(('a', 'A', '?x', '?y', '?z', '?u')) for _ in range(2))) for _ in range(rng.randrange(3)))
        allowed = sorted({'a', 'A', *(v for a in body for v in a.variables)})
        clause = Clause(body, Atom(rng.choice(('p', 'r')), tuple(rng.choice(allowed) for _ in range(2))))
        key = check(clause)
        names = sorted({v for a in body for v in a.variables})
        mapping = dict(zip(names, reversed(('?M0', '?B1', '?Z2', '?A3')[:len(names)])))
        def rename(atom):
            return Atom(atom.pred, tuple(mapping.get(t, t) for t in atom.args))
        renamed = Clause(tuple(rename(a) for a in body[::-1]), rename(clause.head))
        assert check(renamed) == key
        count += 2
        transformations += 1
    class BadRepr:
        def __repr__(self):
            raise AssertionError('repr used')
        def __str__(self):
            raise AssertionError('str used')
    def generator():
        raise AssertionError('generator consumed')
        yield
    previous = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        for obj in (None, True, 42, 'x', Atom('p', ('a', 'b')), (), [], {}, generator(), BadRepr(), 10**5000):
            try:
                canonical_clause_key(obj)
            except LogicValidationError as exc:
                assert str(exc) == 'clause_key.clause must be a Clause; got ' + type(obj).__name__
            else:
                raise AssertionError('accepted invalid type')
    finally:
        sys.set_int_max_str_digits(previous)
    result = dict(result='PASS', clauses_checked=count, renamed_and_reversed_pairs=transformations, exact_invalid_diagnostics=11, random_seed=20260921)
    (out / 'probe.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
