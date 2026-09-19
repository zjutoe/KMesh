"""T0009 R2 rework check: scope, frozen inputs, local links and text hygiene.

Run only through record_check.py after Pi's final documentation is written.
This checks the handoff, not proof correctness or research conclusions.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "reports/T0009"
PRODUCT = "src/kmesh/logic/proof_enumeration.py"
TESTS = "tests/test_proof_enumeration.py"
HANDOFF = "docs/handoffs/T0009-proof-enumeration.md"
MUTABLE = {PRODUCT, TESTS, HANDOFF, "README.md", "docs/implementation_status.md"}


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def main():
    baseline = json.loads((TASK / "planning-baseline.json").read_text())
    frozen = json.loads((TASK / "planning-files.json").read_text())
    review = json.loads((TASK / "review-r1/final-audit.json").read_text())
    history = review["history_sha256"]
    for name, digest in history.items():
        assert sha(name) == digest, f"historical evidence changed: {name}"
    for name, digest in baseline["source_sha256"].items():
        if digest is not None:
            assert sha(name) == digest, f"frozen source changed: {name}"
    for name, digest in frozen.items():
        assert sha(name) == digest, f"planning file changed: {name}"
    subprocess.run(["git", "merge-base", "--is-ancestor", baseline["head"], "HEAD"],
                   cwd=ROOT, check=True)
    assert git("branch", "--show-current").strip() == "T0009-proof-enumeration"
    changed = {s for s in git("diff", baseline["head"], "--name-only", "-z").split("\0") if s}
    changed.update(s for s in git("ls-files", "--others", "--exclude-standard", "-z").split("\0") if s)
    planned = set(frozen) | {HANDOFF, "docs/implementation_status.md",
                             "reports/T0009/planning-files.json"}
    planned.update(history)
    planned.add("reports/T0009/review-r1/final-audit.json")
    for name in changed:
        assert (name in MUTABLE or name in planned or
                name.startswith("reports/T0009/pi-")), f"outside scope: {name}"
        assert (ROOT / name).is_file(), f"file deleted: {name}"
        assert not any(part in ("pytest-tmp", "__pycache__")
                       for part in Path(name).parts), f"scratch not ignored: {name}"
    subprocess.run(["git", "diff", "HEAD", "--check"], cwd=ROOT, check=True)
    docs = [ROOT / p for p in ("README.md", "docs/implementation_status.md", HANDOFF)]
    provenance = sorted(TASK.glob("pi-*/provenance.md"))
    assert provenance, "missing Pi provenance"
    docs.extend(provenance)
    for path in [*docs, ROOT / PRODUCT, ROOT / TESTS]:
        content = path.read_text()
        assert content.endswith("\n"), f"missing final newline: {path}"
        assert all(line == line.rstrip() for line in content.splitlines()), f"trailing whitespace: {path}"
    links = 0
    for path in docs:
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            link = link.strip().strip("<>")
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = path.parent / unquote(parsed.path)
            assert target.exists(), f"broken local link: {path}: {link}"
            links += 1
    handoff = (ROOT / HANDOFF).read_text()
    assert "- 状态：`awaiting_review`" in handoff, "handoff must await review"
    status = (ROOT / "docs/implementation_status.md").read_text()
    line = next(line for line in status.splitlines() if line.startswith("- T0009"))
    assert "awaiting_review" in line, "T0009 status must await review"
    print(f"PASS: scope, frozen inputs, {len(docs)} documents/{links} local links, text hygiene, awaiting_review")


if __name__ == "__main__":
    main()
