from kmesh.logic.proof_key import canonical_proof_key
from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep

# K1：一个事实 + 一条 COPY 规则推出第二个事实（两步发生树）
clauses = (
    Clause((), Atom("p", ("a", "b"))),
    Clause((Atom("p", ("?x", "?y")),), Atom("q", ("?x", "?y"))),
)
query = Atom("q", ("a", "b"))
proof = (
    ProofStep(0, (), Atom("p", ("a", "b"))),    # p(a,b)：事实
    ProofStep(1, (0,), Atom("q", ("a", "b"))),  # q(a,b)：由 p(a,b) 推出
)
k = canonical_proof_key(clauses, query, proof)
assert k == (
    "proof_key_v1",
    (
        (("q", "a", "b"),
         ("clause_key_v1", ("q", ("v", 0), ("v", 1)),
          (("p", ("v", 0), ("v", 1)),))),
        (("p", "a", "b"),
         ("clause_key_v1", ("p", ("c", "a"), ("c", "b")), ())),
    ),
)
