"""R3 T0012: lightweight docs consistency check (not a replacement for semantic review)."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FREEZE_HEAD = "56b41de11a2651da615230117f0d96bd6e0d6e92"

def read(rel):
    return (ROOT / rel).read_text()

readme = read("README.md")
impl = read("docs/implementation_status.md")
handoff = read("docs/handoffs/T0012-proof-key.md")

# 1) T0012 status consistent = awaiting_review across all three docs
assert "单棵证明的规范键（T0012" in readme
assert "`awaiting_review`" in readme.split("单棵证明的规范键（T0012", 1)[1], "README"
assert "`awaiting_review`" in next(s for s in impl.splitlines() if s.startswith("- T0012")), "impl"
assert "- 状态：`awaiting_review`" in handoff, "handoff"

# 2) docs point at the new R3 RUN/provenance
prov = ROOT / "reports/T0012/pi-r3-guards2/provenance.md"
assert prov.exists(), "R3 provenance missing"
assert "pi-r3-guards2" in readme, "README does not reference pi-r3-guards2"
assert "pi-r3-guards2" in impl, "implementation_status does not reference pi-r3-guards2"
assert "pi-r3-guards2" in handoff, "handoff does not reference pi-r3-guards2"

# 3) key cross-links from the three docs resolve
def resolve(doc_rel, base_rel):
    base = (ROOT / doc_rel).parent
    return (base / base_rel).resolve()
links = {
    ("README.md", "reports/T0012/pi-r3-guards2/provenance.md"),
    ("README.md", "reports/T0012/review-r2/review.md"),
    ("README.md", "docs/handoffs/T0012-proof-key.md"),
    ("docs/implementation_status.md", "../reports/T0012/pi-r3-guards2/provenance.md"),
    ("docs/implementation_status.md", "handoffs/T0012-proof-key.md"),
    ("docs/implementation_status.md", "../reports/T0012/review-r2/review.md"),
    ("docs/handoffs/T0012-proof-key.md", "../../reports/T0012/pi-r3-guards2/provenance.md"),
}
for doc_rel, link in links:
    p = resolve(doc_rel, link)
    assert p.is_relative_to(ROOT) if hasattr(Path, "is_relative_to") else True, (doc_rel, link)
    assert (p / "index.md" if link.endswith("/") else p).exists() or p.exists(), (doc_rel, link)

# 4) frozen baseline
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                      capture_output=True, text=True, check=True).stdout.strip()
assert head == FREEZE_HEAD, head

# 5) markdown hygiene (no trailing whitespace, ends with newline)
for rel in ("README.md", "docs/implementation_status.md", "docs/handoffs/T0012-proof-key.md"):
    t = read(rel)
    assert t.endswith("\n"), rel
    assert all(line == line.rstrip() for line in t.splitlines()), rel

print("PASS: R3 docs consistency (T0012=awaiting_review x3; pi-r3-guards2 x3; provenance; links; HEAD frozen)")
