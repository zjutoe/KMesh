"""T0008 R2 文档检查：diff/授权路径、旧哈希核对、本地链接、文本卫生。

与 R1 脚本的区别（按 review.md R4 返工要求）：
- 本地链接只相对文档所在目录解析，不再兜底到候选目录；
- 新增 pi-r2-scripts/baseline_manifest.json 基线：基线内文件不得删除、
  修改仅限本任务授权文档；新增文件仅限 reports/T0008/pi-r2* 目录；
- 产品哈希与 R1 测试哈希显式钉扎，旧 RUN 原件与基线一致。
退出码 0 = 全部通过。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = Path(__file__).resolve().with_name("baseline_manifest.json")

PRODUCT = "src/kmesh/logic/derivations.py"
TESTS = "tests/test_derivations.py"
PIN_PRODUCT = "32634248f401865d068b13758e133037a7a9bc3dcfa409526bc7df86a9aaf29b"
PIN_TESTS_R1 = "694c255ad5251ac1813b07ec335787b96a14e33b020a6aaaf865ac081c338fc0"
PIN_TESTS_R2 = "4738b484445afd6ada35cc2285f717f110825c667a7e0e6938587875a14ea3eb"

AUTHORIZED_CHANGED = {
    TESTS,
    "README.md",
    "docs/implementation_status.md",
    "docs/handoffs/T0008-ground-derivations.md",
}
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}

DOCS = (
    "README.md",
    "docs/implementation_status.md",
    "docs/handoffs/T0008-ground-derivations.md",
    "reports/T0008/pi-r2-full/provenance.md",
)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    failures: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # 1) 基线文件不得删除、修改仅限授权文档（pi-r2* 为本轮工作产物，其自身
    #    中间态不受基线约束，新文件范围由第 3 条约束）
    for rel, expected in manifest.items():
        parts = rel.split("/")
        if parts[:2] == ["reports", "T0008"] and len(parts) > 2 and parts[2].startswith("pi-r2"):
            continue
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"baseline: deleted {rel}")
            continue
        if sha256(path) != expected and rel not in AUTHORIZED_CHANGED:
            failures.append(f"baseline: unauthorized change {rel}")

    # 2) 显式钉扎：产品 / R1 测试 / R2 测试
    if sha256(ROOT / PRODUCT) != PIN_PRODUCT:
        failures.append(f"pin: product hash changed from {PIN_PRODUCT}")
    if manifest.get(TESTS) != PIN_TESTS_R1:
        failures.append("pin: manifest does not record the R1 tests hash (baseline suspect)")
    if sha256(ROOT / TESTS) != PIN_TESTS_R2:
        failures.append(f"pin: tests hash is not the recorded R2 value {PIN_TESTS_R2}")

    # 3) 新增文件仅限 reports/T0008/pi-r2* 目录（本轮合同授权范围）
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts) or rel.suffix == ".pyc":
            continue
        if str(rel) in manifest:
            continue
        if not (rel.parts[:2] == ("reports", "T0008") and len(rel.parts) > 2
                and rel.parts[2].startswith("pi-r2")):
            failures.append(f"new file outside authorized pi-r2* dirs: {rel}")

    # 4) 本地链接：只相对文档所在目录解析
    for rel in DOCS:
        doc = ROOT / rel
        text = doc.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            failures.append(f"{rel}: missing final newline")
        for lineno, line in enumerate(text.splitlines(), 1):
            if line != line.rstrip():
                failures.append(f"{rel}:{lineno}: trailing whitespace")
        for m in LINK_RE.finditer(text):
            target = m.group(1).split("#", 1)[0]
            if not target or re.match(r"^[a-z]+://", target):
                continue
            if not (doc.parent / target).exists():
                failures.append(f"{rel}: broken local link (relative to {doc.parent}) -> {m.group(1)}")

    for f in failures:
        print(f"doc-check FAIL: {f}")
    if failures:
        return 1
    print(f"doc-check OK: {len(manifest)} baseline files reconciled, {len(DOCS)} docs links/hygiene clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
