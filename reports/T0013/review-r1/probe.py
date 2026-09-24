"""Review missing positive fixtures, complete purity snapshot and README example."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import sys

from kmesh.logic.proof_count import count_canonical_proofs
from kmesh.logic.types import Atom, Clause

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / sys.argv[1]


def a(p, x, y):
    return Atom(p, (x, y))


def f(p, x, y):
    return Clause((), a(p, x, y))


u8 = (f("p", "a", "b"), Clause((a("p", "?x", "?y"),), a("q", "?x", "?y")))
missing = count_canonical_proofs(u8, a("missing", "a", "b"), max_fact_checks=1, max_derivations=2, max_proof_steps=1)
assert type(missing) is int and missing == 0
world = (f("p", "a", "b"), f("p", "a", "d"), f("q", "b", "c"), f("q", "d", "c"),
         Clause((a("p", "?x", "?y"), a("q", "?y", "?z")), a("r", "?x", "?z")))
renamed = (*world[:-1], Clause((a("p", "?u", "?v"), a("q", "?v", "?w")), a("r", "?u", "?w")))
query = a("r", "a", "c")
assert world[:-1] == renamed[:-1] and world[-1] != renamed[-1]
original = (world, query)
before = copy.deepcopy(original)
before_hash = hash(original)
results = []
for clauses, q in (original, ((), a("p", "a", "b")), (renamed, query), original):
    value = count_canonical_proofs(clauses, q, max_fact_checks=6, max_derivations=6, max_proof_steps=10)
    assert type(value) is int
    results.append(value)
assert results == [2, 0, 2, 2]
assert original == before and hash(original) == before_hash
readme = (ROOT / "README.md").read_text().split("规范证明计数（T0013", 1)[1]
example = re.search(r"```python\n(.*?)```", readme, re.S).group(1)
buf = io.StringIO()
with redirect_stdout(buf):
    exec(compile(example, "README.md:T0013", "exec"), {})
assert buf.getvalue() == "1\n"
with (OUT / "probe.json").open("x") as stream:
    stream.write(json.dumps(dict(result="PASS", U8=missing, U7_rename_and_repeat=results,
        input_pair_unchanged=True, readme_stdout=buf.getvalue()), indent=2) + "\n")
print("PASS: real U8=0, local variable rename=2, pair purity, README U3=1")
