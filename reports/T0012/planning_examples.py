"""Check hand-calculated fixtures against existing verification and a tiny oracle.

This is planning evidence, not the future product and not a Pi test dependency.
The oracle enumerates every local integer assignment and body permutation.
"""
import itertools
import json
from pathlib import Path

from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep, verify_proof
from kmesh.logic.proof_enumeration import enumerate_proofs


def a(pred, x, y):
    return Atom(pred, (x, y))


def fact(pred, x, y):
    return Clause((), a(pred, x, y))


def step(index, refs, pred, x, y):
    return ProofStep(index, refs, a(pred, x, y))


def v(n):
    return ('v', n)


def c(s):
    return ('c', s)


def ck(head, *body):
    return ('clause_key_v1', head, body)


def hf(pred, x, y):
    return ((pred, x, y), ck((pred, c(x), c(y))))


def pk(*headers):
    return ('proof_key_v1', headers)


def oracle(world, proof):
    def variants(index):
        node = proof[index]
        rule = world[node.clause_index]
        names = sorted({t for atom in (rule.head, *rule.body) for t in atom.args if t.startswith('?')})
        keys = set()
        for values in itertools.permutations(range(len(names))):
            mapping = dict(zip(names, values))
            def atom_key(atom):
                return (atom.pred, *(('v', mapping[t]) if t in mapping else ('c', t) for t in atom.args))
            for slots in itertools.permutations(range(len(rule.body))):
                schema = ('clause_key_v1', atom_key(rule.head), tuple(atom_key(rule.body[j]) for j in slots))
                header = ((node.conclusion.pred, *node.conclusion.args), schema)
                pools = [variants(node.premise_steps[j]) for j in slots]
                for children in itertools.product(*pools):
                    keys.add((header,) + tuple(token for child in children for token in child))
        return keys
    return ('proof_key_v1', min(variants(len(proof) - 1)))


def main():
    cases = []
    def add(name, world, proof, expected):
        assert verify_proof(world, proof[-1].conclusion, proof) is True, name
        counts = [0] * len(proof)
        for node in proof:
            for ref in node.premise_steps:
                counts[ref] += 1
        assert counts == [1] * (len(proof) - 1) + [0], name
        actual = oracle(world, proof)
        assert actual == expected, (name, actual, expected)
        assert len(actual[1]) == len(proof)
        cases.append(dict(name=name, steps=len(proof), expected=expected))

    p_ab = step(0, (), 'p', 'a', 'b')
    add('K0_fact', (fact('p', 'a', 'b'),), (p_ab,), pk(hf('p', 'a', 'b')))
    for name, head, ground, body_args in (
        ('K1_copy', ('?x', '?y'), ('a', 'b'), (v(0), v(1))),
        ('K2_inv', ('?y', '?x'), ('b', 'a'), (v(1), v(0))),
    ):
        world = (fact('p', 'a', 'b'), Clause((a('p', '?x', '?y'),), a('q', *head)))
        proof = (p_ab, step(1, (0,), 'q', *ground))
        add(name, world, proof, pk((('q', *ground), ck(('q', v(0), v(1)), ('p', *body_args))), hf('p', 'a', 'b')))
    join = Clause((a('p', '?x', '?y'), a('q', '?y', '?z')), a('r', '?x', '?z'))
    world = (fact('p', 'a', 'b'), fact('q', 'b', 'c'), join)
    proof = (p_ab, step(1, (), 'q', 'b', 'c'), step(2, (0, 1), 'r', 'a', 'c'))
    add('K3_join', world, proof, pk((('r', 'a', 'c'), ck(('r', v(0), v(1)), ('p', v(0), v(2)), ('q', v(2), v(1)))), hf('p', 'a', 'b'), hf('q', 'b', 'c')))
    sym = Clause((a('p', '?x', '?z'), a('p', '?x', '?w')), a('q', '?x', '?x'))
    world = (fact('p', 'a', 'b'), fact('p', 'a', 'c'), sym)
    key = pk((('q', 'a', 'a'), ck(('q', v(0), v(0)), ('p', v(0), v(1)), ('p', v(0), v(2)))), hf('p', 'a', 'b'), hf('p', 'a', 'c'))
    for refs in ((0, 1), (1, 0)):
        add('K4_sym_' + str(refs), world, (p_ab, step(1, (), 'p', 'a', 'c'), step(2, refs, 'q', 'a', 'a')), key)

    base = (fact('p', 'a', 'a'), fact('s', 'a', 'a'), Clause((a('s', '?x', '?y'),), a('p', '?x', '?y')))
    nonsym = Clause((a('p', '?z', '?x'), a('p', '?x', '?y')), a('q', '?x', '?x'))
    duplicate = Clause((a('p', '?x', '?y'), a('p', '?x', '?y')), a('q', '?x', '?y'))
    A = (step(0, (), 'p', 'a', 'a'),)
    B = (step(1, (), 's', 'a', 'a'), step(2, (0,), 'p', 'a', 'a'))
    ha = hf('p', 'a', 'a')
    hs = hf('s', 'a', 'a')
    hb = (('p', 'a', 'a'), ck(('p', v(0), v(1)), ('s', v(0), v(1))))
    summary = []
    for name, rule, expected_count in (('K5', nonsym, 4), ('K6', duplicate, 3)):
        root_key = ck(('q', v(0), v(0)), ('p', v(0), v(1)), ('p', v(2), v(0))) if name == 'K5' else ck(('q', v(0), v(1)), ('p', v(0), v(1)), ('p', v(0), v(1)))
        root = (('q', 'a', 'a'), root_key)
        world = (*base, rule)
        expected_keys = set()
        for left, right in itertools.product(('A', 'B'), repeat=2):
            pieces = {'A': A, 'B': B}
            l, r = pieces[left], pieces[right]
            offset = len(l)
            proof = (*l, *(ProofStep(s.clause_index, tuple(x + offset for x in s.premise_steps), s.conclusion) for s in r), step(3, (len(l)-1, len(l)+len(r)-1), 'q', 'a', 'a'))
            streams = {'A': (ha,), 'B': (hb, hs)}
            order = (right, left) if name == 'K5' else tuple(sorted((left, right)))
            expected = pk(root, *(t for child in order for t in streams[child]))
            add(name + '_' + left + right, world, proof, expected)
            expected_keys.add(expected)
        raw = enumerate_proofs(world, a('q', 'a', 'a'), max_fact_checks=3, max_derivations=4, max_proof_steps=20)
        assert len(raw) == 4
        assert all(verify_proof(world, a('q', 'a', 'a'), proof) for proof in raw)
        actual_keys = {oracle(world, proof) for proof in raw}
        assert actual_keys == expected_keys and len(actual_keys) == expected_count
        summary.append(dict(name=name, raw_trees=4, canonical_keys=expected_count, C=3, D=4, S=20))
    loop = Clause((a('p', '?x', '?y'),), a('p', '?x', '?y'))
    add('K7_finite_cycle', (fact('p', 'a', 'b'), loop), (p_ab, step(1, (0,), 'p', 'a', 'b')),
        pk((('p', 'a', 'b'), ck(('p', v(0), v(1)), ('p', v(0), v(1)))), hf('p', 'a', 'b')))
    out = dict(result='PASS', hand_cases=len(cases), cases=cases, enumerator_crosschecks=summary, product_implemented=False)
    (Path('reports/T0012/planning-examples') / 'examples.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(dict(result='PASS', hand_cases=len(cases), enumerator_crosschecks=summary, product_implemented=False), indent=2))


if __name__ == '__main__':
    main()
