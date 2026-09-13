# T0001 版本与来源说明（provenance）

记录时间：2026-09-13（UTC，实际为 2026-09-13T13:56–13:59Z 左右执行）。

## 基线

- 交接文档代码基线：`8d41ad631441bab9dd92af26ac99b6544e664e2d`。
- 实际执行时 HEAD：`69984c2e99ff73cbb43de9e1e440d2b8379a9fd7`（`8d41ad6` 之后仅新增提交 `69984c2 README`，即 README 文案更新，不影响代码基线语义）。
- 执行分支：`T0001-bootstrap-doctor`（为任务单独新建，从 `69984c2` 切出）。
- 执行前工作树只有未跟踪交接文档 `docs/handoffs/T0001-bootstrap-doctor.md`，无其他已有改动。

## 实际 diff 范围（均为本任务新增/修改）

- 新增：`pyproject.toml`、`src/kmesh/__init__.py`、`src/kmesh/utils/__init__.py`、`src/kmesh/cli.py`、`src/kmesh/utils/environment.py`、`tests/test_doctor.py`、`docs/implementation_status.md`、`reports/environment.json`、`reports/T0001/`（本目录）。
- 修改：`README.md`（追加“安装与诊断”一节并更新实施状态段）。
- 未修改：研究计划、AGENTS.md、交接模板及其他既有文件。
- 提交：按用户明确授权，全部改动已提交为本分支单一 commit（未 push）。

## 解释器与虚拟环境

- 基础解释器：`/opt/anaconda3/bin/python3`，Python `3.13.9 | packaged by Anaconda, Inc.`。
- 虚拟环境：`/home/mye/src/llm/KMesh/.venv`，由
  `/opt/anaconda3/bin/python3 -m venv --system-site-packages .venv` 新建（此前不存在）。
- **继承系统包**：`pyvenv.cfg` 中 `include-system-site-packages = true`，torch/numpy/yaml 等直接来自 `/opt/anaconda3` 全局环境，未隔离、未锁定。
- 注意：venv 自带 pip `25.2`，而全局 pip 为 `25.3`；报告中的 `packages.pip` 取自当前解释器（venv）的元数据，两者差异属预期。

## 安装命令与来源

```
.venv/bin/python -m pip install --no-index --no-build-isolation --no-deps -e '.[dev]'
```

- `--no-index`：不访问网络，`kmesh` 本身在本机构建为 editable wheel 并安装；`[dev]` extra 的 pytest 未安装（`--no-deps` + 系统已有）。
- 除 kmesh 外**未安装、升级、卸载任何依赖**；全部运行依赖复用全局 conda 环境既有版本，因此没有完整依赖锁，本轮安装来源是本地既有环境，原始下载渠道 `unknown`（未在线查询）。

## torch / numpy / yaml 实际导入路径

`/opt/anaconda3/lib/python3.13/site-packages/`：

| 模块 | 导入路径 |
|---|---|
| torch | `/opt/anaconda3/lib/python3.13/site-packages/torch/__init__.py` |
| numpy | `/opt/anaconda3/lib/python3.13/site-packages/numpy/__init__.py` |
| yaml | `/opt/anaconda3/lib/python3.13/site-packages/yaml/__init__.py` |

## 报告与依赖快照 SHA-256

| 文件 | SHA-256 |
|---|---|
| `reports/environment.json` | `a0639fe3d530d68c13491ef85d61669021f0599b825649530b86b34afa212b91` |
| `reports/T0001/environment-console.json` | `8b1ce381c609f8b1a1a402275cf9666da5a5cf1e1836c7878f1dc60bdbfcc1b9` |
| `reports/T0001/environment-cpu.json` | `a8271ceb712cb807e7d2db1aeddac26f863aa254ff55d2243619d1d7f641683d` |
| `reports/T0001/installed-packages.json` | `8300a47582adb207ca7cbb0dc425430ceaf4ddb5afcc6b1cd384efa090cfd841` |

## 旧报告保留

执行前 `reports/environment.json` 不存在，无需保留旧文件。

## 已知未知项

- 各依赖的原始发布/下载渠道：`unknown`（未联网核验）。
- CUDA 驱动版本、CPU/主存详细盘点、RNG/kernel 元数据：不属于本任务契约，`not_run`。
- GPU 仅通过 `torch.cuda` 属性查询，未做 forward/backward 验证，不声称可稳定训练。
