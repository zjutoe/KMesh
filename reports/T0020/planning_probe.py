"""Codex planning analysis of the accepted T0019 report, not a product oracle."""
import collections
import hashlib
import json
from pathlib import Path
import sys


source = Path(sys.argv[1])
report = json.loads(source.read_text())
groups = {
    "train": ("CJ", "CT", "IC", "II", "JC", "JI", "TJ", "TT"),
    "dev_composition": ("CC", "IJ", "JT", "TI"),
    "test_composition": ("CI", "IT", "JJ", "TC"),
}
rows = report["candidates"]
by_id = {row["id"]: row for row in rows}
assert len(rows) == len(by_id) == 80
owner = {row["id"]: split for split, roots in groups.items()
         for row in rows if row["id"][:2] in roots}
assert set(owner) == set(by_id)
graph = {key: set() for key in by_id}
matrix = {a: {b: 0 for b in groups} for a in groups}
for row in rows:
    for child in row["contained_ids"]:
        graph[row["id"]].add(child)
        graph[child].add(row["id"])
        matrix[owner[row["id"]]][owner[child]] += 1
assert all(count == 0 for a, values in matrix.items() for b, count in values.items() if a != b)
components = []
unseen = set(by_id)
while unseen:
    stack = [min(unseen)]
    reached = set()
    while stack:
        item = stack.pop()
        if item not in reached:
            reached.add(item)
            stack.extend(graph[item] - reached)
    unseen -= reached
    components.append(sorted(reached, key=lambda value: (len(value), value)))
assert len(components) == 16 and all(len(c) == 5 for c in components)
assert all(len({owner[item] for item in c}) == 1 for c in components)
splits = []
for split, roots in groups.items():
    selected = [row for row in rows if owner[row["id"]] == split]
    buckets = collections.Counter((row["minimum_depth"], row["proof_steps"]) for row in selected)
    keys = {json.dumps(row["motif_key"], separators=(",", ":")) for row in selected}
    position_counts = [{op: sum(word[position] == op for word in roots) for op in "CIJT"}
                       for position in range(2)]
    splits.append({"split": split, "roots": list(roots), "ids": [row["id"] for row in selected],
                   "motif_count": len(keys), "component_count": len(roots),
                   "buckets": [{"depth": d, "proof_steps": n, "count": count}
                               for (d, n), count in sorted(buckets.items())],
                   "root_position_operation_counts": position_counts})
assert [s["motif_count"] for s in splits] == [40, 20, 20]
assert all(a["count"] == 2*b["count"] == 2*c["count"]
           for a, b, c in zip(*(s["buckets"] for s in splits)))
assert all(row["canonical_proof_count"] == 1 for row in rows)
print(json.dumps({"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "source_schema": report["schema_version"], "source_summary": report["summary"],
                  "connected_components": components, "splits": splits, "edge_matrix": matrix,
                  "cross_split_edges": 0,
                  "scope": "Accepted finite left_spine_ops_v1 catalogue only; not generated-world isolation"},
                 ensure_ascii=False, sort_keys=True, indent=2))
