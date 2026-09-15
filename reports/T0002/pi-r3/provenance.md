# T0002 第 3 轮（Pi 返工）溯源

- **实际基线**：`git rev-parse HEAD` = `2c15f6a6db71ab2839643276f43eee05cab99f15`（分支 `T0002-model-config`，HEAD 与前两轮相同；全部 T0002 改动仍为工作树变更，未 commit、未 push）。
- **轮次起点快照**（本轮新增的留存机制，文件在 `reports/T0002/pi-r3-dev1/round-start-snapshot.txt`）：记录日期、HEAD、`git status --short` 与实施/测试/示例/驱动 SHA-256（`config.py` = `edcc274f…`，与第 2 轮 `pi-r2/sha256.txt` 所列一致，即 Codex review-r2 冻结输入）。此后每轮先落盘该快照再动源码。
- **使用工具与模型**：Pi + `qwen3.8-coding-27b`（本地 Ollama；`PI_MODEL=qwen3.8-coding:27b-q8_0-64k`，`PI_REASONING_LEVEL=off`），与规划指定一致，未换模型。
- **本轮变更文件**：
  - `src/kmesh/config.py`：**仅** `_load_strict_yaml` 中 `yaml.load(...)` 边界新增一个 `except (IndexError, AttributeError, OverflowError)` 子句（R2）。ConfigError 原样传播、YAMLError 处理、MappingNode 检查、ModelConfig/字段集/`parse_model_config`/CLI 均未动。
  - `tests/test_config.py`：新增 8 个回归（4 个输入 × API 与真实 CLI 子进程各一组）：`!!int ''`、`!!float ''`、`!!timestamp nope`、sexagesimal 浮点 `"0:"*200+"0"`（401 字符）。断言 ConfigError（消息含 `invalid YAML`）、CLI 退出码 1、stdout 空、stderr 含源路径且无 `Traceback`。原 91 个用例未改。
  - 文档：`docs/handoffs/T0002-model-config.md`（追加第 3 轮 Pi 记录、状态 `awaiting_review`）、`docs/implementation_status.md`。
  - 证据：`reports/T0002/pi-r3-dev1/`（起点快照 + 修复前失败原样输出）、`reports/T0002/pi-r3-dev2/`（修复后原样输出）、`reports/T0002/pi-r3/`（契约驱动产物，见下）。
- **留存方式（按第 2 轮 R5 要求改变）**：本轮**没有**再运行会覆盖固定路径的旧 dev 驱动，也没有复用任何已存在证据目录；每次检查使用独占新目录并原样保存命令输出与退出码：
  - `pi-r3-dev1/pre-fix.stdout` / `pre-fix.exit`：`.venv/bin/python -m pytest -q --basetemp reports/T0002/pi-r3-dev1/pytest-tmp -k builtin_constructor tests/test_config.py` → **EXIT=1，`8 failed, 66 deselected in 0.85s`**（修复前；输出中含逸出的 `IndexError`、`AttributeError`、`OverflowError` 原文）。这是本轮唯一在修复前运行并立即留存的失败记录。
  - `pi-r3-dev2/post-fix.stdout` / `post-fix.exit`：同一命令、独立新目录 → **EXIT=0，`8 passed, 66 deselected in 0.45s`**（修复后）。
- **合同命令**：`.venv/bin/python reports/T0002/run_checks.py reports/T0002/pi-r3`（`pi-r3` 此前不存在，驱动自建目录并一次通过）→ **EXIT=0**，十项子检查退出码符合预期，末尾 `PASS: T0002 verification completed`（`pi-r3/driver.stdout` 原样 11 行）；`verification.json` = `{"result": "PASS", "entrypoints_equal": true, "scope": "model_only", "doctor_regression": "cpu_only"}`；`pi-r3/tests.stdout` = `99 passed in 3.64s`（91 原例 + 8 新回归）；`doctor-cpu.json` = `status=cpu_only`、`errors=[]`。
  - **如实记录一次操作事故**：首次尝试用 shell 重定向 `> reports/T0002/pi-r3/driver.stdout` 启动驱动时，目录尚不存在导致重定向先于 Python 失败，驱动实际未运行、`pi-r3` 亦未创建（无残留）。改为先重定向到临时文件、驱动成功后再移入 `pi-r3/` 保存；`pi-r3/` 内驱动产物来自**这一次**成功的契约命令执行，未重跑。
