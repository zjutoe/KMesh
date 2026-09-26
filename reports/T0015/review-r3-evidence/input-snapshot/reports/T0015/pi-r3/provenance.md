# T0015 R3 provenance（唯一执行说明，仅证据收尾）

- 日期：2026-09-25（Pi，UTC）。R3 仅证据收尾（E1/E2）；产品 `8c6c4392…`、测试 `955ca72a…` 自此冻结，不重跑 pytest/full/guards/doctor/GPU，不回切产品、不补造历史。
- 实际执行者／模型归属：Pi；旧文字自述 qwen3.8-coding-27b，授权为 bonsai2-27b，现有录制器不独立采集模型；用户当前确认继续 Bonsai 不能证明历史会话的实际模型。归属保持 unknown，不用当前授权替代历史证据。

## E1 恢复隐藏证据可见性

- 两份额外证据目录 `pi-r1-r2full`／`pi-r1-r2guards` 的 `.gitignore` 原模式隐藏 26 个非临时文件（full 4 项：.gitignore/record.json/stdout.txt/stderr.txt；guards 22 项：.gitignore/guards.json＋五个副本各 4 项）。原模式保留，仅在其末尾按原行顺序追加每条 `!原模式`（如 `.gitignore`→`!.gitignore`、`submitted/`→`!submitted/`），父级 `pytest-tmp/`、`__pycache__/` 排除不变。26 项字节未改。此操作是明确授权的归档范围纠正，不把此前越界改称合规；不删除／移动目录，不用强制暂存掩盖规则，不补造缺失 record。

## E2 时序与来源更正

1. 当前版本已有两份 934 项 full：`pi-r1-r2full`（14:21:52）与 `pi-r2-full`（14:32:18），均为最终 R2 两个 hash。撤回"R2 full 仅一次"；遗漏的 `pi-r1-r2full` 列入本次证据，不凭名称当作首轮旧实现。
2. `pi-r2-regression`（14:31:24）在旧产品字节（R1 `2127c103…`）上真实复现子类例失败（16 过），但其前已有当前修复版通过 full；不能称已证明"首次修复前先失败"。实际版本序列为 R2→R1→R2；切换方式／操作者未记录时保持 unknown。
3. 未找到 R2 preflight 原件，不能称规定的编码前核对已录制完成。无原件的历史标记保持 unknown/not_recorded；不回切版本补跑冒充历史的 prefill。
4. `pi-r1-r2guards` 有可核验的内部结果（guards.json、五个副本），但没有外层 record/stdout/stderr；其启动时间、外层命令退出码、执行环境不能补写为已录制事实。保留"完整外层录制"与"仅内部产物"两类。
5. R2 provenance 及提交前 README／状态的"独立 17 项"来源不成立：Pi 的 17 项是自检；本报告的 17 项才是本轮独立复验；二者时间与来源分开。本轮已核验 Pi 934，不等于 Codex 重跑 934。
6. 原规划冻结清单 3088 项，R2 冻结清单 3167 项；不要把 3167 称作原规划数。模型归属仍 unknown（授权 bonsai2-27b，旧文字自述 Qwen）。

## 来源说明

- 已完成且有外层 record 的 Pi 目录共 13 个（R1 七个＋本轮六个），另加无外层 record 的 `pi-r1-r2guards`。完整列表由 docs 检查自动索引，不在多处手抄计数／时间表。
- 两份 934 full 原件已核验；旧源码与历史冻结材料未变；本说明不重造历史，缺失保持 unknown/not_recorded。
