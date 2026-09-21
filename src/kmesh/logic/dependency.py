"""Relation dependency acyclicity check for offline E0 audits.

Checks that the "premise relation -> head relation" dependency among a
tuple of clauses is acyclic, and returns a deterministic topological
order of the relation names when it is.  The order is a deterministic
convention for offline auditing only: it is not a logical depth or
research level, and it must not become a model token, embedding, read
route, or extra feature.  This module does not prove that a world
passed the full E0 audit, does not reason about entities, variables,
unification, or reachability, and is a different graph object from any
model read graph (research plan section 6).
"""

import heapq

from kmesh.logic.types import Clause, LogicValidationError


def relation_topological_order(clauses: tuple[Clause, ...]) -> tuple[str, ...]:
    """Return a deterministic topological order of relation names.

    Vertices are the distinct predicate names occurring in any clause
    head or body atom (facts contribute their head; body-only
    relations are kept).  For every non-empty body, each body atom
    ``u`` contributes a directed edge ``u.pred -> clause.head.pred``.
    Duplicate edges do not raise the target indegree twice; repeated
    facts or clauses are allowed.

    The order picks, at each step, the lexicographically smallest
    predicate among the currently zero-indegree vertices (Python
    string order, case preserved), so identical graphs under clause
    reordering, premise swapping, or duplicated rules yield identical
    output.  The scan is iterative (Kahn with a min-heap) and uses no
    recursion, global state, randomness, file access, or cache.

    Raises ``LogicValidationError`` when ``clauses`` is not a tuple of
    Clauses (checked before any graph work, so a type error on a
    later member always wins over a cycle in an earlier clause) or
    when the dependency graph is cyclic (self-loops included).  On
    failure nothing is returned; no partial order is produced.
    """
    if not isinstance(clauses, tuple):
        raise LogicValidationError(
            "dependency.clauses must be a tuple of Clause; "
            f"got {type(clauses).__name__}")
    for index, clause in enumerate(clauses):
        if not isinstance(clause, Clause):
            raise LogicValidationError(
                f"dependency.clauses[{index}] must be a Clause; "
                f"got {type(clause).__name__}")

    vertices: set[str] = set()
    edges: set[tuple[str, str]] = set()
    for clause in clauses:
        vertices.add(clause.head.pred)
        for body_atom in clause.body:
            vertices.add(body_atom.pred)
            edges.add((body_atom.pred, clause.head.pred))

    indegree: dict[str, int] = {pred: 0 for pred in vertices}
    adjacency: dict[str, set[str]] = {pred: set() for pred in vertices}
    for source, target in edges:
        indegree[target] += 1
        adjacency[source].add(target)

    ready = [pred for pred in vertices if indegree[pred] == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        pred = heapq.heappop(ready)
        order.append(pred)
        for successor in adjacency[pred]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, successor)

    if len(order) != len(vertices):
        raise LogicValidationError(
            "dependency.clauses: cyclic predicate dependency")
    return tuple(order)
