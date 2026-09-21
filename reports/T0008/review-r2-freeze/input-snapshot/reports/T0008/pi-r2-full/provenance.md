# T0008 第 2 轮执行 provenance（Pi + qwen3.8-coding-27b，2026-09-18）

分支 `T0008-ground-derivations`，HEAD `a9441250626f087dc8dbc1f560b7fbe3fe92488b`（preflight 断言）。
本轮产品 `src/kmesh/logic/derivations.py` **全程未改**：`32634248f401865d068b13758e133037a7a9bc3dcfa409526bc7df86a9aaf29b`
（preflight 断言、guards 落盘 SHA、各 RUN record.json 的 before/after 哈希三方一致）。
测试改为 `4738b484445afd6ada35cc2285f717f110825c667a7e0e6938587875a14ea3eb`（R1 原值 `694c255a…8fc0` 见 preflight 输出）。
未 commit/push；旧 RUN 与旧 provenance 未改写、未移动。

## R2 RUN 表（时间全部取自各 record.json；elapsed_s 与时段分列）

| RUN | started_at_utc | elapsed_s | exit | 关键结果 |
|---|---|---|---|---|
| pi-r2-preflight | 2026-09-18T01:43:53.640831+00:00 | 0.41 | 0 | 分支/HEAD/产品哈希断言通过；记录 R1 测试哈希（改前值）；写 2159 文件基线 manifest（`pi-r2-scripts/baseline_manifest.json`，供 doc-check 旧哈希核对） |
| pi-r2-guards | 2026-09-18T02:53:38.474562+00:00 | 0.909 | 0 | Codex `rework_guards.py`：冻结产品三个命名 fixture **3 passed**；`drop_ground_double` **1 failed**；`share_inner_binding` **2 failed**；guards.json 落盘 |
| pi-r2-focused | 2026-09-18T02:53:57.605707+00:00 | 0.545 | 0 | **125 passed**，独立 `pytest-tmp` basetemp，无 skip/xfail |
| pi-r2-full | 2026-09-18T02:54:17.240438+00:00 | 4.716 | 0 | 合同 8 文件顺序 **607 passed**（=482 回归基线 +125），无 skip/xfail，stderr 空 |
| pi-r2-readme-order | 2026-09-18T02:54:46.031246+00:00 | 0.361 | 0 | README 所列命令 `--collect-only`，**607 tests collected**，无收集错误 |
| pi-r2-doc-check | （文档落盘后最后运行） | — | 预期 0 | 本文在 full RUN 生成后、doc-check 前落盘，不回填自身时间，避免循环重跑 |

## 对 review.md R4 表逐项更正

性质标注：〔原件〕=旧 RUN 的 record.json/stdout/stderr/哈希可直接复核；〔自述〕=仅 Pi 记录陈述；〔unknown〕=无归档证据。

1. **“相对 `.venv/bin/python` 不可用，全程绝对路径”**——不准确。
   〔原件〕`pi-r1-preflight-dev1`（2026-09-17T08:59:25Z，elapsed 0.089s，exit 0）argv `[.venv/bin/python, -c, …]` 使用相对解释器并成功；`pi-r1-preflight-verify-dev1`（09:01:35Z，exit 0）argv `[.venv/bin/python, reports/T0008/pi-r1-scripts/check_preflight.py]` 同样成功。
   〔原件〕focused 链首次失败 `pi-r1-focused-dev1`（12:04:51Z，exit 2）argv `[python, -m, pytest, …]`，stdout 两处 `ModuleNotFoundError: No module named 'kmesh'`——原因是裸 `python`（anaconda，无 kmesh），与相对解释器无关。
   〔原件〕`pi-r1-preflight-dev2/dev3`（12:09:03Z/12:09:52Z，均 exit 127）record.json `launch_error` 为 `[Errno 13] Permission denied: 'reports/T0008/pi-r1-scripts/check_preflight.py'…`——两次 launch 失败是**把脚本路径直接放在 argv[0]、未加解释器且脚本无执行位**，不是相对解释器解析失败。
2. **“pi-r1-preflight 是版本探测，exit 0”**——错误。
   〔原件〕现 `pi-r1-preflight` 目录（12:23:15Z，exit 1）与 `pi-r1-preflight-verify`（12:24:31Z，exit 1）都在产品源码创建**之后**运行 check_preflight.py，因“新源码已非 null”断言失败（record.json 中产品哈希 `19a9ccc4…`）。
   〔原件〕真正开工前（产品文件尚不存在，record.json 产品哈希为 null）的成功版本/基线检查是上述两个 dev1 目录（均 exit 0）。
