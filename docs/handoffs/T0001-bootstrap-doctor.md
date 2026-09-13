# T0001：最小 Python 包与环境诊断命令

## 任务信息

- 任务编号／修订号：T0001 / r1；创建于 2026-09-13。
- 状态：`awaiting_review`（首轮实施完成，待 Codex 验收）。本文是已准备好的实施契约。
- 所属阶段：M0 的第一个子任务，为 E0 基础性质研究准备可运行入口；本任务通过不等于 M0 完成。
- 研究依据：研究计划文档 v0.1.1；E0 协议 `e0_v2`，E1 协议 `e1_v2`。本任务不改变研究协议。
- 规划者：Codex + `gpt-6-astra`，`xhigh`。
- 执行者：Pi + `qwen3.8-coding-27b`。
- 验收者：Codex + `gpt-6-astra`，`xhigh`。
- 代码基线：`8d41ad631441bab9dd92af26ac99b6544e664e2d`。规划开始时工作树干净；本交接文档为随后新增的规划文件。执行前记录实际 HEAD 和已有改动；仅增加交接文档的提交不影响代码基线。
- 前置任务：N/A，仓库首项实施任务；现有研究计划、AGENTS.md 和交接模板已提交，无未验收代码依赖。
- 必读材料：[工作协议](../../AGENTS.md) 全文；[研究计划](../../KMesh_Research_Plan_v0.1.md) §0.2、§14、§16.1–16.2、§17 的 M0、§19；[交接模板](TEMPLATE.md)。

## 目标、范围与交付物

单一主要目标：在当前仓库根目录建立可编辑安装的 `kmesh` 包，使模块入口和控制台入口都能运行 `doctor --out PATH`，报告真实依赖及 CUDA 探测结果，并明确区分 CPU 降级与诊断失败。

允许新增或修改的路径仅限下表。主要行为实现集中在 `cli.py` 和 `utils/environment.py` 两个文件。

| 路径 | 用途 |
|---|---|
| `pyproject.toml` | setuptools 构建、src 包发现、依赖及控制台入口 |
| `src/kmesh/__init__.py`、`src/kmesh/utils/__init__.py` | 轻量包标识；不得在导入时探测硬件 |
| `src/kmesh/cli.py` | argparse 命令行、报告写入与退出码 |
| `src/kmesh/utils/environment.py` | 只读环境采集 |
| `tests/test_doctor.py` | 本任务的外部边界与命令行为测试 |
| `README.md` | 实际安装、help、doctor、测试命令与当前限制 |
| `docs/implementation_status.md` | 记录 T0001 待验收、M0 进行中及后续未运行项 |
| `reports/environment.json` | 模块入口生成的真实环境报告 |
| `reports/T0001/` | 其余诊断报告、依赖快照、执行日志、版本与来源说明 |
| 本交接文档 | Pi 更新状态并追加执行记录；原任务契约和 Codex 验收区不可自行改写 |
| `.venv/` | 本任务本地虚拟环境，已由现有 `.gitignore` 忽略 |

另允许本任务命令自动生成、被现有 `.gitignore` 忽略的 `src/kmesh.egg-info/`、相关 `__pycache__/`、`.pytest_cache/` 等缓存／构建副产物，以及 pytest 在临时目录中创建的合成 fixture 文件。这些不作为源码交付，不扩大上表中的人工修改范围。

不实施配置校验、数据／求解器、模型、训练、评估、20-step smoke 或性能测量，不创建这些功能的占位接口。§19 的决策记录初始化等后续文档工作另行安排；README 和状态文档直接引用现有研究计划。完整实验环境锁定、驱动／CPU／主存盘点和 RNG／kernel 元数据不属于这个最小诊断契约，M0 后续仍须补齐。不得修改研究计划、AGENTS.md、模板或无关文件；不得自动 commit 或 push。

## 前提与假设

### 已验证事实

Codex 在 2026-09-13 于上述代码基线进行了只读检查；以下是规划证据，不是 Pi 的执行结果：

- 仓库尚无 Python 实现、测试或 `.venv`，只有研究计划、工作协议、模板及基础仓库文件。
- `/opt/anaconda3/bin/python3` 为 Python `3.13.9`；实际成功导入 `torch`、`numpy`、`yaml`、`pytest`。
- 已安装版本：PyTorch `2.10.0+cu126`、NumPy `2.3.5`、PyYAML `6.0.3`、pytest `8.4.2`、pip `25.3`、setuptools `80.9.0`、wheel `0.45.1`。
- `torch.version.cuda` 为 `12.6`；这是 PyTorch 构建对应的 CUDA 版本，尚未检查 GPU 是否实际可用。
- `venv` 可用，`timeout` 位于 `/usr/bin/timeout`；Pi 可执行文件位于 `/home/mye/.nvm/versions/node/v24.8.0/bin/pi`，但尚未确认其模型配置或运行 Pi。

