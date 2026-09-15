# T0003 Pi 第 2 轮（R1 返工）provenance

- 日期：2026-09-15。
- 实际工具／模型：Pi + `qwen3.8-coding-27b`。本会话运行元数据：`provider=ollama`、`model=qwen3.8-coding:27b-q8_0-64k`、`api=openai-completions`（完整别名以 Ollama 实际加载的端点为准；配置别名 `qwen3.8-coding:27b`，`PI_REASONING_LEVEL=off`）。
- 基线核对：分支 `T0003-logic-types`，HEAD `9acaa3184fa3b87a2263cfb21571224c609867be`；返工前实测 `src/kmesh/logic/types.py` SHA-256 = `b6b4cc94af5746160fd09b5cf99477193c89ac1624f89e3b43e8107ffadc2a44`、`tests/test_logic_types.py` = `a475ed354880ba3cb849ce9cfda50d5b12ee8e9568138169b4d85917a20eae97`，与第 1 轮冻结基线逐位一致；Codex 第 1 轮验收目录（`review-r1/`、`review-r1-full/`、`review-r1-boundaries/`、`review-r1-arity/`）及全部历史 RUN、规划文件均保留未动、未重用。
- 中断范围澄清（更正首轮“无中断损失”的简写表述）：首轮此前超时中断的未完成回复未生成任何测试或产品文件；首轮全部落盘内容以第 1 轮冻结哈希为准完整保留，返工从冻结基线开始，无中断期内容参与本轮。

## 本轮改动（仅两个允许文件）

- `src/kmesh/logic/types.py`：R1 最小修复。7 个类型/长度错误分支删除对未验证值或容器的 `!r`，只报告字段路径、预期与实际类型/长度（`atom.pred` 类型、`atom.args[i]` 成员类型、`atom.args` 容器类型与长度、`clause.body` 容器类型与成员类型、`clause.head`）；长度检查先于成员检查；未验证容器（如含超大整数的 list）不再被遍历或格式化。已确认为字符串后的词法错误与未绑定变量诊断（4 处 `!r`）保持原行为。未添加 safe_repr、未加宽泛异常捕获、未改整数转换上限、未改合法接受范围。
- `tests/test_logic_types.py`：在修复前先追加 8 条 R1 回归（`10**5000` + 工厂参数化、显式短 `ids`，`pinned_int_str_limit` fixture 将整数转换上限固定为 4300 并在 `finally` 恢复）。覆盖契约八条单点路径与目标字段路径/原因；未改弱任何旧断言。

## 命令、退出码与日志（Codex 记录器；失败先于修复保存）

1. `record_check.py pi-r3-focused -- .venv/bin/python -m pytest -q tests/test_logic_types.py --basetemp reports/T0003/pi-r3-focused/pytest-tmp` → **exit 1，8 failed / 60 passed**，`reports/T0003/pi-r3-focused/`。八条路径均以原生 `ValueError`（整数转换上限）逸出，未产生约定的 `LogicValidationError` 与字段路径；原 60 例不受影响。
2. 最小修复 `types.py`（见上）。
3. `record_check.py pi-r4-focused -- …（同定向命令，新 RUN）` → exit 0，**68 passed**，`reports/T0003/pi-r4-focused/`。
4. `record_check.py pi-r2-full -- .venv/bin/python -m pytest -q tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0003/pi-r2-full/pytest-tmp` → exit 0，**167 passed**（68 logic + 74 config + 25 doctor），无 skip/xfail，`reports/T0003/pi-r2-full/`（本文所在目录）。

## 边界限制

- 无数据版本、采样 seed、checkpoint；无训练、无联网、无包安装；`CUDA_VISIBLE_DEVICES` 由记录器置空。
- 第 1 轮全部记录与 provenance 原样保留；本轮未覆盖任何旧目录。

## 未运行项

- 求解器、数据审计、CLI/文件加载、训练与 M0 smoke：范围外，not_run。
- 自动 commit/push：未执行，交 Codex 复验 R1 与受影响回归。
