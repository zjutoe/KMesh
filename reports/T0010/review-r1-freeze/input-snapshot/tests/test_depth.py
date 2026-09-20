"""T0010 contract tests: minimum proof depth for one ground query.

Group A: hand-calculated depths (facts, chains, shortcuts, joins,
repeated premises, parameter sensitivity, order independence, balance).
Group B: budget boundaries and error propagation (never converted to
None). Group C: input validation order and exact diagnostics. Group D:
T0008 called exactly once with the original inputs, exception
propagation, idempotence and input purity. Group E: long chain and
deep repeated sources. Group F: frozen 16-world x 4-query matrix
cross-checked against T0009 raw proofs plus the T0006 verifier.
Group G: import/source isolation from torch, yaml, and proof modules.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from kmesh.logic import depth as depth_module
from kmesh.logic.depth import minimum_proof_depth
from kmesh.logic.derivations import DerivationLimitError
from kmesh.logic.proof import verify_proof
from kmesh.logic.proof_enumeration import enumerate_proofs
from kmesh.logic.types import Atom, Clause, LogicValidationError

CLE = "enumerate.max_fact_checks exhausted before enumeration completed"
DLE = "enumerate.max_derivations exhausted before enumeration completed"
DCE = "dependency.clauses: cyclic predicate dependency"


def atom(pred: str, x: str = "a", y: str = "b") -> Atom:
    return Atom(pred, (x, y))


def fact(pred: str, x: str = "a", y: str = "b") -> Clause:
    return Clause((), atom(pred, x, y))


def rule(*body: Atom, head: Atom) -> Clause:
    return Clause(tuple(body), head)


def run(clauses, query, c=1000, d=100):
    return minimum_proof_depth(
        clauses, query, max_fact_checks=c, max_derivations=d)


def cyclic_pair():
    return (
        rule(atom("a", "?x", "?y"), head=atom("b", "?x", "?y")),
        rule(atom("b", "?x", "?y"), head=atom("a", "?x", "?y")),
    )


# ---------------------------------------------------------------- Group A

def test_a1_fact_zero_and_absent_none():
    world = (fact("p"),)
    assert run(world, atom("p")) == 0
    assert run(world, atom("p", "b", "a")) is None
    assert run(world, atom("q")) is None

def test_a2_fork_join_chain_depth_3():
    world = (fact("p"), fact("t"),
             rule(atom("p", "?x", "?y"), head=atom("u", "?x", "?y")),
             rule(atom("u", "?x", "?y"), head=atom("v", "?x", "?y")),
             rule(atom("t", "?x", "?y"), head=atom("w", "?x", "?y")),
             rule(atom("v", "?x", "?y"), atom("w", "?x", "?y"),
                  head=atom("z", "?x", "?y")))
    assert run(world, atom("z")) == 3
    assert run(world, atom("v")) == 2
    assert run(world, atom("u")) == 1

def test_a3_later_shortcut_beats_earlier_deep_source():
    late = (fact("p"),
            rule(atom("p", "?x", "?y"), head=atom("m", "?x", "?y")),
            rule(atom("m", "?x", "?y"), head=atom("q", "?x", "?y")),
            rule(atom("p", "?x", "?y"), head=atom("q", "?x", "?y")))
    assert run(late, atom("q")) == 1
    early = (fact("p"),
             rule(atom("p", "?x", "?y"), head=atom("m", "?x", "?y")),
             rule(atom("p", "?x", "?y"), head=atom("q", "?x", "?y")),
             rule(atom("m", "?x", "?y"), head=atom("q", "?x", "?y")))
    assert run(early, atom("q")) == 1

def test_a3b_shortcut_downstream():
    world = (fact("p"),
             rule(atom("p", "?x", "?y"), head=atom("m", "?x", "?y")),
             rule(atom("m", "?x", "?y"), head=atom("q", "?x", "?y")),
             rule(atom("p", "?x", "?y"), head=atom("q", "?x", "?y")),
             rule(atom("q", "?x", "?y"), head=atom("z", "?x", "?y")))
    assert run(world, atom("z")) == 2

def test_a4_fact_source_position_independent():
    rule_first = (fact("p"),
                  rule(atom("p", "?x", "?y"), head=atom("q", "?x", "?y")),
                  fact("q"))
    fact_first = (fact("p"), fact("q"),
                  rule(atom("p", "?x", "?y"), head=atom("q", "?x", "?y")))
    assert run(rule_first, atom("q")) == 0
    assert run(fact_first, atom("q")) == 0

def test_a5_repeated_premise_slot():
    assert run((fact("p"),
                rule(atom("p", "?x", "?y"), atom("p", "?x", "?y"),
                     head=atom("q", "?x", "?y"))),
               atom("q")) == 1

def test_a6_join_direct_and_reversed():
    world = (fact("p"), fact("p", "b", "c"),
             rule(atom("p", "?x", "?y"), atom("p", "?y", "?z"),
                  head=atom("r", "?x", "?z")))
    assert run(world, atom("r", "a", "c")) == 1
    assert run(world, atom("r", "c", "a")) is None

def test_a7_different_ground_parameters():
    world = (fact("q"), fact("p", "c", "d"),
             rule(atom("p", "?x", "?y"), head=atom("q", "?x", "?y")))
    assert run(world, atom("q")) == 0
    assert run(world, atom("q", "c", "d")) == 1

def test_a8_rule_only_no_fact():
    assert run((rule(atom("p", "?x", "?y"), head=atom("q", "?x", "?y")),),
               atom("q")) is None

def test_a9_irrelevant_component_and_absent():
    world = (fact("q"), fact("p"),
             rule(atom("p", "?x", "?y"), head=atom("u", "?x", "?y")),
             rule(atom("u", "?x", "?y"), head=atom("v", "?x", "?y")),
             rule(atom("v", "?x", "?y"), head=atom("z", "?x", "?y")))
    assert run(world, atom("q")) == 0
    assert run(world, atom("missing")) is None

def test_a10_balanced_deep_vs_short():
    world = (fact("a"), fact("b"), fact("c"), fact("d"),
             rule(atom("a", "?x", "?y"), head=atom("m", "?x", "?y")),
             rule(atom("m", "?x", "?y"), head=atom("n", "?x", "?y")),
             rule(atom("n", "?x", "?y"), head=atom("z", "?x", "?y")),
             rule(atom("a", "?x", "?y"), atom("b", "?x", "?y"),
                  head=atom("u", "?x", "?y")),
             rule(atom("c", "?x", "?y"), atom("d", "?x", "?y"),
                  head=atom("v", "?x", "?y")),
             rule(atom("u", "?x", "?y"), atom("v", "?x", "?y"),
                  head=atom("z", "?x", "?y")))
    assert run(world, atom("z")) == 2
    assert run(world, atom("m")) == 1
    assert run(world, atom("n")) == 2

def test_a11_empty_world():
    assert run((), atom("q")) is None
    assert run((), atom("p")) is None

def test_a12_fact_query_with_unrelated_rule():
    world = (fact("q"), fact("p"),
             rule(atom("p", "?x", "?y"), head=atom("u", "?x", "?y")))
    assert run(world, atom("q")) == 0

# ---------------------------------------------------------------- Group B

@pytest.mark.parametrize("bad", [0, -1, True, False, "3", 3.0, None])
def test_b1_budget_validation(bad):
    with pytest.raises(LogicValidationError) as c1:
        run((fact("p"),), atom("p"), c=bad)
    with pytest.raises(LogicValidationError) as c2:
        run((fact("p"),), atom("p"), d=bad)
    assert str(c1.value) == (
        "depth.max_fact_checks must be a non-bool positive integer; "
        f"got {type(bad).__name__}")
    assert str(c2.value) == (
        "depth.max_derivations must be a non-bool positive integer; "
        f"got {type(bad).__name__}")

def test_b1b_default_budgets():
    assert minimum_proof_depth((fact("p"),), atom("p")) == 0
    assert minimum_proof_depth((fact("p"),), atom("missing")) is None

def test_b2_exact_budget_boundaries():
    chain = (fact("p"), fact("t"),
             rule(atom("p", "?x", "?y"), head=atom("u", "?x", "?y")),
             rule(atom("u", "?x", "?y"), head=atom("v", "?x", "?y")),
             rule(atom("t", "?x", "?y"), head=atom("w", "?x", "?y")),
             rule(atom("v", "?x", "?y"), atom("w", "?x", "?y"),
                  head=atom("z", "?x", "?y")))
    assert run(chain, atom("z"), c=5, d=6) == 3
    with pytest.raises(DerivationLimitError) as c1:
        run(chain, atom("z"), c=4, d=6)
    assert str(c1.value) == CLE
    with pytest.raises(DerivationLimitError) as c2:
        run(chain, atom("z"), c=5, d=5)
    assert str(c2.value) == DLE

def test_b2b_shortcut_boundaries():
    shortcut = (fact("p"),
                rule(atom("p", "?x", "?y"), head=atom("m", "?x", "?y")),
                rule(atom("m", "?x", "?y"), head=atom("q", "?x", "?y")),
                rule(atom("p", "?x", "?y"), head=atom("q", "?x", "?y")))
    assert run(shortcut, atom("q"), c=3, d=4) == 1
    with pytest.raises(DerivationLimitError) as c1:
        run(shortcut, atom("q"), c=2, d=4)
    assert str(c1.value) == CLE
    with pytest.raises(DerivationLimitError) as c2:
        run(shortcut, atom("q"), c=3, d=3)
    assert str(c2.value) == DLE

def test_b3_unrelated_component_still_checked():
    world = (fact("q"),) + cyclic_pair()
    with pytest.raises(LogicValidationError) as exc:
        run(world, atom("q"))
    assert str(exc.value) == DCE
    with pytest.raises(LogicValidationError) as exc2:
        run(world, atom("missing"), c=0)
    assert "depth.max_fact_checks" in str(exc2.value)
    with pytest.raises(LogicValidationError) as exc3:
        run((fact("p"),) + cyclic_pair(), atom("p"))
    assert str(exc3.value) == DCE
    with pytest.raises(LogicValidationError) as exc4:
        run(cyclic_pair(), atom("a"))
    assert str(exc4.value) == DCE

def test_b3b_limits_never_none():
    chain = (fact("p"), fact("t"),
             rule(atom("p", "?x", "?y"), head=atom("u", "?x", "?y")),
             rule(atom("u", "?x", "?y"), head=atom("v", "?x", "?y")),
             rule(atom("t", "?x", "?y"), head=atom("w", "?x", "?y")),
             rule(atom("v", "?x", "?y"), atom("w", "?x", "?y"),
                  head=atom("z", "?x", "?y")))
    for c, d in ((4, 6), (5, 5), (0, 100), (100, 0)):
        with pytest.raises((DerivationLimitError, LogicValidationError)):
            run(chain, atom("z"), c=c, d=d)

# ---------------------------------------------------------------- Group C

def test_c1_container_type_and_generator_not_consumed():
    for bad in ([fact("p")], {fact("p")}, "p", 3):
        with pytest.raises(LogicValidationError) as exc:
            run(bad, atom("p"))
        assert str(exc.value) == (
            "depth.clauses must be a tuple of Clause; "
            f"got {type(bad).__name__}")
    gen = (clause for clause in (fact("p"), fact("q")))
    with pytest.raises(LogicValidationError) as exc:
        run(gen, atom("p"))
    assert str(exc.value) == (
        "depth.clauses must be a tuple of Clause; got generator")
    assert next(gen) == fact("p")

def test_c2_first_bad_member_position():
    bad = (fact("p"), "not-a-clause", fact("q"), 0)
    with pytest.raises(LogicValidationError) as exc:
        run(bad, atom("p"))
    assert str(exc.value) == "depth.clauses[1] must be a Clause; got str"
    with pytest.raises(LogicValidationError) as exc2:
        run((fact("p"), fact("q"), None), atom("p"))
    assert str(exc2.value) == (
        "depth.clauses[2] must be a Clause; got NoneType")

def test_c3_query_type_and_groundness():
    for bad in ("p", 1, None, fact("p"), atom("p", "a", "b").args):
        with pytest.raises(LogicValidationError) as exc:
            run((fact("p"),), bad)
        assert str(exc.value) == (
            "depth.query must be an Atom; got "
            f"{type(bad).__name__}")
    with pytest.raises(LogicValidationError) as exc2:
        run((fact("p"),), atom("p", "?x", "?y"))
    assert str(exc2.value) == "depth.query must be a ground Atom"
    with pytest.raises(LogicValidationError) as exc3:
        run((fact("p"),), atom("p", "?x", "a"))
    assert str(exc3.value) == "depth.query must be a ground Atom"

def test_c4_validation_priority():
    bad_clause = "x"
    with pytest.raises(LogicValidationError) as e1:
        run((fact("p"), bad_clause), atom("p", "?x", "?y"), c=0, d=-2)
    assert e1.value.args[0].startswith("depth.clauses[1]")
    with pytest.raises(LogicValidationError) as e2:
        run((fact("p"),), atom("p", "?x", "?y"), c=0, d=-2)
    assert str(e2.value) == "depth.query must be a ground Atom"
    with pytest.raises(LogicValidationError) as e3:
        run((fact("p"),), atom("p"), c=0, d=-2)
    assert str(e3.value) == (
        "depth.max_fact_checks must be a non-bool positive integer; "
        "got int")
    with pytest.raises(LogicValidationError) as e4:
        run((fact("p"),), atom("p"), c=1, d=-2)
    assert str(e4.value) == (
        "depth.max_derivations must be a non-bool positive integer; "
        "got int")

def test_c5_huge_budget_ints_legal():
    giant = 10**30
    assert run((fact("p"),), atom("p"), c=giant, d=giant) == 0
    assert type(run((fact("p"),), atom("p"), c=giant, d=giant)) is int
    assert type(minimum_proof_depth((fact("p"),), atom("p"))) is int

# ---------------------------------------------------------------- Group D

def test_d1_t0008_called_exactly_once_with_original_input(monkeypatch):
    calls = []
    real = depth_module.enumerate_derivations

    def wrapper(clauses, *, max_fact_checks, max_derivations):
        calls.append((clauses, max_fact_checks, max_derivations))
        return real(clauses,
                    max_fact_checks=max_fact_checks,
                    max_derivations=max_derivations)

    monkeypatch.setattr(depth_module, "enumerate_derivations", wrapper)
    fact_world = (fact("q"),)
    absent_world = (fact("p"),)
    chain = (fact("p"),
             rule(atom("p", "?x", "?y"), head=atom("q", "?x", "?y")))
    assert run(fact_world, atom("q"), c=7, d=9) == 0
    assert run(absent_world, atom("nope"), c=4, d=4) is None
    assert run(chain, atom("q"), c=3, d=5) == 1
    assert calls == [
        (fact_world, 7, 9), (absent_world, 4, 4), (chain, 3, 5)]
    assert calls[0][0] is fact_world
    assert calls[1][0] is absent_world

def test_d1b_fact_query_never_skips_enumeration(monkeypatch):
    def explode(clauses, *, max_fact_checks, max_derivations):
        raise AssertionError("T0008 must not be skipped")
    monkeypatch.setattr(depth_module, "enumerate_derivations", explode)
    with pytest.raises(AssertionError):
        run((fact("q"),), atom("q"))

def test_d2_exceptions_propagate_unchanged():
    with pytest.raises(LogicValidationError) as exc:
        run((fact("q"),) + cyclic_pair(), atom("q"))
    assert str(exc.value) == DCE
    chain5 = (fact("p"), fact("t"),
              rule(atom("p", "?x", "?y"), head=atom("u", "?x", "?y")),
              rule(atom("u", "?x", "?y"), head=atom("v", "?x", "?y")),
              rule(atom("t", "?x", "?y"), head=atom("w", "?x", "?y")),
              rule(atom("v", "?x", "?y"), atom("w", "?x", "?y"),
                   head=atom("z", "?x", "?y")))
    with pytest.raises(DerivationLimitError) as exc2:
        run(chain5, atom("z"), c=1000, d=3)
    assert str(exc2.value) == DLE
    with pytest.raises(LogicValidationError) as exc3:
        minimum_proof_depth((fact("p"),), atom("p"), max_fact_checks=True)
    assert "depth.max_fact_checks" in str(exc3.value)

def test_d3_repeated_calls_agree_and_input_pure():
    world = (fact("p"), fact("t"),
             rule(atom("p", "?x", "?y"), head=atom("u", "?x", "?y")),
             rule(atom("u", "?x", "?y"), atom("t", "?x", "?y"),
                  head=atom("z", "?x", "?y")))
    before_hash = hash(world)
    before_copy = tuple(world)
    for query in (atom("z"), atom("u"), atom("nope")):
        a = run(world, query)
        b = run(world, query)
        assert a == b
        if a is not None:
            assert type(a) is int
    assert tuple(world) == before_copy
    assert hash(world) == before_hash

# ---------------------------------------------------------------- Group E

def test_e1_long_chain_1200():
    length = 1200
    clauses = [fact("c0")]
    for i in range(length):
        clauses.append(rule(atom(f"c{i}"), head=atom(f"c{i + 1}")))
    world = tuple(clauses)
    assert minimum_proof_depth(world, atom("c1200")) == 1200
    assert minimum_proof_depth(world, atom("c599")) == 599
    assert minimum_proof_depth(world, atom("d0")) is None

def test_e2_deep_duplicate_sources_16_layers():
    clauses = [fact("l0", "g", "g0")]
    for i in range(16):
        for _ in range(2):
            clauses.append(rule(atom(f"l{i}", "g", f"g{i}"),
                                head=atom(f"l{i + 1}", "g", f"g{i + 1}")))
    world = tuple(clauses)
    assert minimum_proof_depth(world, atom("l16", "g", "g16")) == 16
    assert minimum_proof_depth(world, atom("l8", "g", "g8")) == 8
    assert minimum_proof_depth(world, atom("l0", "g", "g0")) == 0

# ---------------------------------------------------------------- Group F

BASE = (fact("p"), fact("q", "b", "c"),
        rule(atom("p", "?x", "?y"), atom("q", "?y", "?z"),
             head=atom("r", "?x", "?z")))
QUERIES = (atom("r", "a", "c"), atom("r", "a", "b"),
           atom("t", "c", "a"), atom("t", "a", "a"))

def world_for_mask(mask: int) -> tuple[Clause, ...]:
    clauses = list(BASE)
    if mask & 1:
        clauses.append(fact("p"))
    if mask & 2:
        clauses.append(fact("r", "a", "c"))
    if mask & 4:
        clauses.append(rule(atom("p", "?x", "?y"),
                            head=atom("s", "?x", "?y")))
        clauses.append(rule(atom("s", "?x", "?y"),
                            head=atom("r", "?x", "?y")))
    if mask & 8:
        clauses.append(rule(atom("r", "?x", "?y"),
                            head=atom("t", "?y", "?x")))
    return tuple(clauses)

def test_f_frozen_matrix_against_proofs_and_verifier():
    compared = 0
    for mask in range(16):
        world = world_for_mask(mask)
        for query in QUERIES:
            mine = run(world, query, c=1000, d=100)
            proofs = enumerate_proofs(
                world, query,
                max_fact_checks=1000, max_derivations=100,
                max_proof_steps=100_000)
            for proof in proofs:
                assert verify_proof(world, query, proof)
            if proofs:
                heights = []
                for proof in proofs:
                    proof_heights = []
                    for step in proof:
                        proof_heights.append(
                            0 if not step.premise_steps else
                            1 + max(proof_heights[i]
                                    for i in step.premise_steps))
                    heights.append(proof_heights[-1])
                assert mine == min(heights), (mask, query, mine, heights)
            else:
                assert mine is None, (mask, query, mine)
            compared += 1
    assert compared == 64

def test_f_sanity_anchors():
    assert run(world_for_mask(0), atom("r", "a", "c")) == 1
    assert run(world_for_mask(0), atom("t", "c", "a")) is None
    assert run(world_for_mask(2), atom("r", "a", "c")) == 0
    assert run(world_for_mask(0x0C), atom("t", "c", "a")) == 2
    assert run(world_for_mask(0x0C), atom("t", "a", "a")) is None

# ---------------------------------------------------------------- Group G

def test_g_product_source_isolation_text():
    source = Path(depth_module.__file__).read_text(encoding="utf-8")
    low = source.lower()
    assert "torch" not in low
    assert "yaml" not in low
    assert "kmesh.logic.proof" not in source
    assert "proof_enumeration" not in source
    assert "reference_engine" not in source


def test_g_depth_import_pulls_no_forbidden_modules():
    code = (
        "import sys\n"
        "import kmesh.logic.depth\n"
        "banned = ('kmesh.logic.proof', 'kmesh.logic.proof_enumeration',\n"
        "          'kmesh.logic.engine', 'kmesh.logic.reference_engine',\n"
        "          'kmesh.logic.engine_acyclic', 'torch', 'yaml')\n"
        "bad = tuple(name for name in banned if name in sys.modules)\n"
        "assert not bad, bad\n"
        "print('ISOLATION-PASS')\n")
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        capture_output=True, text=True, timeout=120,
        env={"PATH": "/usr/bin:/bin",
             "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
             "PYTHONPATH": "src"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "ISOLATION-PASS" in proc.stdout