### 执行时检查与边界

- 先确认实际执行工具／模型符合本任务要求，并核对代码基线。Pi 不可用、模型不匹配或出现影响本任务的其他改动时，记录 `blocked` 及证据，交回 Codex；不得自行换模型或覆盖已有工作。
- 本任务复用当前机器已有依赖：新建 `.venv` 并使用 `--system-site-packages`。这是有明确来源的启动环境，尚不是隔离、锁定的正式实验环境。若解释器、依赖或构建工具不满足前提，停止安装并反馈；不在线补装、不升级全局环境或驱动。
- `.venv` 若已存在，先核对其解释器和 `pyvenv.cfg`；不自动删除或重建不明环境。若已有 `reports/environment.json`，先在任务产物目录保留原文件及 hash，再生成本轮报告。
- 数据、训练 seed、模型 checkpoint、张量形状及研究公式：N/A。本任务仅使用合成测试 fixture 和环境元数据，不读取研究数据、用户数据集、凭据或其他项目；不联网、不分配测试张量、不启动训练。
- 允许调用 PyTorch CUDA 可用性与设备属性查询；GPU 可能因此初始化。报告不宣称 GPU 已通过 forward/backward 或可稳定训练。
- 每条验证命令上限 120 秒；实际 doctor 上限 60 秒；验证预算合计 10 分钟，不含编码时间。超时（通常退出码 124）、进程崩溃或意外资源占用均记录为失败并停止重复尝试，交回 Codex。

## 具体实施步骤

### 1. 核对执行条件并建立可安装包

记录实际工具／模型、HEAD、工作树状态和解释器／依赖版本，满足前提后将任务设为 `in_progress`。

`pyproject.toml` 使用 `setuptools.build_meta`，构建依赖 `setuptools>=68` 和 `wheel`，从 `src/` 发现包。项目名 `kmesh`，包版本 `0.1.0`（独立于研究文档版本），Python 要求 `>=3.11`；运行依赖为 `torch`、`numpy`、`PyYAML`，`dev` extra 包含 `pytest`。控制台入口为 `kmesh = "kmesh.cli:main"`，pytest 的 `testpaths` 为 `tests`。本轮不增加其他依赖。

在**当前仓库根目录**创建 `src/kmesh/`，不要再嵌套一层项目根目录。两个 `__init__.py` 保持轻量；help 和包导入不得触发 PyTorch 导入或环境采集。

可检查结果：可编辑安装成功，包路径确实指向本仓库 `src/kmesh`，控制台入口已生成。不要用临时设置 `PYTHONPATH` 掩盖安装问题。

### 2. 实现只读环境采集接口

在 `src/kmesh/utils/environment.py` 提供：

```python
def collect_environment() -> dict[str, object]:
    ...
```

函数只采集并返回 JSON 可序列化的内建类型，不写文件、不打印、不安装依赖。使用标准库 `sys`、`platform`、`datetime`、`importlib.metadata`，在函数内延迟导入 `torch`。报告字段固定如下：

| 字段 | 类型与含义 |
|---|---|
| `schema_version` | 整数 `1` |
| `generated_at_utc` | 含 UTC 时区的 ISO 8601 时间字符串 |
| `python_executable` | 当前 `sys.executable`，字符串 |
| `python_version` | 当前 Python 版本，字符串 |
| `platform` | `platform.platform()`，字符串 |
| `packages` | 固定键 `torch`、`numpy`、`PyYAML`、`pytest`、`pip`、`setuptools`；值为安装元数据版本字符串，未安装为 `null` |
| `torch_import_ok` | 布尔值，表示本轮实际导入成功 |
| `cuda.runtime_version` | `torch.version.cuda` 的字符串或 `null`；不是驱动版本 |
| `cuda.available` | PyTorch 可用性查询结果；探测失败或未进行时为 `null` |
| `cuda.device_count` | 本次可用且可见设备数量；CPU 降级为 `0`，探测失败为 `null` |
| `cuda.devices` | 按 index 排序的列表；每项仅含 `index` 整数、`name` 字符串、`total_memory_bytes` 正整数 |
| `status` | `ok`、`cpu_only` 或 `error` |
| `errors` | 字符串列表；每项写明失败组件和原因，成功／CPU 降级时为空 |

