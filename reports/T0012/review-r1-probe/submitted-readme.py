from kmesh.logic.proof_key import canonical_proof_key
from kmesh.logic.types import Atom, Clause, LogicValidationError
from kmesh.logic.proof import ProofStep

def fact(p, a, b):
    return Clause((), Atom(p, (a, b)))

def A(p, x, y):
    return Atom(p, (x, y))

join = Clause((A("p", "?x", "?y"), A("q", "?y", "?z")), A("r", "?x", "?z"))
c = (fact("p", "a", "b"), fact("q", "b", "c"), join)

# 结构同构但 ref 编号与 leaf 顺序不同：键相等
p1 = (ProofStep(0, (), A("p", "a", "b")), ProofStep(1, (), A("q", "b", "c")),
      ProofStep(2, (0, 1), A("r", "a", "c")))
p2 = (ProofStep(0, (), A("q", "b", "c")), ProofStep(1, (), A("p", "a", "b")),
      ProofStep(2, (1, 0), A("r", "a", "c")))
assert canonical_proof_key(c, A("r", "a", "c"), p1) == \
       canonical_proof_key(c, A("r", "a", "c"), p2)

# 常量改变（真实不同支撑路径）：键不等
d = (fact("p", "a", "b"), fact("q", "b", "d"), join)
assert canonical_proof_key(c, A("r", "a", "c"), p1) != \
       canonical_proof_key(d, A("r", "a", "d"), p2)

# 单发生树守卫：同一子节点被 ref 两次 => LogicValidationError（验证器放行，key 拒绝）
join2 = Clause((A("p", "?x", "?y"), A("p", "?z", "?w")), A("r", "?x", "?w"))
cc = (fact("p", "a", "b"), join2)
bad = (ProofStep(0, (), A("p", "a", "b")),
       ProofStep(1, (0, 0), A("r", "a", "b")))
try:
    canonical_proof_key(cc, A("r", "a", "b"), bad)
    raise AssertionError("expected LogicValidationError")
except LogicValidationError:
    pass
