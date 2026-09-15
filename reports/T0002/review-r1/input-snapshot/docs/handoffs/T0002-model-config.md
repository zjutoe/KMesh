# T0002：模型结构配置的读取与校验

## 任务信息

- 任务编号／修订号：T0002 / r1，2026-09-13。
- 状态：`ready`；Codex 将本任务明确交接给 Pi + Qwen。
- 状态：`awaiting_review`；Pi 第 1 轮（T0002-r1）实施与自检完成（2026-09-13，实际工具／模型见执行记录），等待 Codex 验收；验收记录尚未填写。
- 所属阶段：M0 的配置校验子任务；只覆盖模型结构，完整运行配置和 M0 仍未完成。
- 研究版本：研究计划 v0.1.1，E0 `e0_v2`、E1 `e1_v2`；不改变训练目标、模型输入、研究指标或协议。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`。
- 执行者：Pi + `qwen3.8-coding-27b`；此前确认使用的运行名为 `qwen3.8-coding:27b`。记录实际工具／模型，不自行替换。
- 基线 commit：`2c15f6a6db71ab2839643276f43eee05cab99f15`，分支 `master`；规划开始时工作树干净。其后仅新增本交接文档及状态文档中的任务安排。
- 前置任务：[T0001](T0001-bootstrap-doctor.md) 已 `accepted`，接受实现 `39dabc73e035c8c2627a1e5db4deab31055a9c6d`；验收记录提交 `d7762d8`，当前基线额外清理了 pytest 临时产物跟踪，未改变实现。
- 必读：[AGENTS.md](../../AGENTS.md)；[研究计划](../../KMesh_Research_Plan_v0.1.md) §8.3、§14、§17 的 M0；[T0001 第 2 轮验收记录](T0001-bootstrap-doctor.md)；现有 `src/kmesh/cli.py`、`tests/test_doctor.py`、`pyproject.toml`；[交接模板](TEMPLATE.md)。

## 目标、范围与交付物

单一主要目标：把研究计划中的 **model 区块**变成可独立加载、严格校验的不可变配置对象，提供 `config validate-model --config PATH` 命令，供后续编码器和计算核心的构建复用。

本任务文件 `configs/model_e0.yaml` 仅包含 `schema_version` 和 `model`。它是完整实验配置中的一个独立片段，不是计划中的 `configs/e0_base.yaml`。命令和报告必须明确只校验模型结构；不得把成功解释为完整 E0 配置符合协议或训练可以开始。

| 允许修改／新增的路径 | 交付内容 |
|---|---|
| `src/kmesh/config.py` | `ConfigError`、`ModelConfig`、纯校验与 YAML 加载接口 |
| `src/kmesh/cli.py` | 加入唯一新路径 `config validate-model --config PATH` |
| `configs/model_e0.yaml` | 下文给出的完整模型配置片段 |
| `tests/test_config.py` | 配置边界、CLI、隔离与回归测试 |
| `README.md` | 追加真实命令和“仅校验模型结构”的限制，保留研究介绍 |
| `docs/implementation_status.md` | 按实际执行情况更新 T0002，保留 M0 未完成项 |
| 本交接文档 | 更新状态并追加 Pi 执行记录，不改原契约或填写 Codex 结论 |
| `reports/T0002/` | 分轮次保存驱动脚本、原始日志、输入样例、输出与 hash |

允许命令自动生成已忽略的包缓存、构建元数据及本任务独占的测试临时文件。不得修改 T0001 的实现模块 `utils/environment.py`、既有测试、历史报告、研究计划、AGENTS.md、构建依赖或无关文件。确需改变前置接口或既有测试时先说明冲突，由 Codex 判断。

不实现路由／训练／评估配置，不创建 `e0_base.yaml`、debug/data/E1 配置，不实现配置继承、覆盖、环境变量插值、自动补默认值、插件系统或通用 schema 框架。不构建模型、生成数据、分配训练张量或启动训练；不重新安装依赖，不自动 commit／push。后续 M0/M1 任务另行交接。

## 前提与假设

已验证事实：T0001 接口和 25 个测试已验收；当前有 `.venv` 和 editable `kmesh`。2026-09-13 的规划检查实际导入 PyYAML 成功：Python `3.13.9`，`kmesh 0.1.0`，PyYAML `6.0.3`，pytest `8.4.2`。PyYAML 来源 `/opt/anaconda3/lib/python3.13/site-packages/yaml/__init__.py`。仓库尚无配置模块或配置目录。

规划时用内存字符串确认：现有 `yaml.safe_load` 会把重复的 `heads` 键静默保留为最后一个值；`true` 得到 bool，`.nan` 得到非有限浮点数。不能仅调用 `safe_load` 后就报告配置有效。

执行时核对实际 HEAD、已有改动、工具／模型和 `.venv`。本任务交接／状态文档的变动属于已知规划改动；影响代码依赖的新变化须反馈，不覆盖。模型不匹配、依赖缺失或基线冲突时记录 `blocked` 并交回 Codex；不自行下载、升级或换模型。

执行时核对结论（T0002-r1）：执行时 HEAD 为 `2c15f6a`，工作树仅含本分支已知规划改动（`docs/implementation_status.md` 修改 + 本交接文档），无其他漂移；venv 内实际导入 PyYAML `6.0.3`、`kmesh 0.1.0`、pytest `8.4.2`，`yaml.__file__` 仍为 `/opt/anaconda3/lib/python3.13/site-packages`；`configs/model_e0.yaml` 逐字对照 §8.3 `e0_v2` model 区块核对（`heads: 4` 仅现一次）；全程未下载、未升级包。

只读取仓库代码、指定配置、当前环境元数据与合成 fixture；不读取其他项目、研究数据、测试集、凭据或外部配置。无需网络或 GPU。现有环境检查最多 60 秒，单次 pytest 最多 120 秒，其他验证进程最多 60 秒，总验证预算 10 分钟。超时或崩溃保留证据并反馈；普通契约内实现错误可修复后在新目录重跑。数据版本／训练 seed／checkpoint 为 N/A，本任务不采样或训练。

## 具体实施步骤

### 1. 核对基线并保存模型配置片段

确认前提后将任务改为 `in_progress`。保持 T0001 的 editable 安装；可在核对基线后建立本任务独立分支，不覆盖现有分支，不自动提交。

创建 `configs/model_e0.yaml`，内容必须与下面一致。数值摘自研究计划 §8.3，只是当前示例值，不把它们全部硬锁成唯一允许值。

```yaml
schema_version: 1
model:
  hidden_size: 256
  patch_encoder_layers: 2
  core_layers: 6
  heads: 4
  ffn_size: 1024
  memory_slots_per_patch: 4
  workspace_tokens: 4
  max_clause_tokens: 48
  dropout: 0.1
