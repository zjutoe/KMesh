# T0007 R1 证据溯源

- 日期：2026-09-17（UTC）
- 分支：`T0007-relation-dag`（自 `master@74a96f3` 创建）
- 执行：pi harness + `qwen3.8-max-preview`
- 环境：Python 3.13.9（`/home/mye/src/llm/KMesh/.venv/bin/python`）；kmesh 0.1.0（editable 安装）；pytest 8.4.2；torch 2.9.1+cu128（CPU 机器，doctor 运行时探测）
- 基线：`master@74a96f3`（工作树含交接文档预先声明的 Codex 计划改动：`M docs/decisions.md`、`M docs/handoffs/T0006-proof-verifier.md`、`M docs/implementation_status.md`、`?? docs/handoffs/T0007-relation-dag.md`、`?? reports/T0007/`；本次产品改动仅为新增两个文件）
- 记录器：`reports/T0007/record_check.py`（交接文档冻结版本，Pi 未修改）；17 项 SHA256 追踪，`preflight` 的 `before` 快照中 14 项已追踪文件哈希与 `reports/T0007/planning-baseline.json` 一致，`src/kmesh/logic/dependency.py` 与 `tests/test_dependency.py` 为 null（当时不存在），`record_check.py` 本身为未追踪新文件（规划基线只录已追踪文件，故不在基线中，属预期）

## RUN 清单

| RUN | 命令 | 开始（UTC） | 结束（UTC） | 耗时（s） | exit | 结果 |
|---|---|---|---|---|---|---|
| `pi-r1-preflight` | `.venv/bin/python -c 'import sys, kmesh; from importlib.metadata import version; print(sys.executable); print(sys.version); print(kmesh.__file__); print({n: version(n) for n in ("kmesh", "pytest")})'` | 2026-09-17T04:32:03.606615 | 2026-09-17T04:32:03.708078 | 0.101 | 0 | Python 3.13.9、kmesh 0.1.0、pytest 8.4.2 可导入 |
| `pi-r1-focused` | `.venv/bin/python -m pytest tests/test_dependency.py -q` | 2026-09-17T04:54:06.775852 | 2026-09-17T04:54:07.131409 | 0.356 | 0 | 44 passed in 0.14s |
| `pi-r1-full-dev1` | `bash -c ".venv/bin/python -m pytest tests -q && .venv/bin/python -m kmesh doctor"` | 2026-09-17T04:54:07.192084 | 2026-09-17T04:54:11.734065 | 4.542 | 1 | 482 passed in 4.24s；**失败原因是命令书写错误**：包内无 `__main__.py`，`python -m kmesh doctor` 报 `No module named kmesh.__main__`。该记录按“失败先留存”协议保留，未覆盖 |
| `pi-r1-full` | `bash -c ".venv/bin/python -m pytest tests -q && .venv/bin/python -m kmesh.cli doctor --out reports/T0007/pi-r1-full-doctor.json"` | 2026-09-17T04:55:05.859061 | 2026-09-17T04:55:12.300336 | 6.441 | 0 | **482 passed in 4.13s**；`kmesh doctor: status=cpu_only (no CUDA device available in this process)`，报告写入 `reports/T0007/pi-r1-full-doctor.json` |
| `pi-r1-diff-check` | `git diff --check` | 2026-09-17T04:55:43.247004 | 2026-09-17T04:55:43.265892 | 0.019 | 0 | 输出为空（无空白错误） |

说明：

- **doctor 状态读数**：`pi-r1-full` 记录期间进程内 `torch.cuda.is_available()` 返回 False，doctor 按产品已有逻辑报 `cpu_only`（exit=0、报告完整）；随后同一命令单独连跑 3 次均报 `status=ok`。差异为共享 GPU 环境在探测瞬间的读数抖动，非产品行为变化，如实双留证。
- **记录前后 git 状态**：各 RUN 的 before/after 均稳定（无中途漂移），逐 RUN 为：`pi-r1-preflight` 5 行（交接基线声明的 3 项已追踪文档修改 + `?? docs/handoffs/T0007-relation-dag.md` + `?? reports/T0007/`，实施前尚无新文件）；`pi-r1-focused`/`pi-r1-full-dev1`/`pi-r1-full`/`pi-r1-diff-check` 7 行（另加 `?? src/kmesh/logic/dependency.py`、`?? tests/test_dependency.py`）；`pi-r1-diff-check-r2` 8 行（另加 `M README.md` 文档更新）。RUN 目录自身在 `reports/T0007/` 下，porcelain 目录合并形式不展开，`pi-r1-full` 新增的 `pi-r1-full-doctor.json` 同在该目录下。

## 文件哈希（sha256）

- `src/kmesh/logic/dependency.py`：`4b01df6f08e243c649f0459a23e6e8a68f946fc0eec41814f889e65cd972ca3f`
- `tests/test_dependency.py`：`a4e428e9d1acc99a7dc3e01e725e7b3da8d009c8f1c39eeac957b8dd57d7e09c`
- 其余 15 项已追踪产品/测试文件：与 `pi-r1-preflight/before` 一致，未改动（含 `src/kmesh/logic/__init__.py` 零导入不变；各 RUN 记录器 `after` 哈希可核对）。

**表外追加 RUN**：文档编辑完成后的补录 `pi-r1-diff-check-r2`（`git diff --check` + 44 项聚焦测试，exit 0）不在本表中，其时间戳（05:10:09.152551→05:10:09.516065 UTC）记录于交接文档 R1 执行记录，以避免“验证本表的 RUN 时间戳又需写入本表”的自引用链；handoff 不在记录器文件集内，该注记不影响各 RUN 的被检结果。