采集与失败语义：

1. 分别读取依赖版本。`torch`、`numpy`、`PyYAML` 缺失视为错误；`pytest`、`pip`、`setuptools` 元数据缺失仅记 `null`。其他元数据读取异常必须记录错误，不能当作未安装。本接口只承诺这些版本的元数据检查及 PyTorch 的实际导入，不宣称对全部依赖进行功能自检。
2. 实际导入 torch；失败则 `torch_import_ok=false`，CUDA 三个标量字段均为 `null`，devices 为空，记录错误。
3. 导入成功后记录 runtime，调用 `torch.cuda.is_available()`。为 false 时，available=false、device_count=0、devices 为空，不继续枚举设备；这里的 count 表示本次可用设备，不表示物理 GPU 数量。
4. 为 true 时调用 `torch.cuda.device_count()` 和每个 `torch.cuda.get_device_properties(i)`。count 必须至少为 1，属性完整且满足类型／数值约束。查询异常或不一致时记录错误，将 available、device_count 置 `null`、devices 清空；已取得的 runtime 和 torch 导入成功信息保留，不把部分枚举当作成功。
5. 任何错误优先得到 `status=error`；没有错误且 available=true 为 `ok`，没有错误且 available=false 为 `cpu_only`。遇错误仍保留其余已知字段。只在这些外部依赖边界捕获异常，不用覆盖整个程序的静默兜底。

可检查结果：无 CUDA 的正常环境得到可用的 CPU 报告；损坏的 torch 导入或失败的设备探测得到带原因的 error 报告，二者可区分。

### 3. 实现两种等价 CLI 入口

在 `src/kmesh/cli.py` 提供 `main(argv: list[str] | None = None) -> int`，并以 `raise SystemExit(main())` 支持模块启动。仅实现 `doctor` 子命令和必填参数 `--out PATH`，使用 argparse。

- 根命令与 doctor 的 `--help` 均退出 0，且不调用环境采集。未知子命令、缺少子命令或缺少 `--out` 均退出 2，不创建报告。
- doctor 调用采集函数，将报告按 UTF-8、两空格缩进、末尾换行写入目标文件；允许创建不存在的父目录，拒绝非有限 JSON 数值。同一路径允许覆盖，因此执行时须遵守前述旧报告保留要求。
- `ok` 和 `cpu_only` 均退出 0；stdout 简要写明状态与实际路径，CPU 情况须明确显示 `cpu_only`。
- `error` 报告成功落盘后退出 1，并在 stderr 给出简短原因；不可只返回非零却丢弃采集到的诊断报告。
- 路径为目录、创建目录失败或写入失败：退出 1，stderr 指明目标与 I/O 原因，不打印成功消息。序列化错误同样失败，不生成空的成功报告。

具体例子：`python -m kmesh.cli doctor --out reports/environment.json` 在依赖完好但 CUDA 不可用时，应写出 `status="cpu_only"`、`cuda.available=false`，退出 0；模拟 torch 导入失败时应写出 `status="error"` 和原因，退出 1。

可检查结果：模块入口与 `.venv/bin/kmesh` 入口接受相同参数、遵循相同 schema 和退出约定。

### 4. 编写有意义的边界测试

所有测试放在 `tests/test_doctor.py`，只用标准库 mock／pytest monkeypatch、临时目录及合成设备对象，不需要真实 GPU。先检查该文件的 imports 和 fixtures，再运行测试；隔离外部 pytest 插件。

必须覆盖：

- 合成 CPU 环境和单 GPU 环境的字段、版本来源、状态及正整数显存；测试不绑定当前机器具体版本或 GPU 型号。
- 缺少必需依赖、torch 导入失败、CUDA 查询抛异常、available=true 但 count=0 均报告 error；工具依赖元数据缺失仅为 null。至少覆盖一次非“包未安装”的元数据读取异常。
- 模块导入／help 不导入 torch；可在隔离子进程通过导入拦截禁止 torch，以验证延迟导入。help 不运行 collector 也要验证。
- 使用实际 collector 加合成外部依赖，验证 CPU／GPU／错误三种报告经过 CLI 后的退出码与 JSON 文件内容；不要只测试手写报告的序列化。
- 嵌套输出目录自动创建；使用已存在的临时目录作为输出文件，稳定复现 I/O 失败并断言非零和 stderr。不要用 chmod 模拟权限失败，避免特权环境下测试失真。
- 参数错误返回 2、不生成文件；不支持的 `train` 命令不能被当成成功执行。

