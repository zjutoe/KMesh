# T0007 R2 证据溯源（含 R1 更正）

- 日期：2026-09-17（UTC）
- 分支：`T0007-relation-dag`；HEAD `74a96f3735831d16a14dedffbaa6e0654f8b7658`
- 执行：pi harness + `qwen3.8-coding:27b-q8_0-64k`（Pi 进程环境 `PI_PROVIDER=ollama`、`PI_MODEL=qwen3.8-coding:27b-q8_0-64k`；R1 记录中的 `qwen3.8-max-preview` 仅为协议别名，实际模型以此环境证据为准）
- 本轮返工范围：仅 `tests/test_dependency.py`（generator 用例补原因／类型断言、改正一名例注释）与记录／文档。产品 `src/kmesh/logic/dependency.py` 冻结，SHA-256 `4b01df6f08e243c649f0459a23e6e8a68f946fc0eec41814f889e65cd972ca3f` 与 Codex R1 冻结值一致，本轮未改。本轮新测试文件 SHA-256：`722869ef49a4884d52c1423d3743d4802264bd55ebc7a84521f9433d74ba6313`（仅断言与注释变化，fixture 与测试数 44 不变）。
- 本轮**不重复 full、不串接 doctor**（返工契约）；完整回归沿用 Codex R1 独立复跑结果（`../review-r1-full/`，482 passed），本轮未新跑完整回归。

## 本轮 RUN

| RUN | 命令 | 开始（UTC） | 结束（UTC） | elapsed_s | exit | 结果 |
|---|---|---|---|---|---|---|
| `pi-r2-focused` | `.venv/bin/python -m pytest -q tests/test_dependency.py --basetemp reports/T0007/pi-r2-focused/pytest-tmp`（record_check.py 包装） | 2026-09-17T06:44:36.628136 | 2026-09-17T06:44:37.017959 | 0.376 | 0 | **44 passed**；stderr 为空（本次独占 basetemp，无共享临时目录清理警告） |
| `pi-r2-doc-check` | `.venv/bin/python reports/T0007/pi-r2-scripts/doc_check.py`（交接／README／实现状态／本 provenance 四文件：本地链接、末尾换行、行尾空白） | 2026-09-17T07:04:34.189179 | 2026-09-17T07:04:34.239780 | 0.037 | 0 | OK，4 文件链接／换行／空白全部干净 |
| `pi-r2-diff-check` | `git diff --check` | 2026-09-17T07:04:34.300138 | 2026-09-17T07:04:34.318631 | 0.006 | 0 | 干净（注：不覆盖未跟踪新文件） |

时间直接引自各 `record.json` 的 `started_at_utc`/`finished_at_utc`。**命名更正**：`elapsed_s` 是记录器自计的进程时长，与首末时间戳相减（如 `pi-r1-full` 的 6.441s）不是同一量，R1 表将其混标为“耗时”是命名错误；本表分列。

## 对 R1 记录（`../pi-r1-full/provenance.md` 与交接 R1 执行记录）的逐项更正

1. **torch 版本与机器属性（review R2.1）**：R1 provenance “torch 2.9.1+cu128、CPU 机器”均错误。实存 `../pi-r1-full-doctor.json` 为 **torch 2.10.0+cu126**、RTX 3090 不可见仅因进程隐藏 CUDA；机器本身**有 GPU**（见下条 2 的原始报告，device_count=1 的 RTX 3090，torch 2.10.0+cu126）。2.9.1+cu128 无出处，撤回。
2. **cpu_only 归因（review R2.2）**：R1 所称“共享 GPU 瞬时抖动”与“如实双留证”均**撤回**——无证据支持。事实：`record_check.py` 第 54 行对所有 pi-* RUN 子进程强制 `CUDA_VISIBLE_DEVICES=""`（T0006 记录器沿用），故 `pi-r1-full` 内 doctor 的 `cpu_only` 是**确定性读数**，与隐藏 CUDA 完全一致，与抖动无关。另，三次 `status=ok` 中：一次有原始记录——`/tmp/t7d3.json`（自述命令 `bash -c ".venv/bin/python -m kmesh.cli doctor --out /tmp/t7d3.json"`，2026-09-17T04:58:09.601679 UTC 直连 shell 运行、不经记录器、CUDA 未隐藏；status=ok、1 设备 RTX 3090、torch 2.10.0+cu126）；其余两次同命令写同一路径被覆盖，**无原始记录，属自述、不可核验**，不再补跑 doctor 冒充历史。
3. **命令与 basetemp 偏差（review R2.3）**：R1 所称“除入口误写外无契约偏差”不成立。**全部 pi-r1-* pytest 均未用合同要求的独占 `--basetemp`**，落在共享 `/tmp/pytest-of-mye`；两个 full（`pi-r1-full-dev1`、`pi-r1-full`）的原始 stderr 含共享临时目录清理警告（PytestWarning，rm_rf 报错，非产品失败），原样保留在各自 `stderr.txt`。`pi-r1-full` 实际为 `bash -c ".venv/bin/python -m pytest tests -q && .venv/bin/python -m kmesh.cli doctor --out reports/T0007/pi-r1-full-doctor.json"`：用目录 `tests` 代替合同七文件清单，并串接了合同命令外的 doctor。这些不是四条合同命令的原样执行；Codex 已按原命令独立复跑（482 passed），当前无产品回归阻塞，R2 按合同改用独占 basetemp（见本表，stderr 为空）。
4. **“改名留存”（review R2.4）**：自述更正。失败 RUN 现位于 `../pi-r1-full-dev1/`（record.json：04:54:07→04:54:11 UTC，exit 1，内容为 482 项通过 + `python -m kmesh doctor` 入口误写失败）。R1 所称“改名”的动作细节**无法事后核验**：无 mv／日志原始记录，按自述，失败运行最初以合同名 `pi-r1-full` 落盘后改名 `pi-r1-full-dev1`，**原名自述为 `pi-r1-full`、具体文件系统操作 unknown**；是否满足独占 RUN／不得复用名称要求 unknown，交 Codex 裁量；目录本轮不再移动、不重建。
5. **杂项更正（review R2.5）**：(a) `pi-r1-diff-check-r2` 实际仅 `git diff --check` + 44 项聚焦测试，**不含**文档链接／新文本检查，R1 称其为“文档编辑后补录”的卫生检查是夸大；(b) `git diff --check` 不检查未跟踪新文件，R1 手工执行的换行／空白检查**未入任何 RUN、无原始记录**，属自述；本轮以 `pi-r2-scripts/` 新 RUN 覆盖；(c) 记录器 17 项快照**包含记录器自身 `record_check.py`**，R1 “其余 15 项已追踪产品/测试文件”表述不准（15 中 1 项是记录器）；(d) 测试分组更正为 **9 顺序 + 8 循环 + 8 变换/纯度（含 1200 节点链）+ 15 输入边界 + 2 大整数 + 2 隔离 = 44**，R1 交接记录中“变换/纯度 7 例”为计数错误。(e) README “合同 RUN 全绿”与交接“无其他偏差”一并撤回（本文件第 2、3 条）。

## 与 R1 的关系

R1 六个 RUN（`pi-r1-preflight`、`pi-r1-focused`、`pi-r1-full-dev1`、`pi-r1-full`、`pi-r1-diff-check`、`pi-r1-diff-check-r2`）原件、`../pi-r1-full/provenance.md` 与全部 Codex 证据**未改、未移动**；本文件只追加更正，不修改 R1 原文。（后两行 RUN 在本表补录，交接文档相应行同步说明；本文件不在记录器 17 项文件集内，不形成自我引用。）