- **SHA-256**：本轮终态的源码、测试、配置样例、驱动、交接/状态文档与 `pi-r3/`、`pi-r3-dev1/`、`pi-r3-dev2/` 的全部产物（`pytest-tmp/` 除外）见 `sha256.txt`。
- **未做**：数据、模型、训练或正式实验命令均 `not_run`；无网络、无 GPU 训练、无依赖变更；`pi-r1`、`pi-r2`、`pi-r2-dev1`、`review-r1`、`review-r2` 中任何文件均未改动（本轮只读）。

## 第 3 轮 R5 更正记录（对 Pi 自述与历史证据的边界）

- **G1（“39 项失败”原始日志：未保存，不可核验）**。第 2 轮 provenance C2/C3 称字段集事故“经全量测试对照暴露 39 项失败后修复”、并由“测试输出证明（39 failed → 修复后 91 passed）”。该 39 failed 的 pytest 原始输出当时只在交互终端，**从未落盘**，当前仓库内不存在任何文件可证明这一具体数字；本处予以更正：该事故修复过程为 Pi 自述，**不可核验**。现可核验的失败记录只有本轮 `reports/T0002/pi-r3-dev1/pre-fix.stdout`（R2 四个输入各 8 项修复前失败中的全部 8 项）。
- **G2（第 2 轮 dev 驱动修复前输出：已被覆盖，不可核验）**。`reports/T0002/pi-r2-dev1/dev_checks.py` 以固定路径 `write_text` 写 `*.stdout`/`*.stderr`/summary。第 2 轮修正 dev 脚本字段集前后在**同一目录**先后运行，修复前的原始失败输出已被第二次运行覆盖，现仅存修复后运行（`R3 ... PASS`）的产物；“39 项”“R3 FAILED”等修复前内容无法回验。自此起不再运行该脚本；本轮起采用“独占新目录 + 先留存失败再修复”的方式（上文留存方式）。
- **G3（第 1 轮产物清单更正：**`module-valid.yaml`** 不存在）**。Pi 第 1 轮记录所称产物清单含 `module-valid.yaml`，但契约驱动从未写出该文件；`pi-r1/` 实际存在的是合法样例 `configs/model_e0.yaml` 的输出 `module-valid.stdout`／`module-valid.stderr`，非法样例才是驱动写出的 `invalid-model.yaml`。第 1 轮清单一律以 `pi-r1/` 现存文件为准。
- **G4（第 1 轮“执行前 `git status`”的时点：自述，且与“实施前”不符）**。`pi-r1/provenance.md` 称“执行前 `git status --short`（2026-09-13）”，但该清单已含 `src/kmesh/config.py`、`tests/test_config.py` 等实现改动，属于**实施完成、驱动运行前**的状态；其对应时点没有落盘的时间戳工件佐证，属 Pi 自述，不能当作“实施前只有规划改动”的证据。本轮起用带日期的 `round-start-snapshot.txt` 替代这类无锚定表述。
- **G5（“全部 fixture 都是完整合法文档单点变异”的准确化）**。第 2 轮 R4 修正实际为：根重复键、未知根键、`schema_version`、必填/类型/取值、`hidden_size`/`heads` 整除、非零整数 `dropout` 等用例已改为“完整合法文档 + 单点变异”，并由目标原因断言核验；而语法错误、根非 mapping、merge 键、非法 tag 等规则本就**不能**字面表达为合法文档的单点变异，其正确性由各用例对目标原因（含源路径）的断言保证，而非由“单点变异”这一构造方式保证。
- **G6（可核验事实与自述的边界，永久保留）**。可核验：本文及 `pi-r3/`、`pi-r3-dev1/`、`pi-r3-dev2/` 内现存文件与哈希；`pi-r1/`、`pi-r2/`、`review-r1/`、`review-r2/` 的冻结清单匹配（经 Codex 哈希审计）。不可核验（自述/已丢失）：第 1 轮被整体删除的早期 pi-r1 产物及其前后状态、第 2 轮字段集事故的 39 项失败原始输出与 dev 脚本修复前输出。本任务记录不再对后者作任何“已证明/已保留”表述。