可检查结果：无需 GPU 的测试可以证实正常、降级及错误路径；真实环境测试不会读取任何实验数据。

### 5. 运行真实安装／诊断验证并保存证据

按下节命令执行，每项记录命令、退出码、关键 stdout／stderr 和耗时；不通过吞掉错误的管道制造成功。由实际程序生成 JSON，不手写或修补真实环境结果。

保存 `reports/T0001/installed-packages.json` 及 `reports/T0001/provenance.md`：后者记录基线、实际 diff 范围、解释器及虚拟环境路径、继承系统包的事实、安装命令，以及 torch/numpy/yaml 实际导入路径。原始下载渠道查不到时如实写 `unknown`；本轮安装来源是本地既有环境，不能声称已重建完整依赖锁。记录报告与依赖快照的 SHA-256；原始日志放本轮单独文件中，重试时保留失败日志。

可检查结果：报告可追溯到真实环境和当前实现，命令成功／失败没有依赖语言模型估计。

### 6. 完成最小使用说明并交回验收

README 只列已实现入口、安装／诊断／测试命令，解释三种状态，链接现有研究计划和交接文件。状态文档列出 T0001 `awaiting_review`、M0 `in_progress`；配置校验、CPU forward/backward、20-step smoke、GPU 训练与性能测量均为 `not_run`，说明尚未实现／尚未获本任务覆盖。不得用 doctor 成功推断科研结论或宣称 M0 完成。

把实际结果追加到本文 Pi 执行区，全部条件满足后将任务状态改为 `awaiting_review`。失败或阻塞不得写成完成；不得填写 Codex 验收结论。

## 验证方法

以下命令均在 `/home/mye/src/llm/KMesh` 执行，无需 activate；每条独立执行并记录退出状态。只有解释器／依赖及现有环境检查通过后才安装。安装需要的源码文件由上面步骤创建。

```bash
git rev-parse HEAD
git status --short
timeout 60s /opt/anaconda3/bin/python3 -c 'import sys, torch, numpy, yaml, pytest; from importlib.metadata import version; print(sys.executable, sys.version); print({n: version(n) for n in ("torch", "numpy", "PyYAML", "pytest", "pip", "setuptools", "wheel")})'
timeout 120s /opt/anaconda3/bin/python3 -m venv --system-site-packages .venv
timeout 120s .venv/bin/python -m pip install --no-index --no-build-isolation --no-deps -e '.[dev]'
timeout 60s .venv/bin/python -c 'from pathlib import Path; import kmesh; p = Path(kmesh.__file__).resolve(); print(p); assert p == Path("src/kmesh/__init__.py").resolve()'
timeout 60s .venv/bin/python -m kmesh.cli --help
timeout 60s .venv/bin/kmesh --help
timeout 60s .venv/bin/python -m kmesh.cli doctor --help
timeout 60s .venv/bin/python -m kmesh.cli doctor --out reports/environment.json
timeout 60s .venv/bin/kmesh doctor --out reports/T0001/environment-console.json
CUDA_VISIBLE_DEVICES="" timeout 60s .venv/bin/python -m kmesh.cli doctor --out reports/T0001/environment-cpu.json
timeout 60s .venv/bin/python - <<'PY'
import json
from pathlib import Path
paths = ["reports/environment.json", "reports/T0001/environment-console.json", "reports/T0001/environment-cpu.json"]
reports = [json.loads(Path(p).read_text(encoding="utf-8")) for p in paths]
assert all(r["schema_version"] == 1 and r["errors"] == [] for r in reports)
assert reports[0]["status"] in {"ok", "cpu_only"}
stable = lambda r: {k: v for k, v in r.items() if k != "generated_at_utc"}
assert stable(reports[0]) == stable(reports[1])
cpu = reports[2]
assert cpu["status"] == "cpu_only" and cpu["cuda"]["available"] is False
assert cpu["cuda"]["device_count"] == 0 and cpu["cuda"]["devices"] == []
print("PASS: reports readable, entrypoints agree, CPU fallback explicit")
PY
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 timeout 120s .venv/bin/python -m pytest -q tests/test_doctor.py
timeout 60s .venv/bin/python -m pip list --format=json > reports/T0001/installed-packages.json
timeout 60s .venv/bin/python -c 'import torch, numpy, yaml; print({m.__name__: m.__file__ for m in (torch, numpy, yaml)})'
sha256sum reports/environment.json reports/T0001/environment-console.json reports/T0001/environment-cpu.json reports/T0001/installed-packages.json
git diff --check
```

