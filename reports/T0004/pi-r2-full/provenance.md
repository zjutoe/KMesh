# T0004 · pi-r2-full provenance（R1 测试断言返工）

- 执行者：Pi + Qwen Coding (`qwen3.8-coding:27b`)，2026-09-15（UTC）
- 背景：Codex 第 1 轮验收 `needs_changes`，仅 R1（P2）：`tests/test_reference_engine.py` 的错误原因断言逐字符匹配（字符串 `expect`）且巨整数用例只核对字段，7 条参数化行放过“缺完整原因”的消息（Codex 修复前探针 0/7，见 `reports/T0004/review-r1-reason-guards/`）。本轮只按交接文档 R1 四步返工：产品源码 `src/kmesh/logic/reference_engine.py` 保持冻结（哈希前后一致，见下）；仅改 `tests/test_reference_engine.py` 的参数表与断言；不改契约、预算、接口、旧测试或 Codex 检查脚本。
- 返工内容：
  1. 预算测试 7 行 `expect` 全部为字符串元组（`("positive",)`、`("float",)`、`("str",)` 等），`for fragment in expect` 按完整片段检查；bool/路径/异常类型断言原样保留。
  2. 巨整数参数表新增 `expect` 列：非 tuple 输入 `tuple`、非法成员 `Clause`、负预算 `positive`；工厂 lambda、短 ids、`pinned_int_str_limit` fixture（含整数转换上限的 finally 恢复）保留；测试函数名与 `field` 参数名不变；新增 `assert expect in message`，不新增或删除其他测试（仍 51 项）。
- 三个全新记录 RUN（命令、退出码、耗时见各自 `record.json` 的 `elapsed_s`）：
  - `pi-r2-reason-guards`：`.venv/bin/python reports/T0004/record_check.py pi-r2-reason-guards -- .venv/bin/python reports/T0004/review-r1/check_reason_guards.py`，`SUMMARY: 7/7 diagnostic reason guards effective`，exit 0，耗时 0.172s
  - `pi-r2-focused`：`… pi-r2-focused -- .venv/bin/python -m pytest -q tests/test_reference_engine.py --basetemp reports/T0004/pi-r2-focused/pytest-tmp`，`51 passed in 0.11s`，exit 0，耗时 0.345s
  - `pi-r2-full`：`… pi-r2-full -- .venv/bin/python -m pytest -q tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0004/pi-r2-full/pytest-tmp`，`218 passed in 3.63s`，exit 0，耗时 3.885s
  - 三条记录命令均启动于 2026-09-15T12:06:04Z 起的连续序列；合计约 4.40s。
- 实施时段：完整实施窗口自收到 Codex 第 1 轮结论（`reports/T0004/review-r1/final-audit.json` 创建时间 11:37:16 UTC）起至本文件写入止，约 2026-09-15 11:37–12:10 UTC；会话起始的精确秒数未单独计时，实际记录命令耗时以上述 `elapsed_s` 为准（与第 1 轮 provenance 的耗时口径一致，均只指记录命令）。
- 环境：
  - 分支 `T0004-reference-closure`，HEAD `e53e2bd0ec4cf3347c5b6103ab8061d71666150b`（master，未产生 commit）
  - Python：`.venv/bin/python`（3.13）；`record_check.py` 固定 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`CUDA_VISIBLE_DEVICES=""`，timeout 120s，原样使用未修改
- SHA-256：
  - `src/kmesh/logic/reference_engine.py` `54ff628abeb37dbe66410d87e5522af727db62e345cfa151281c14b64327a147`（与第 1 轮冻结值 `reports/T0004/review-r1/final-audit.json` 一致，产品未改）
  - `tests/test_reference_engine.py` `2434c17e929a9af13281041a9f92ac97e1f03eef98fb3c31a2b3347d1e213090`（返工后；第 1 轮值 `9c2292f8…` 由 Codex 冻结保留于 review-r1 证据）
- 结果计数：目标测试 51 项（定向），完整回归 218 项（新增 51 + 既有 167），无 skip/xfail。
- 第 1 轮 Codex 证据澄清引用（交接文档 r1 验收记录第 ①–⑥ 条）：本记录不再重复其内容，直接引用：规划/实施时序澄清、开发脚本失败恢复（`reports/T0004/review-r1/session-evidence.json`）、`in_progress` 披露（本轮已先落盘 `in_progress` 再完成返工）、计时口径（只看记录命令 `elapsed_s`）、无独立空 domain 早退分支、哈希以完整值为准。
- 环境约束：全程纯本地，无网络、无 GPU（`CUDA_VISIBLE_DEVICES=""`）；未触发研究计划 smoke/profile/GPU 门槛。
- 基线完整性：`git diff --check` 退出 0；历史 RUN（`pi-r1-*`、`planning-*`）、`review-r1*` Codex 证据、`.gitignore` 均未改动；未 commit/push。
- 遗留：无实现遗留；返工未改动任何断言语义以外的行为，测试数量保持 51。
