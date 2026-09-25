"""Verify unchanged product at the exact R3 gaps; retain concrete evidence."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
t = runpy.run_path(str(ROOT / 'tests/test_motif.py'))
m = t['motif']
LVE = t['LogicValidationError']
expected_error = 'motif.max_orientations must be a non-bool positive integer; got int'
old = sys.get_int_max_str_digits()
results = {}
try:
    sys.set_int_max_str_digits(4300)
    args = t['fact_proof']('p', 'a', 'b')
    assert m.canonical_motif_key(*args, max_orientations=10**5000) == t['FACT_KEY']
    try:
        m.canonical_motif_key(*args, max_orientations=-10**5000)
    except LVE as exc:
        assert type(exc) is LVE and str(exc) == expected_error
    else:
        raise AssertionError('negative budget accepted')
    results['giant_integer_4300'] = 'PASS'
finally:
    sys.set_int_max_str_digits(old)

orig = m.canonical_proof_key
sentinel = LVE('R3 logic sentinel')
calls = []


def raiser(*a, **kw):
    calls.append((a, kw))
    raise sentinel


try:
    m.canonical_proof_key = raiser
    try:
        m.canonical_motif_key(*args, max_orientations=-1)
    except LVE as exc:
        assert exc is sentinel and len(calls) == 1
    else:
        raise AssertionError('sentinel swallowed')
finally:
    m.canonical_proof_key = orig
results['logic_error_before_invalid_O'] = 'PASS'
for fixture in ('m6_aa', 'm6_ab'):
    args = t[fixture]()
    assert m.canonical_motif_key(*args, max_orientations=8) == m.canonical_motif_key(*args)
    try:
        m.canonical_motif_key(*args, max_orientations=7)
    except m.MotifLimitError as exc:
        assert type(exc) is m.MotifLimitError
        assert str(exc) == 'motif.max_orientations insufficient for complete canonicalization'
    else:
        raise AssertionError('incomplete orientation budget accepted')
    results[fixture + '_8_7'] = 'PASS'

triples = (t['join_proof'](), t['fact_proof']('p', 'a', 'b'), t['m6_aa']())
before = [hash(args) for args in triples]
keys = [m.canonical_motif_key(*args) for args in triples]
assert m.canonical_motif_key(*triples[0]) == keys[0]
assert before == [hash(args) for args in triples]
for key in keys:
    assert type(key) is tuple and type(key[0]) is str and key[0] == 'proof_motif_v1'
    assert type(key[1]) is tuple
    for node in key[1]:
        assert type(node) is tuple and len(node) == 3
        ground, head, body = node
        assert type(ground) is tuple and len(ground) == 3
        assert all(type(i) is int and i >= 0 for i in ground)
        assert type(body) is tuple
        for atom in (head, *body):
            assert type(atom) is tuple and len(atom) == 3
            assert type(atom[0]) is int and atom[0] >= 0
            for term in atom[1:]:
                assert type(term) is tuple and len(term) == 2
                assert type(term[0]) is str and term[0] in ('c', 'v')
                assert type(term[1]) is int and term[1] >= 0
    assert {key: True}[key]
long_key = m.canonical_motif_key(*t['long_chain'](), max_steps=1201, max_orientations=1)
assert sorted((long_key, t['FACT_KEY'])) == [t['FACT_KEY'], long_key]
hash(long_key)
results['raw_types_hashes_dict_and_long_key_comparison'] = 'PASS'
out = ROOT / 'reports/T0014/review-r3-probe/result.json'
out.write_text(json.dumps(dict(checks=results,
    product_sha256=hashlib.sha256((ROOT/'src/kmesh/logic/motif.py').read_bytes()).hexdigest()), indent=2) + '\n')
print(json.dumps(results, indent=2))