- 上述命令应退出 0。前两份真实 doctor 报告允许 `ok` 或 `cpu_only`；两入口的稳定字段应一致，比较时忽略生成时间。任何 `error` 说明当前环境尚未满足本任务验收，保留报告、记录阻塞；不能把符合错误处理契约等同于环境已经可用。
- 通过 `CUDA_VISIBLE_DEVICES=""` 启动的是新进程，应得到 `cpu_only`、available=false、count=0、devices=[]。不更改全局 GPU 设置；这一结果只验证 CPU 降级路径。
- 仔细核对真实报告中的 Python 路径和依赖版本；以执行时实际环境为准，环境若较规划发生变化，记录原因，不硬编码覆盖。标准库 `json` 读回三份报告并核对 schema、类型和上述状态；该项结果记入执行记录。
- 参数缺失／未知命令的退出 2、诊断错误和 I/O 失败的退出 1 由上述单测验证，不作为本节成功命令的例外。没有固定测试数量门槛，但必须对应步骤 4 的各项行为。
- 合成 fixture 无随机采样，seed=N/A。测试输出必须包含真实通过／失败数量；已有全局 pytest 插件不得自动加载。不得以 GPU 缺失跳过 CPU 及合成 GPU 测试。
- `git diff --check` 不覆盖未跟踪新文件，另检查本任务所有新文件的末尾换行、尾随空白，以及 README／状态文档的本地链接。不得为检查而暂存无关文件。
- 不运行计划中的 data/train/evaluate、smoke、profile 或正式矩阵；这些命令尚未实现。

## 验收标准

- [ ] A1：可编辑安装真实成功；导入来自本仓库；模块与控制台入口均可用，没有依赖 PYTHONPATH 或未声明的新库。
- [ ] A2：采集函数满足全部字段与状态契约；报告为运行时采集，未把 CUDA 构建版本或可用性探测当作训练能力证明。
- [ ] A3：依赖缺失、导入／设备探测异常与 CPU 降级可区分；未知信息为 null，错误附原因，CLI 退出码正确。
- [ ] A4：help 无环境采集副作用；参数和 I/O 失败明确；三份真实报告可读回，两入口稳定字段一致，强制 CPU 报告符合预期。
- [ ] A5：步骤 4 的边界测试在隔离插件、无真实 GPU 依赖的条件下通过；已审查 imports／fixtures，没有越界数据访问。
- [ ] A6：真实命令、退出码、日志、包版本快照、已知来源与未知项、报告 hash 完整可追溯；无虚构结果或覆盖失败证据。
- [ ] A7：README 与状态文档对应实际实现，准确列出 M0 未完成项；没有模型、数据或训练占位实现，没有扩大研究／资源范围。
- [ ] A8：改动仅限授权路径，文档／diff 基础检查通过；Pi 已记录实际工具和模型并交回 `awaiting_review`，最终接受由 Codex 根据实际 diff 和独立核验决定。

Codex 验收时冻结上述 diff，先审阅实现与测试 fixture，再独立重跑 editable import、help、真实 doctor、强制 CPU 路径及本任务单测，并核对报告和来源记录。实际 GPU 不可用不妨碍本任务通过；环境依赖损坏、诊断 error 或证据缺失则不能通过。T0001 接受后才据实拆分下一项 M0 工作，不预先把尚未编号的后续任务视为可执行。

## Pi 执行记录

