# T0002 第 2 轮（Pi 返工）溯源

- **实际基线**：`git rev-parse HEAD` = `2c15f6a6db71ab2839643276f43eee05cab99f15`（任务分支 `T0002-model-config`，HEAD 与第 1 轮相同；本任务全部改动仍为工作树变更，未提交）。
- **执行前 `git status --short`**（2026-09-14）：

  ```text
   M README.md
   M docs/implementation_status.md
   M src/kmesh/cli.py
  ?? configs/
  ?? docs/handoffs/T0002-model-config.md
  ?? reports/T0002/
  ?? src/kmesh/config.py
  ?? tests/test_config.py
  ```

- **源码预检**（契约给出的只读命令，原样执行，EXIT=0）：

  ```text
  /home/mye/src/llm/KMesh/.venv/bin/python
  {'kmesh': '0.1.0', 'PyYAML': '6.0.3', 'pytest': '8.4.2'}
  /opt/anaconda3/lib/python3.13/site-packages/yaml/__init__.py
  ```

- **配置样例核对**：`configs/model_e0.yaml` 与第 1 轮相同（未被本轮修改；驱动内 `source.count("heads: 4") == 1` 预检通过）。
- **使用工具与模型**：Pi + `qwen3.8-coding-27b`（本地 Ollama；会话环境 `PI_MODEL=qwen3.8-coding:27b-q8_0-64k`、`PI_BASE_URL=http://127.0.0.1:11434/v1`、`PI_REASONING_LEVEL=off`）。未换模型。Codex 第 1 轮验收未指定换用其他代理。
- **本轮变更文件**（相对第 1 轮验收冻结版本）：
  - `src/kmesh/config.py`：R1（`import yaml` 移入 `_load_strict_yaml`，模块顶层不再导入 yaml/PyYAML）、R2（`construct_mapping` 对非 MappingNode 委托给 `yaml.SafeLoader.construct_mapping` 产生 `ConstructorError(YAMLError)`；`yaml.load` 边界仅捕获 `(KeyError, TypeError, ValueError)` 转 `ConfigError`，不用宽 `except Exception`）、R3（`model.dropout` 为非零整数值时在 `float()` 之前即被拒绝）。R1 之外，本轮相对 review-r1 冻结输入的唯一来源是 Codex 的 R1–R4 要求；实现基座恢复自冻结快照（见更正 C2）。
  - `tests/test_config.py`：R4（全部非法文档 fixture 改为“完整合法文档 + 单点变异”，每个用例断言目标规则原因与源路径；`schema_version` 用例使用完整文档并把期望/实际值写入消息）。新增回归：R1（阻塞 yaml 导入 + 缺失元数据子进程中 `--help`/`doctor` 行为）、R2（5 个构造错误文档的 API 与 CLI 子进程断言）、R3（`±10**400` 的 API 与 CLI 断言）。
  - 开发证据：`reports/T0002/pi-r2-dev1/`（新目录；`dev_checks.py` 及其全部 stdout/stderr/`dev-summary.json`）。
  - 文档：`docs/handoffs/T0002-model-config.md`（追加第 2 轮 Pi 执行记录、状态改 `in_progress`→`awaiting_review`）、`docs/implementation_status.md`（T0002 条目更新）。
- **合同命令**：
  - 自检验证：`.venv/bin/python -m pytest -q --basetemp reports/T0002/pi-r2-dev1/pytest-tmp tests/test_config.py tests/test_doctor.py` → **EXIT=0**，`91 passed in 3.18s`（66 新/改 config + 25 T0001 回归）。
  - 开发检查：`.venv/bin/python reports/T0002/pi-r2-dev1/dev_checks.py` → **EXIT=0**，8 项检查全部通过（R1；R2 API + 5×R2 CLI；R3），见 `pi-r2-dev1/dev-summary.json`。
  - 最终验证（契约首轮命令原样，输出目录此前不存在）：`.venv/bin/python reports/T0002/run_checks.py reports/T0002/pi-r2` → **EXIT=0**，十个子检查退出码全部符合预期（module-help、config-help、model-help、module-valid、console-valid = 0；invalid-model = 1；missing-argument = 2；tests、doctor-regression、diff-check = 0），末尾输出 `PASS: T0002 verification completed`（原样保存为 `pi-r2/driver.stdout`）；`verification.json` 为 `{"result": "PASS", "entrypoints_equal": true, "scope": "model_only", "doctor_regression": "cpu_only"}`；`pi-r2/tests.stdout` 为 `91 passed`；`doctor-cpu.json` 为 `status=cpu_only`、`errors=[]`（`CUDA_VISIBLE_DEVICES=""`）。
