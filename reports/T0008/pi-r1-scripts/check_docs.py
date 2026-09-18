"""T0008 R1 文档检查：本地链接、末尾换行、行尾空白。

只检查列出的文档；退出码 0 = 全部通过。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC_ROOTS = (ROOT, ROOT / "docs" / "handoffs", ROOT / "reports" / "T0008")
FILES = (
    "docs/handoffs/T0008-ground-derivations.md",
    "README.md",
    "docs/implementation_status.md",
    "reports/T0008/pi-r1-full/provenance.md",
)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def bases_for(doc: Path) -> tuple[Path, ...]:
    return (doc.parent, *DOC_ROOTS)


def main() -> int:
    failures: list[str] = []
    for rel in FILES:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            failures.append(f"{rel}: missing final newline")
        for lineno, line in enumerate(text.splitlines(), 1):
            if line != line.rstrip():
                failures.append(f"{rel}:{lineno}: trailing whitespace")
        for m in LINK_RE.finditer(text):
            target = m.group(1).split("#", 1)[0]
            if not target:
                continue
            if re.match(r"^[a-z]+://", target):
                continue  # non-local, unchecked
            candidates = [base / target for base in bases_for(path)]
            if not any(c.exists() for c in candidates):
                failures.append(f"{rel}: broken local link -> {m.group(1)}")
    for f in failures:
        print(f"doc-check FAIL: {f}")
    if failures:
        return 1
    print(f"doc-check OK: {len(FILES)} files, links/newlines/trailing-whitespace clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