- 轮次 1，2026-09-13；实际工具／模型：Pi + `qwen3.8-coding:27b`（ollama `qwen3.8-coding:27b-q8_0-64k`，`PI_REASONING_LEVEL=off`）。执行前已核对基线与依赖版本，满足前提后改为 `in_progress`。
- 实际基线与改动文件：执行时 HEAD `69984c2e99ff73cbb43de9e1e440d2b8379a9fd7`（交接文档基线 `8d41ad6` 之后仅有 README 文案提交，代码基线未变）；执行前工作树仅本交接文档未跟踪。为任务单独新建分支 `T0001-bootstrap-doctor`。改动仅限授权路径：新增 `pyproject.toml`、`src/kmesh/__init__.py`、`src/kmesh/utils/__init__.py`、`src/kmesh/cli.py`、`src/kmesh/utils/environment.py`、`tests/test_doctor.py`、`docs/implementation_status.md`，修改 `README.md`（追加“安装与诊断”一节并更新状态段）；另有自动产物 `.venv/`、`src/kmesh.egg-info/`、`__pycache__/`、`.pytest_cache/`（均被 .gitignore 忽略）。未修改研究计划、AGENTS.md、模板。（提交记录见本执行记录末项）
- 命令、退出状态、耗时、关键结果及日志路径：全部按“验证方法”一节顺序独立执行，均记录于 `reports/T0001/run-log.md`（含首轮 pytest `14 passed, 2 failed` 的失败摘要与修复后 `16 passed` 复跑）。要点：venv 创建 EXIT=0（3s，`--system-site-packages`，此前不存在）；editable 安装 EXIT=0（3s，`--no-index --no-build-isolation --no-deps -e .[dev]`）；导入路径断言指向本仓库 `src/kmesh/__init__.py`；三个 help 均 EXIT=0；三份 doctor 报告 EXIT=0（真实环境 1×RTX 3090，前两份 `status=ok`，`CUDA_VISIBLE_DEVICES=""` 子进程 `status=cpu_only`、available=false、count=0、devices=[]；均 2s）；交叉核对脚本打印 PASS 且 EXIT=0；pytest 最终 EXIT=0（16 passed，1s，插件已隔离）；`pip list` 快照、导入路径查询、`sha256sum`、`git diff --check` 均 EXIT=0。
- 未运行项与原因：无本轮应跑而未跑项。计划中 data/train/evaluate、smoke、profile 等不属于本任务，`not_run`（尚未实现）。
- 产物路径、版本／SHA-256：`reports/environment.json`（`a0639fe3...212b91`）、`reports/T0001/environment-console.json`（`8b1ce381...fcc1b9`）、`reports/T0001/environment-cpu.json`（`a8271ceb...61683d`）、`reports/T0001/installed-packages.json`（`8300a475...4841`），完整 SHA-256 及来源说明见 `reports/T0001/provenance.md`。
- 偏差、失败、阻塞及最小复现：无阻塞。两点如实记录：(1) 规划时未确认 GPU 可用性，实际执行环境含 1×NVIDIA GeForce RTX 3090（24 GB），两份真实报告为 `ok` 而非 `cpu_only`，符合契约允许范围（前两份允许 `ok` 或 `cpu_only`）；(2) 首轮 pytest 有 2 个失败，均为实现/测试自身缺陷（`main([])` 空参数时 cli 取 `argv[0]` 越界；一个测试函数签名漏 `monkeypatch` 参数），已最小修复并复跑通过，失败未覆盖、原始结果保留在日志。
- 提交验收的 diff／产物范围与状态：上述全部改动文件与 `reports/` 产物，分支 `T0001-bootstrap-doctor`，状态改为 `awaiting_review`。按用户明确授权，已于 2026-09-13 将全部改动提交为本分支单一 commit（未 push）；验收期间如需冻结 diff，以该 commit 为准。验收区由 Codex 填写，本区不代写。

## Codex 验收记录

本区只记录 Pi 实施结果的验收；交接文档检查不算实施验收。

- 轮次、日期、实际模型／推理强度：`not_run`。
- 核验的基线、差异与产物版本：`not_run`。
- 独立检查／复跑命令、退出状态及结果：`not_run`。
- A1–A8 逐项结论与证据：`not_run`。
- 具体问题、返工要求或剩余限制：`not_run`。
- 最终状态：`not_run`，尚未接受实施结果。
- 后续依赖或拆分任务编号：N/A，待 T0001 验收后安排。

## 实施参考

- [Python venv 文档](https://docs.python.org/3/library/venv.html)：继承系统 site-packages 及通过完整解释器路径使用环境。
- [setuptools quickstart](https://setuptools.pypa.io/en/latest/userguide/quickstart.html)：pyproject.toml、包发现和入口声明；本任务使用本地已安装版本支持的基础功能。
- PyTorch 2.10：[CUDA 可用性](https://docs.pytorch.org/docs/2.10/generated/torch.cuda.is_available.html)、[设备属性](https://docs.pytorch.org/docs/2.10/generated/torch.cuda.get_device_properties.html)。使用与已安装 PyTorch 对应的接口，不从文档示例猜测本机 GPU。
