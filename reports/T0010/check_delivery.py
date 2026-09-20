"""T0010 baseline/scope/document checks, not an oracle for product correctness."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "reports/T0010"
PRODUCT = "src/kmesh/logic/depth.py"
TESTS = "tests/test_depth.py"
HANDOFF = "docs/handoffs/T0010-minimum-depth.md"
MUTABLE = {PRODUCT, TESTS, HANDOFF, "README.md", "docs/implementation_status.md"}


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def main():
    assert len(sys.argv) == 2 and sys.argv[1] in ("preflight", "docs")
    mode = sys.argv[1]
    baseline = json.loads((TASK / "planning-baseline.json").read_text())
    frozen = json.loads((TASK / "planning-files.json").read_text())
    for name, digest in baseline["source_sha256"].items():
        if digest is not None:
            assert sha(name) == digest, f"frozen source changed: {name}"
    for name, digest in frozen.items():
        assert sha(name) == digest, f"planning file changed: {name}"
    subprocess.run(["git", "merge-base", "--is-ancestor", baseline["head"], "HEAD"],
                   cwd=ROOT, check=True)
    assert git("branch", "--show-current").strip() == "T0010-minimum-depth"
    changed = {p for p in git("diff", baseline["head"], "--name-only", "-z").split("\0") if p}
    changed.update(p for p in git("ls-files", "--others", "--exclude-standard", "-z").split("\0") if p)
    for name in changed:
        assert (name in MUTABLE or name in frozen or
                name == "reports/T0010/planning-files.json" or
                name.startswith("reports/T0010/pi-")), f"outside scope: {name}"
        assert (ROOT / name).is_file(), f"file deleted: {name}"
        assert not any(p in ("pytest-tmp", "__pycache__") for p in Path(name).parts), name
    if mode == "preflight":
        import kmesh
        assert sys.version_info[:3] == (3, 13, 9)
        assert str(Path(sys.executable).absolute()) == str(ROOT / ".venv/bin/python")
        assert Path(kmesh.__file__).resolve() == ROOT / "src/kmesh/__init__.py"
        for name, version in baseline["packages"].items():
            assert importlib.metadata.version(name) == version, name
        assert all(not (ROOT / p).exists() for p in (PRODUCT, TESTS)), "run preflight before coding"
        print("PASS: branch, frozen baseline, environment, scope; new product/tests absent")
        return
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
            parsed = urlsplit(link.strip().strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            assert (path.parent / unquote(parsed.path)).exists(), f"broken link: {path}: {link}"
            links += 1
    assert "- 状态：`awaiting_review`" in (ROOT / HANDOFF).read_text()
    line = next(s for s in (ROOT / "docs/implementation_status.md").read_text().splitlines()
                if s.startswith("- T0010"))
    assert "awaiting_review" in line
    print(f"PASS: scope, frozen inputs, {len(docs)} documents/{links} local links, text hygiene, awaiting_review")


if __name__ == "__main__":
    main()
