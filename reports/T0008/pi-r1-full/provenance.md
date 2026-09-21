# T0008 Pi 第 1 轮 full RUN provenance

- 记录者：Pi + `qwen3.8-coding:27b-q8_0-64k`（ollama），2026-09-17。
- 分支／基线：`T0008-ground-derivations` @ `a9441250626f087dc8dbc1f560b7fbe3fe92488b`（T0007 接受提交，仅存在于 `origin/T0007-relation-dag`；本地／远端 master 仍为 `74a96f3735831d16a14dedffbaa6e0654f8b7658`，本基线不在其上，按交接要求从 T0007 基线开工）；本 RUN 时工作树含 Codex 交接改动（未提交）与本轮新增文件；未 commit/push。
- 环境：解释器 `/home/mye/src/llm/KMesh/.venv/bin/python`（Python 3.13.9），editable `kmesh 0.1.0`，`pytest 8.4.2`；记录器固定 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`CUDA_VISIBLE_DEVICES=""`、120 秒时限。
- 偏差：契约命令的相对解释器路径在本机 shell=False 下不可解析，全程以同文件绝对路径执行（见交接执行记录偏差 1）。

## 合同 RUN

| RUN | 命令（`<py>` = `/home/mye/src/llm/KMesh/.venv/bin/python`） | 退出码 | 结果 |
|---|---|---|---|
| `pi-r1-preflight` | `record_check.py pi-r1-preflight -- <py> -c '<版本探测>'` | 0 | 解释器/版本/包路径正确 |
| `pi-r1-focused` | `record_check.py pi-r1-focused -- <py> -m pytest -q tests/test_derivations.py --basetemp reports/T0008/pi-r1-focused/pytest-tmp` | 0 | **122 passed**（无 skip/xfail） |
| `pi-r1-full` | `record_check.py pi-r1-full -- <py> -m pytest -q tests/test_derivations.py tests/test_dependency.py tests/test_proof.py tests/test_engine.py tests/test_reference_engine.py tests/test_logic_types.py tests/test_config.py tests/test_doctor.py --basetemp reports/T0008/pi-r1-full/pytest-tmp` | 0 | **604 passed** = 122 新 + 482 原（无 skip/xfail） |
| `pi-r1-diff-check` | `record_check.py pi-r1-diff-check -- git diff --check` | 0 | 无空白/冲突标记 |
| `pi-r1-doc-check` | `record_check.py pi-r1-doc-check -- <py> reports/T0008/pi-r1-scripts/check_docs.py` | 0* | T0008 交接/README/实现状态/本 provenance 的本地链接、末尾换行、行尾空白；*本文件在 doc-check 前定稿 |

失败先保存的开发链：`pi-r1-focused-dev1`（原合同名下的收集错误，重命名留证）与 `dev2`–`dev7`、`pi-r1-preflight-dev1/2/3`、`pi-r1-preflight-verify-dev1`；全部未覆盖。成功 RUN 不重复占用。

## 关键哈希（sha256）

- 产品：`src/kmesh/logic/derivations.py` `32634248f401865d068b13758e133037a7a9bc3dcfa409526bc7df86a9aaf29b`
- 测试：`tests/test_derivations.py` `694c255ad5251ac1813b07ec335787b96a14e33b020a6aaaf865ac081c338fc0`
- 记录器（原样使用）：`reports/T0008/record_check.py` `ab6ff5a2f20fc8c20f82288fdc4e26ca08d72d7806cdbd1db8c2dd23286a07d1`
- 文档：`README.md` `98e735c0…ab1e90`、`docs/implementation_status.md` `e4ce0986…4a6f5`、`docs/handoffs/T0008-ground-derivations.md` `ddd720b8…97d22`、`docs/decisions.md` `0d5bd5c1…0da73`、`docs/handoffs/T0007-relation-dag.md` `230cb878…3d49d`、`reports/T0008/pi-r1-scripts/check_docs.py` `e5ff90bd…2f36a`
- 冻结核对（前后哈希一致，均未改）：`dependency.py` `4b01df6f…2ca3f`、`test_dependency.py` `722869ef…6313`（T0007 接受值）、`types.py` `b8468612…37f8`、`proof.py` `008bdd36…3daa`、`test_proof.py` `68fef57a…7e35`、`engine.py` `21c4694f…4eb7`、`reference_engine.py` `54ff628a…b42d`、`logic/__init__.py` `649c92a6…fa96`。

## 边界事实

- full 回归 604 项无 skip/xfail；focused 122 项含 1200 条长链、64 微世界×2 求解器结论集对照、预算精确边界、导入隔离（5 个阻塞根）。
- git diff 范围（tracked）：`README.md`、`docs/decisions.md`、`docs/handoffs/T0007-relation-dag.md`、`docs/implementation_status.md`；新增 untracked：产品、测试、T0008 交接、`reports/T0008/`。冻结模块零修改。
- 无外部数据、网络、模型、训练或 GPU；无 `not_run`；未 commit/push。
