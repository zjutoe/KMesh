# T0003 Pi 首轮实施 provenance

- 日期：2026-09-15（续前一会话，无中断损失；会话恢复后逐条复核了分支、文件与记录目录状态）。
- 实际工具／模型：Pi + `qwen3.8-coding-27b`（Ollama 本地别名 `qwen3.8-coding:27b`；`PI_BASE_URL=http://127.0.0.1:11434/v1`，`PI_REASONING_LEVEL=off`）。
- 基线：分支 `T0003-logic-types`，自 `9acaa3184fa3b87a2263cfb21571224c609867be`（master，T0002 已接受）建立；Codex 交接改动（本文档、`docs/decisions.md`、`reports/T0003/` 记录器与 planning 检查、`docs/implementation_status.md` 更新）保留在工作树，未丢弃、未单独提交。
- 环境（pi-r1-preflight，exit 0）：`.venv/bin/python` = Python 3.13.9；editable `kmesh 0.1.0` 指向本仓库 `src/kmesh/__init__.py`；`pytest 8.4.2`；新模块起点哈希为 null，现有产品文件哈希与 T0002 接受版本一致（`cli.py` `b3163390…`、`config.py` `7a3a43db…`、`test_config.py` `e0e63ff4…`、`test_doctor.py` `5a1f324d…`）。

## 改动文件

- 新增 `src/kmesh/logic/__init__.py`（仅包说明，无导入）。
- 新增 `src/kmesh/logic/types.py`（`LogicValidationError`、`Atom`、`Clause` 与私有校验函数；仅标准库 `re`、`dataclasses`）。
- 新增 `tests/test_logic_types.py`（60 个手工合成用例）。
- 修改 `README.md`、`docs/implementation_status.md`（“已实施，awaiting_review”及范围限定）。
- 修改本交接文档（状态与 Pi 执行记录）。
- 未改：`config.py`/`cli.py`/environment、旧测试、pyproject/依赖、研究计划、AGENTS、历史报告；`reports/T0003/record_check.py` 原样使用。

## 命令、退出码与日志路径（均为 Codex 记录器保存，前后源码哈希见各 record.json）

1. `record_check.py pi-r1-preflight -- .venv/bin/python -c '…版本/路径…'` → exit 0，`reports/T0003/pi-r1-preflight/`。
2. `record_check.py pi-r1-focused -- .venv/bin/python -m pytest -q tests/test_logic_types.py --basetemp reports/T0003/pi-r1-focused/pytest-tmp` → **exit 1，59 passed / 1 failed**，`reports/T0003/pi-r1-focused/`。失败为测试自身断言错误（`inter` 例误写 `body[0] == body[1]`；契约例中两原子谓词 `p`/`q` 不同、仅参数对相同），实现行为经交互冒烟复核正确。
3. 最小修复：仅改 `tests/test_logic_types.py` 该断言为谓词/参数各自相等。
4. `record_check.py pi-r2-focused -- …（同定向命令，新 RUN）` → exit 0，**60 passed**，`reports/T0003/pi-r2-focused/`。
5. `record_check.py pi-r1-full -- .venv/bin/python -m pytest -q tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0003/pi-r1-full/pytest-tmp` → exit 0，**159 passed**（60 logic + 74 config + 25 doctor），无 skip/xfail，`reports/T0003/pi-r1-full/`（本文所在目录）。

## 卫生检查

- `git diff --check` → 通过。
- 新/改文本文件（`logic/__init__.py`、`types.py`、`test_logic_types.py`、`README.md`、`implementation_status.md`、交接文档）尾随空白与末尾换行 → 通过；仓库根 `.gitignore` 的 `__pycache__/` 规则覆盖新编译缓存（`git check-ignore` 确认）。
- `git ls-files` 无 pytest-tmp；`reports/T0003/*/pytest-tmp/` 由记录器目录级 `.gitignore`（`*/pytest-tmp/`）排除。
- 记录器 before/after 源码哈希对照确认 full 运行期间产品文件与旧测试/记录器零改动；历史目录（T0001/T0002 及 T0003 planning 与既有 RUN）未改动、未重用。

## 来源与边界限制

- 测试全部为手工合成对象；数据版本、采样 seed、checkpoint 均为 N/A；无训练。
- 只读本仓库代码、任务文档与 `.venv` 元数据；未联网、未安装/升级/下载任何包（PyPI 未访问）；`CUDA_VISIBLE_DEVICES` 由记录器固定为空，测试仅用 CPU。
- 新模块导入隔离由 `test_import_isolation_blocks_torch_and_yaml` 的子进程实测（拦截式 finder + `sys.modules` 断言）。
- 本层仅验证句法与单 clause 变量作用域；world 合格性、E0 模板、DAG、重复/泄漏与证明审计均未实现，构造成功不代表数据合法。

## 未运行项

- JSON/YAML 加载、序列化、CLI、World/Patch/Query/Proof、ModelBatch/EvalMeta、求解器、生成器、tokenizer、训练、M0 smoke：本轮范围外，not_run。
- 自动 commit/push：未执行，等待 Codex 验收。
