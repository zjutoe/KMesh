# T0006 R1 证据与来源（provenance）

- 任务／轮次：T0006 / R1（修订 r1），2026-09-16（UTC）。
- 执行：Pi harness + 别名 `qwen3.8-max-preview`（实际完整名 `qwen3.8-coding:27b-q8_0-64k`，ollama）。规划/验收：Codex + `gpt-6-astra`（xhigh）。
- 基线：分支 `T0006-proof-verifier`，HEAD `6dcaae2ef40459e80ed5919e658db84986526211`（= T0005 验收合并 master）。
- 解释器：`/home/mye/src/llm/KMesh/.venv/bin/python`，Python 3.13.9（Anaconda 打包，x86_64，Linux 6.8.0-111-generic），editable `kmesh==0.1.0`，`pytest==8.4.2`。无 torch；`kmesh.logic` 全链路零导入。
- 记录器：本任务目录内副本 `reports/T0006/record_check.py`（未修改；每个 RUN 目录含 `record.json`、`stdout.txt`、`stderr.txt`，`record.json.exit_code` 与两路原始输出一致，失败 RUN 全部保留）。

## RUN 清单

| RUN | 命令（节选） | exit | 结果 |
|---|---|---:|---|
| `pi-r1-preflight` | 交接规定前置检查 | 0 | Python/包/pytest 版本；⚠ 命令嵌套引号截断，git 段未入证据（见偏差 ①） |
| `pi-r1-preflight-r2` | 同上（修复引号） | 0 | 完整前置检查含 branch/status 快照 |
| `pi-r1-dev-syntax` | `py_compile` 两交付文件 | 0 | 两文件语法通过 |
| `pi-r1-focused` | `pytest tests/test_proof.py -q` | 1 | 52 passed / 33 failed（fixture 首版错误，失败先留存） |
| `pi-r1-focused-r2` | 同上 | 1 | 79 passed / 6 failed（第一轮 fixture 修复后） |
| `pi-r1-focused-r3` | 同上 | 1 | 84 passed / 1 failed（残留期望表键缺失） |
| `pi-r1-focused-r4` | 同上 | 0 | **85 passed**（focused 全绿） |
| `pi-r1-full` | `pytest tests/ -q` | 0 | **422 passed**（既有 337 + 新增 85，无 skip/xfail） |
| `pi-r1-diff-check` / `-r2` | `git diff --check` | 0 / 0 | 无空白错误（r2 在全部文档编辑后收口） |
| `pi-r1-mutation-set`（-r1..-r3） | `python reports/T0006/mutation_set_check.py` | 1 / 1 / 1 | 前三轮失败均为检查脚本自身期望缺陷（未 track 交付物误入冻结清单、`-u` 展开未聚合、T0006 交接行 M/?? 误判），非仓库异常；失败证据保留 |
| `pi-r1-mutation-set-r4` | 同上 | 0 | 交付哈希、冻结 blob、变更集精确匹配、换行/尾随空白、链接全部通过 |

失败→修复→通过链：`pi-r1-focused`（33 失败）→ 修复 fixture（二元原子、步骤索引、诊断片段）→ `pi-r1-focused-r2`（6）→ `pi-r1-focused-r3`（1）→ `pi-r1-focused-r4`（0）→ `pi-r1-full`（0）。修复仅限 `tests/test_proof.py` 与（一次）诊断期望措辞；`proof.py` 自 `pi-r1-dev-syntax` 后未再改动（R1 冻结哈希 `008bdd36…` 覆盖最终版）。

## 冻结与变更

- 冻结（哈希核对，见 `mutation_set_check.py`）：T0001–T0004 产品/测试/交接 blob、`logic/__init__.py`（`649c92a6…`）。T0005 交接文档由 Codex 在执行期间做过验收更正外部改动，不在本任务变更内。
- 本任务交付：`src/kmesh/logic/proof.py`（`008bdd36…`）、`tests/test_proof.py`（`857dd21d…`）、`README.md` T0006 小节与当前限制、`docs/implementation_status.md` 状态行、本交接文档执行记录、`reports/T0006/`。
- 外部 worktree 改动（Codex，执行期间、非本任务）：研究计划 v0.1.1→v0.1.2（E1 `e1_v3` 等）、`docs/decisions.md` 新增 D21–D24、T0005 交接文档验收更正、新增 `KMesh_Paper_Framework_v0.1.md`。本任务未触碰这些文件；D21 文字与 T0006 交接契约一致。

## 偏差（如实）

1. `pi-r1-preflight` 因外层 shell 嵌套引号截断，git 段未进入证据；`pi-r1-preflight-r2` 已补齐，两者均保留。
2. 本轮 focused/full RUN 实际未附交接命令中的 `--basetemp`（pytest 临时目录落在默认位置）；不影响测试内容与退出码，后续记录器 RUN 不再重跑同一范围。
3. focused 首失败前的一次 `-c` 单行开发探针未走记录器；同等断言已由正式 RUN 覆盖。
4. README 最小例未单独再走 RUN（与 focused A5 主例同构且断言相同）。
5. 首轮 focused 前误用记录器 CLI（`RUN` 与命令间缺 `--`，exit 2 未执行命令），已纠正为 `RUN -- COMMAND`。
6. mutation-set 检查脚本前三轮期望缺陷（见上表），r4 通过；`reports/T0006/.gitignore` 仅排除 `*/pytest-tmp/`，不排除证据。