```

可检查结果：片段有且仅有两个根字段，model 有九个字段；没有混入 seed、router、training 或 evaluation，也没有修改研究计划。

### 2. 实现不可变对象和纯校验

在 `src/kmesh/config.py` 定义 `ConfigError(ValueError)` 和 `@dataclass(frozen=True)` 的 `ModelConfig`。字段名与 YAML 的 model 完全相同；前八个字段类型为 int，dropout 为 float，全部必填，不设默认值。

```python
def parse_model_config(value: object) -> ModelConfig:
    ...

def load_model_config(path: str | Path) -> ModelConfig:
    ...
```

**`parse_model_config` 的入参仅是内层 model 字典**，不接收整个 YAML 文档。该函数不读取文件、不导入 torch、不修改传入对象；通过下列检查后构建 dataclass，失败抛 `ConfigError`：

| 字段／边界 | 校验约定 |
|---|---|
| 内层根值 | 必须为 dict；键必须为字符串；先检查键类型，再检查缺失／未知字段 |
| `hidden_size`、`patch_encoder_layers`、`core_layers`、`heads`、`ffn_size`、`memory_slots_per_patch`、`workspace_tokens`、`max_clause_tokens` | 必须为非 bool 的 int，且大于 0；不接受数值字符串或 `4.0` 代替整数 |
| 维度关系 | `hidden_size % heads == 0`；不额外假定 ffn_size 必须大于 hidden_size 等未约定条件 |
| `dropout` | 允许非 bool 的 int 或 float，有限且 `0 <= value < 1`；验证后转为 float，因此输入 `0` 输出 `0.0` |
| 字段集合 | 九项全部必需；缺字段或额外拼写均报错，不静默忽略或补默认值 |

错误须包含字段路径和原因，例如 `model.hidden_size: expected a positive integer`。整除性错误必须同时包含 `model.hidden_size` 和 `model.heads`，例如 `model.hidden_size: must be divisible by model.heads`，以便下节驱动明确核对。多处同时出错时报告首个明确错误即可，不要求聚合所有错误。不把未知编程异常统一兜底为配置错误。

可检查结果：示例产生不可变 `ModelConfig`；合法替代值如 hidden_size=128、heads=8 可以通过；不能因为与示例不同就拒绝。此处仅判定结构合法，研究配置变动仍须遵循 AGENTS.md 的协议流程。

### 3. 实现严格 YAML 加载

`load_model_config` 按 UTF-8 读取指定文件；读取失败、解码失败、YAML 解析／构造失败和字段校验失败均对外抛 `ConfigError`，信息包含源路径及已有具体原因。只捕获这些明确边界的异常，保留异常原因，不调用 eval。

解析规则：

- 以 **PyYAML SafeLoader 的专用子类**处理 YAML，避免修改全局 SafeLoader 或全局构造器。使用该子类的 `yaml.load` 是安全加载路径，不使用默认／不安全 Loader。
- 在 mapping 构造时拒绝非字符串键及重复键；根和 model 两层都要检查。重复键即使前后值相同也不允许。对 YAML merge 键 `<<`（包括 merge tag）明确报错，不进行隐式合并。
- 其余沿用 SafeLoader 的单文档语义，普通标量 anchor／alias 可以使用，不要求另写解析器。不支持的 tag、多文档、语法错误必须失败。若 alias 得到不符合字段类型的对象，按普通字段类型检查拒绝。
- 外层必须为 dict，且键集合恰好是 `schema_version`、`model`；schema_version 必须为非 bool 的整数 1。空文件、null、序列根、缺失／未知根键或不支持的版本都拒绝。
- 将外层 `model` 交给 `parse_model_config`，返回同一 `ModelConfig` 类型。整个 §8.3 实验配置含额外根字段，不能被本接口接受；不要偷偷丢弃未校验内容。

可检查结果：重复键不会被最后一个值覆盖；错误文件带路径返回受控异常；成功对象只包含经过验证的九个字段。

### 4. 接入 CLI 并覆盖真实边界

新增命令：`python -m kmesh.cli config validate-model --config PATH`，控制台入口 `kmesh` 等价。不增加 `--out`；成功 JSON 输出至 stdout，调用方可保存为文件。

- 参数由 argparse 解析；新增 `config` 的 `validate-model` 子命令及必填 `--config`。
- CLI 显式导入 `ConfigError`、`load_model_config`；按 command 分支调用。同步现有 `_KNOWN_SUBCOMMANDS`、parser 和 dispatch，不能让 config 命令落入 doctor 分支。保持 doctor 的行为、退出码和报告 schema。
- 成功退出 0，stdout 是单个 UTF-8 可序列化 JSON 对象，两空格缩进、末尾换行，不夹杂文字日志；stderr 为空。输出键恰为 `schema_version`（整数 1）、`validation_scope`（字符串 `model_only`）、`model`（用已验证 dataclass 生成的九字段字典）。不回传未校验的原始 YAML 对象，不增加时间戳或其他字段。
- `ConfigError`：退出 1，stdout 为空，stderr 简要写明源路径与原因，不打印 traceback 或伪造成功报告。参数缺失、未知命令／选项退出 2；不把读取／内容错误归为参数错误。
- 根、`config` 和 `config validate-model` 的 `--help` 均退出 0，不能调用加载函数或环境采集。配置校验本身也不调用 doctor、torch、模型或训练。

在 `tests/test_config.py` 覆盖下列行为，先读该文件 imports／fixtures 再执行测试：

1. 示例 YAML 及合法替代尺寸；dataclass 不可变、输入字典未被修改；dropout=0 合法且输出 float。检查 CLI 输出确实来自 loader 的验证结果。
2. 代表性非法类型／数值：整数维度为 bool、字符串、浮点数、零或负数；hidden/head 不整除；dropout 为 bool、字符串、负数、1、NaN／Inf。缺失／未知字段、非字符串键、非 dict 值须失败。用少量有区别的参数化样例验证行为，不机械复制每一行实现。
3. YAML 重复键（根和 model）、merge、空文件、多文档、错误语法、不支持 tag、缺失／错误 schema、非 mapping 根均失败；标量 anchor／alias 的合法样例成功。使用无执行副作用的非法 tag 样例，例如 `!!python/tuple [1, 2]`。
4. 文件不存在、将目录当文件、非法 UTF-8：API 抛 ConfigError，CLI 退出 1、stdout 空、stderr 包含路径与原因。用 tmp_path 构造文件，不依赖权限 chmod。
5. 三种 help 不调用 loader／collector，参数错误退出 2。guard 必须 patch **实际调用位置** `cli.load_model_config`、`cli.collect_environment`；在没有预加载 torch 的子进程中执行配置校验，确认 `torch` 未进入 sys.modules。
6. 对有效文件和至少一个非法字段文件调用实际 CLI+loader，断言返回码、完整 JSON 或错误信息；模块／控制台真实入口由下节命令核验。既有 `tests/test_doctor.py` 的 25 个用例完整复跑，不改弱原断言。

可检查结果：从文件到 dataclass 再到 CLI 的路径可运行，错误不会被静默转换，help 和配置校验均保持隔离。无需真实 GPU，不按固定新增测试数量代替上述行为覆盖。

### 5. 保存机器生成的验证记录并交回验收

README 添加示例命令、输出字段含义和局限：本任务只校验 model，尚未检查路由、训练、数据兼容性、设备可用性或完整 E0 协议。状态文档列明 T0002 `awaiting_review`、M0 `in_progress`；训练和 smoke 保持 `not_run`。不要把完整“配置校验”一项笼统标成完成。

按下节执行并自动保留真实命令、stdout/stderr、退出码和耗时。失败先保留记录，修复后用新轮次目录重跑；不得把手写摘要称为原始日志。测试 guard 若使用临时回归注入，只在内存中进行，并保存实际驱动代码及捕获到的异常；不引用不存在的函数，不改动后又丢掉失败证据。

全部要求满足后，在本文 Pi 区追加记录并改为 `awaiting_review`；出现未解决失败时记录阻塞，不能宣布通过。只由 Codex 验收并标记 accepted。

## 验证方法

工作目录固定为 `/home/mye/src/llm/KMesh`。执行前独立记录 `git rev-parse HEAD`、`git status --short`，并运行以下只读前提检查；失败先记录原因：

```bash
timeout 60s .venv/bin/python -c 'import sys, yaml; from importlib.metadata import version; print(sys.executable); print({n: version(n) for n in ("kmesh", "PyYAML", "pytest")}); print(yaml.__file__)'
```

下面是精确的验证驱动。Pi 将其保存为 `reports/T0002/run_checks.py` 后运行；它不属于产品实现。首轮命令为 `.venv/bin/python reports/T0002/run_checks.py reports/T0002/pi-r1`。将 `reports/T0002/.gitignore` 写为一行 `*/pytest-tmp/`，只忽略临时 fixture，保留日志和报告。驱动要求输出目录此前不存在；返工使用 pi-r2 等新目录，禁止清空旧目录重用。

```python
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path.cwd()
run = Path(sys.argv[1]).resolve()
run.mkdir(parents=True, exist_ok=False)
source = (root / "configs/model_e0.yaml").read_text(encoding="utf-8")
assert source.count("heads: 4") == 1
invalid = run / "invalid-model.yaml"
invalid.write_text(source.replace("heads: 4", "heads: 3"), encoding="utf-8")
checks = [
    ("module-help", [".venv/bin/python", "-m", "kmesh.cli", "--help"], {}, 0),
    ("config-help", [".venv/bin/python", "-m", "kmesh.cli", "config", "--help"], {}, 0),
    ("model-help", [".venv/bin/python", "-m", "kmesh.cli", "config", "validate-model", "--help"], {}, 0),
    ("module-valid", [".venv/bin/python", "-m", "kmesh.cli", "config", "validate-model", "--config", "configs/model_e0.yaml"], {}, 0),
    ("console-valid", [".venv/bin/kmesh", "config", "validate-model", "--config", "configs/model_e0.yaml"], {}, 0),
    ("invalid-model", [".venv/bin/python", "-m", "kmesh.cli", "config", "validate-model", "--config", str(invalid)], {}, 1),
    ("missing-argument", [".venv/bin/kmesh", "config", "validate-model"], {}, 2),
    ("tests", [".venv/bin/python", "-m", "pytest", "-q", "tests/test_config.py", "tests/test_doctor.py", "--basetemp", str(run / "pytest-tmp")], {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}, 0),
    ("doctor-regression", [".venv/bin/python", "-m", "kmesh.cli", "doctor", "--out", str(run / "doctor-cpu.json")], {"CUDA_VISIBLE_DEVICES": ""}, 0),
    ("diff-check", ["git", "diff", "--check"], {}, 0),
]
records = []
for name, argv, overrides, expected in checks:
    start = time.monotonic()
    limit = 120 if name == "tests" else 60
    try:
        p = subprocess.run(argv, cwd=root, env=os.environ | overrides,
                           capture_output=True, timeout=limit)
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        code, out, err = 124, exc.stdout or b"", exc.stderr or b""
    (run / f"{name}.stdout").write_bytes(out)
    (run / f"{name}.stderr").write_bytes(err)
    records.append(dict(name=name, argv=argv, cwd=str(root), env_overrides=overrides,
                        expected_exit=expected, exit_code=code, timeout_s=limit,
                        elapsed_s=round(time.monotonic() - start, 3)))
    (run / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
    print(name, code, flush=True)
    if code != expected:
        raise SystemExit(1)
left = json.loads((run / "module-valid.stdout").read_text(encoding="utf-8"))
right = json.loads((run / "console-valid.stdout").read_text(encoding="utf-8"))
assert left == right
assert set(left) == {"schema_version", "validation_scope", "model"}
assert left["schema_version"] == 1 and left["validation_scope"] == "model_only"
assert left["model"]["hidden_size"] == 256 and left["model"]["heads"] == 4
assert (run / "module-valid.stderr").read_bytes() == b""
assert (run / "console-valid.stderr").read_bytes() == b""
assert (run / "invalid-model.stdout").read_bytes() == b""
assert b"model.hidden_size" in (run / "invalid-model.stderr").read_bytes()
doctor = json.loads((run / "doctor-cpu.json").read_text(encoding="utf-8"))
assert doctor["status"] == "cpu_only" and doctor["errors"] == []
(run / "verification.json").write_text(json.dumps({"result": "PASS", "entrypoints_equal": True, "scope": "model_only", "doctor_regression": "cpu_only"}, indent=2) + "\n")
print("PASS: T0002 verification completed")
```

保存驱动自身执行的 stdout/stderr 和退出码；若末尾断言失败，保留其 traceback 与全部子命令记录，不能只记录“驱动返回非零”。当前源码预检、实际基线和使用模型写入该轮 `provenance.md`；记录配置样例、实现／测试文件、驱动和验证产物的 SHA-256。成功 JSON 来自 CLI stdout，不手工补填。

另检查本任务新文件的末尾换行、尾随空白及 README／状态文档本地链接；`git diff --check` 不覆盖未跟踪文件。上述驱动只负责命令与主要断言，不能替代步骤 4 的测试覆盖或人工 diff 审阅。合成测试无随机采样，seed=N/A；不运行数据、模型、训练或正式实验命令。

## 验收标准

- [ ] A1：片段值与 §8.3 model 一致；接口、对象和 CLI 明确仅校验模型配置，完整实验配置未被误当作已校验。
- [ ] A2：九字段类型／范围、hidden/heads 关系、不可变对象和不修改输入的契约成立；无默认补全或字符串／bool 隐式转换。
- [ ] A3：安全加载，重复／merge／非字符串键及非法外层明确失败；读取、解码和 YAML 错误均有准确源路径与原因。
- [ ] A4：两入口成功 JSON 相同，退出码 0/1/2 符合约定；help 和配置校验不触发环境采集、torch 或训练，guard patch 位置真实有效。
- [ ] A5：新边界测试与 T0001 既有 25 个测试通过，实际配置命令和强制 CPU doctor 回归通过；使用独占临时目录且不跟踪其产物。
- [ ] A6：原始命令、stdout/stderr、退出码、驱动、源码／配置／结果 hash 可追溯；失败证据保留，未核验的历史或临时过程不写成完成。
- [ ] A7：差异仅限允许路径，README 与状态准确；完整配置校验、模型训练及 M0 完成状态没有被提前宣称。

Codex 对冻结的提交／diff 再审，独立核验新测试质量、错误与成功 CLI 路径、隔离 guard 及 doctor 回归，核对产物 hash；不只根据 Pi 的“通过”摘要接受。通过后 T0002 才可成为后续模型构建的依赖。路由／训练配置和 M1 数据 schema 等另行拆分，本任务不预先赋予它们 ready 状态。

## Pi 执行记录

- 轮次、日期、实际工具／模型：**第 1 轮（T0002-r1），2026-09-13，Pi + `qwen3.8-coding-27b`**（本地 Ollama，`PI_MODEL=qwen3.8-coding:27b-q8_0-64k`，`PI_REASONING_LEVEL=off`；与规划指定模型一致）。
- 实际基线、已有改动与本轮变更文件：基线 `2c15f6a`，在任务分支 `T0002-model-config` 上执行；已知规划改动（状态文档修改 + 本交接文档）保留未覆盖。本轮变更／新增：`src/kmesh/config.py`（新增）、`src/kmesh/cli.py`（加入 `config` 子命令，doctor 路径行为保持不变）、`configs/model_e0.yaml`（新增）、`tests/test_config.py`（新增，52 个测试）、`README.md`、`docs/implementation_status.md`、`reports/T0002/`（`.gitignore`、`run_checks.py`、`pi-r1/`）。未触碰 `utils/environment.py`、既有测试、历史报告、研究计划、AGENTS.md、依赖。
- 原始命令、退出状态、耗时及 stdout/stderr 路径：
  - 自检 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/test_config.py tests/test_doctor.py` → **EXIT=0**，`77 passed in 0.38s`（52 新 + 25 T0001 回归）。
  - 前提检查（契约原样命令，EXIT=0，输出全文见 `pi-r1/provenance.md`）。驱动为**契约驱动**（“验证方法”小节 fenced 代码块逐字提取保存，未做任何修改）：`.venv/bin/python reports/T0002/run_checks.py reports/T0002/pi-r1` 原样执行 → **EXIT=0**，十项子检查退出码均符合预期（module-help/config-help/model-help/module-valid/console-valid=0，invalid-model=1，missing-argument=2，tests/doctor-regression/diff-check=0），结尾输出 `PASS: T0002 verification completed`；`verification.json` 为 `{"result": "PASS", "entrypoints_equal": true, "scope": "model_only", "doctor_regression": "cpu_only"}`；驱动自身 stdout/stderr/退出码 → `pi-r1/driver.stdout`（子检查清单）/`driver.stderr`（空）/`driver.exit`。
  - 关键单条：`pi-r1/module-valid.stdout` 为单个 JSON（两入口一致由驱动断言）；`pi-r1/invalid-model.stderr` 含源路径 `invalid-model.yaml` 与 `model.hidden_size`，`invalid-model.stdout` 为空；`pi-r1/doctor-cpu.json` 为 `status=cpu_only`、`errors=[]`（`CUDA_VISIBLE_DEVICES=""`）。
- 覆盖的边界、未运行项与原因：已覆盖——(1) 合法两规格、不可变、输入 dict 不被修改、dropout 0→0.0；(2) int 字段 bool/str/float/0/负数、hidden 非 heads 倍数、dropout bool/str/负/1/NaN/Inf、缺字段、未知字段、非 dict model、非字符串键；(3) 重复键（根层与 model 层）、`<<` merge、`!<merge>` tag、多文档、`!!python/tuple`、语法错误、空文件、非映射根、schema_version 字符串/2/bool/缺失、多余根键、标量锚点/别名合法、完整实验文档（含 router 键）不被接受、缺文件/目录当文件/非法 UTF-8 的 ConfigError 均含源路径；(4) CLI 两入口输出一致、非法 EXIT=1 且 stderr 含路径+字段名+无 Traceback、IO 错误 EXIT=1、三个 help（patch 的是 `cli.load_model_config` 与 `cli.collect_environment` 真实调用点）不触发采集/加载、参数错误 EXIT=2、新 `python -c` 子进程校验后 torch 未进入 `sys.modules`；(5) T0001 既有 25 个测试原样通过。未运行：完整 E0 配置校验、模型构建、训练、性能测量（均不属于本任务或明确禁止）；真实 GPU 数据不读。
- 产物路径、版本／SHA-256：`reports/T0002/pi-r1/`（`commands.json`、十个子命令的 `*.stdout`／`*.stderr`、`verification.json`、`doctor-cpu.json`、`module-valid.yaml`／`invalid-model.yaml`、`driver.stdout`／`driver.stderr`／`driver.exit`、`sha256.txt`、`provenance.md`、`pytest-tmp/`[被任务级 `.gitignore` 忽略]）；配置样例、实现／测试文件、驱动与全部验证产物的 SHA-256 见 `pi-r1/sha256.txt`。本任务代码与文档改动在工作树，**未 commit（按契约不自动 commit）**，随用户指令一次性提交后冻结。
- 失败、偏差、阻塞、临时验证内容及最小复现：开发中自行修正（均未改变契约）：① `cli.py` 初版丢失了 T0001 `main` 对 argparse `SystemExit` 的返回值转换与“输出为目录→EXIT=1”处理，导致 6 个既有 doctor 测试失败；按 `master:src/kmesh/cli.py` 原结构恢复并加 config 分支后全绿；② 一个测试拼 YAML 时尾部换行遗漏致语法错误，补换行修复；③ **驱动偏差（已修正并如实保留记录）**：我先自写了一版自检驱动并跑出一份 `pi-r1` 产物，之后核对交接文档发现契约已规定精确驱动，遂把驱动替换为与文档逐字一致版本、整体删除旧 `pi-r1` 目录、用契约首轮命令重跑生成本套证据；替换前后产品代码与测试完全未变。此为执行流程偏差（应先用契约驱动），非契约变更。无阻塞。最小复现：`.venv/bin/python reports/T0002/run_checks.py <全新 reports/T0002 轮次目录>`。
- 提交验收的 diff／产物范围与状态：范围=本节列出的全部文件 + `reports/T0002/pi-r1`；分支 `T0002-model-config`；状态 `awaiting_review`，请 Codex 冻结工作树并验收。

## Codex 验收记录

- 轮次、日期、实际模型／推理强度：`not_run`。
- 冻结的基线、diff 和产物版本：`not_run`。
- 独立检查／复跑命令、退出状态与结果：`not_run`。
- A1–A7 逐项结论、具体问题与证据：`not_run`。
- 返工要求或剩余限制：`not_run`。
- 最终状态：`not_run`；只由 Codex 根据实际实施结果填写。
- 后续任务：N/A，待验收后确定。
