"""T0010 R2 preflight/docs checker; original planning checker stays frozen."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "reports/T0010"
HANDOFF = "docs/handoffs/T0010-minimum-depth.md"
PRODUCT = "src/kmesh/logic/depth.py"
TEST = "tests/test_depth.py"


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def main():
    mode = sys.argv[1]
    assert mode in ("preflight", "docs")
    audit = json.loads((TASK / "review-r1/final-audit.json").read_text())
    frozen = json.loads((TASK / "planning-files.json").read_text())
    assert git("rev-parse", "HEAD").strip() == audit["head"]
    assert git("branch", "--show-current").strip() == "T0010-minimum-depth"
    for manifest in (audit["history_sha256"], audit["review_material_sha256"], frozen):
        for name, digest in manifest.items():
            assert sha(name) == digest, name
    for name, digest in json.loads((TASK / "planning-baseline.json").read_text())["source_sha256"].items():
        if digest is not None:
            assert sha(name) == digest, name
    assert sha(PRODUCT) == audit["reviewed_files"][PRODUCT]
    if mode == "preflight":
        assert sha(TEST) == audit["reviewed_files"][TEST]
        print("PASS: R2 baseline, product/test frozen start, prior evidence and Codex review unchanged")
        return
    changed = {p for p in git("diff", audit["head"], "--name-only", "-z").split("\0") if p}
    changed.update(p for p in git("ls-files", "--others", "--exclude-standard", "-z").split("\0") if p)
    allowed = set(frozen) | set(audit["history_sha256"]) | set(audit["review_material_sha256"]) | {
        PRODUCT, TEST, HANDOFF, "README.md", "docs/implementation_status.md", "reports/T0010/review-r1/final-audit.json"}
    for name in changed:
        assert name in allowed or name.startswith("reports/T0010/pi-r2"), f"outside scope: {name}"
        assert (ROOT / name).is_file(), f"deleted: {name}"
        assert not any(x in ("pytest-tmp", "__pycache__") for x in Path(name).parts), name
    docs = [ROOT / p for p in ("README.md", "docs/implementation_status.md", HANDOFF)]
    provenance = list(TASK.glob("pi-r2*/provenance.md"))
    assert provenance, "missing new R2 provenance"
    docs.extend(provenance)
    links = 0
    for path in [*docs, ROOT / TEST]:
        content = path.read_text()
        assert content.endswith("\n") and all(s == s.rstrip() for s in content.splitlines()), path
    for path in docs:
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            parsed = urlsplit(link.strip().strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            assert (path.parent / unquote(parsed.path)).exists(), (path, link)
            links += 1
    assert "- 状态：`awaiting_review`" in (ROOT / HANDOFF).read_text()
    assert "awaiting_review" in next(line for line in (ROOT / "docs/implementation_status.md").read_text().splitlines()
                                     if line.startswith("- T0010"))
    subprocess.run(["git", "diff", "HEAD", "--check"], cwd=ROOT, check=True)
    print(f"PASS: frozen history/product, R2 scope, {len(docs)} documents/{links} links, awaiting_review")


if __name__ == "__main__":
    main()