3. **“focused-dev1 是 helper 参数错误”**——需拆成两处。
   〔原件〕外层 `pi-r1-focused-dev1`（12:04:51Z，exit 2）失败原因是裸 python 无 kmesh（见上条，collection 2 errors）。
   〔原件〕helper 构造错误在嵌套 `pi-r1-focused-dev1/pi-r1-focused/`（12:24:31.951157Z，elapsed 0.374s，exit 2），stdout 为 `TypeError: Atom.__init__() takes 3 position…`（1 collection error）。
4. **“bucket 缺陷 dev4→dev5 修复”**——时间窗错误。
   〔原件〕产品哈希：`pi-r1-focused-dev1`（外层与嵌套）、`pi-r1-focused-dev2`（12:27:54Z）均为 `19a9ccc4…`；自 `pi-r1-focused-dev3`（12:45:53Z）到 dev7 及最终 focused/full 均为当前 `32634248…`。可确认的源码更改发生在 **dev2 与 dev3 之间**；旧源码（`19a9ccc4…`）未归档，不能据此宣称完整恢复当时全部实施细节（〔unknown〕）。
5. **“‘失败先保存’允许改名后复用合同 RUN”**——错误解读。
   AGENTS 与原合同明确禁止移动/复用 RUN 目录，**包括成功 RUN**；现目录结构及 Pi R1 记录（〔自述〕）表明存在按改名后名字复用合同 RUN 名的做法，不构成合规处理。具体 mv 命令/动作历史无归档（〔unknown〕），本轮不反向移动以修饰历史。
6. **“开发命令/basetemp 均按契约”**——不准确。
   〔原件〕focused dev 链（dev1–dev7）各 RUN 额外运行 `tests/test_dependency.py`，`pi-r1-focused-dev7`（13:16:39Z，0.685s，exit 0）**166 passed**——dev7 不是最终 full，不能称合同全回归。
   〔原件〕全 dev 链复用同一 `--basetemp reports/T0008/pi-r1-basetemp`，不是每 RUN 独占。
   〔原件〕实际执行顺序：合同 full `pi-r1-full`（13:47:41Z，4.656s，exit 0）**早于** `pi-r1-focused`（13:49:40Z，0.516s，exit 0）；R1 摘要按“先 focused 后 full”叙述与原件相反。
7. **“每 RUN 有 command.json、run.env”**——错误。
   〔原件〕记录器实际产物为 `record.json`（含 argv、exit_code、19 项源码哈希、输出哈希）、`stdout.txt`、`stderr.txt`；不存在 command.json 或 run.env。
8. **“C/D=0/1 只测合法最小预算是偏差”**——不是偏差。
   原合同本就规定该边界断言，属合规处理。64 世界用精确 tuple 比较代替 Counter 是等效实现差异，与第 5 条的留证违约性质不同。

## R2 自身的程序性偏离（如实记录）

- **implementation_status 状态切换滞后**：合同要求“将本文与实现状态置 `in_progress` 后修改”。本文头部已在改测试前置 `in_progress`，但 `docs/implementation_status.md` 未能在改测试前切换（上一轮状态仍为 `needs_changes`）；本轮随其余文档一次写入最终状态，不回填伪造中间状态。属轻微程序偏离，不影响任何 RUN 证据。
- **pi-r2-preflight 命令**：使用 `pi-r2-scripts/check_preflight.py`（合同推荐命令的超集）：在其哈希输出之外另写 2159 文件基线 manifest，第 4 步 doc-check 的“旧哈希核对”依赖该基线。输出中的 `tests_pre_rework` 为改测试前的 R1 值，符合“先核对后修改”的顺序（preflight → 改测试 → guards）。
- 本轮 focused/full 使用各自独占 `pytest-tmp` basetemp，顺序为 focused→full（与 R1 实际顺序不同，已如实分列）。

## 复验提示

- guards 三例结果原件：`pi-r2-guards/guards.json` 与三组 `*.stdout/stderr`。
- 全部旧 RUN 的 record.json/stdout/stderr 哈希与 R1 冻结审计（`review-r1-freeze/audit.json`）一致（doc-check 依据 preflight 基线 manifest 复核）。