- **SHA-256**：配置样例、实现/测试/文档文件、驱动与本轮全部验证产物（`pi-r2/` 与 `pi-r2-dev1/`，`pytest-tmp/` 除外）见 `sha256.txt`。
- **卫生检查**：全部本轮变更/新增文件以单个 `\n` 结尾、无尾随空白（逐一核对）；`pytest-tmp/` 由任务级 `.gitignore` 忽略未跟踪；README 与状态文档链接全部解析到已存在文件；驱动 `diff-check`（`git diff --check`）通过。
- **未做**：数据、模型、训练或正式实验命令均 `not_run`；无网络、无 GPU 训练、无额外依赖；未卸载/重装任何包。

## 第 2 轮更正记录（R5）

- **C1：早期已删除产物的历史边界（承接第 1 轮更正）**。第 1 轮曾删除自写驱动产物（旧 `pi-r1` 目录）——该部分原始日志**不可恢复**，本任务所有记录只能证明现存文件一致，不能证明被删除产物的前后源码或日志未变化。此项作为永久限制保留，不用第 2 轮通过反向声称旧证据存在。
- **C2：本轮返工中 `src/kmesh/config.py` 曾一度引入错误字段集（已修复，须如实披露）**。第 2 轮实施初期，一次整体重写把 `ModelConfig`/`parse_model_config` 的字段集错误地改为通用 LLM 配置字段（`layers/sequence_length/vocab_size/embed_scale/embed_dtype/mlp_expansion` 等），丢失了研究计划 §8.3 的九个字段（`patch_encoder_layers/core_layers/ffn_size/memory_slots_per_patch/workspace_tokens/max_clause_tokens`）、`CONFIG_SCHEMA_VERSION`、`as_dict()` 与 `hidden_size % heads` 检查。全量测试对照暴露 39 项失败后，以 Codex 冻结的 review-r1 输入快照 `reports/T0002/review-r1/input-snapshot/src/kmesh/config.py`（即第 1 轮被验收审阅的实现）为基座恢复，再在其上重放 R1–R3 修复。`configs/model_e0.yaml`、`src/kmesh/cli.py`、`tests/test_doctor.py` 及研究文档均未受影响。开发脚本 `dev_checks.py` 的 R3 段也存在同样的错误字段集，已同步更正到 §8.3 字段后重跑通过。
- **C3：可复验事实与 Pi 自述的区分**。上述 C2 过程仅由第 2 轮工作树与测试输出证明（39 failed → 修复后 91 passed），中间的错误版本文件本身未单独留档；第 1 轮实现的可复核副本即 review-r1 冻结快照。本 provenance 不声称被删除的旧日志或其前后源码状态。
- **C4：驱动与证据目录**。本轮开发日志在 `reports/T0002/pi-r2-dev1/`（独立新目录，未复用/清空任何旧目录）；最终产物在 `reports/T0002/pi-r2/`（目录此前不存在，契约命令原样执行一次即 PASS，未重跑）。`pi-r1/`、`review-r1/` 未做任何修改。
- **C5：状态快照时点**。本 provenance 中 `git status` 为执行开始时刻；`sha256.txt` 为产物落盘后生成，覆盖本轮终态文件。两者时点不同但不冲突：期间变更文件仅限上述“本轮变更文件”清单。
