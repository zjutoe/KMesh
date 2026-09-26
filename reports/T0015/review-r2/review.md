# T0015 第 2 轮 Codex 验收：needs_changes（仅证据收尾）

2026-09-25；HEAD `f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41`，分支 `T0015-proof-subtree`。
本任务按原手工交接流程审查，不调用 Codinator；未修改产品／测试，不 commit/push。

**产品与测试修复通过；任务尚未 accepted。** 剩余阻塞为 E1 证据可见性和 E2 记录准确性。
下一轮不再修改产品／测试，也不重跑 focused、full、guards、doctor 或 GPU。

## 已关闭的产品与测试问题

- 产品 SHA-256：`8c6c439269961f5de53c760b6d38660effd5dfade5804154b1d2543f6cf9fe6c`。
- 测试 SHA-256：`955ca72abf90b0574afcd75b7ccc0bfe3a3c0a114c063534b5cc24d7440c3bce`。
- [独立定向](../review-r2-focused/stdout.txt)：17 passed，stderr 空。
- [独立错误副本检查](../review-r2-guards/guards.json)：submitted 通过；长链引用损坏、重复委托、消费 generator、违规导入四个副本均被指定测试拒绝。
- [独立产品探针](../review-r2-probe/result.json)：与 R1 相比恰好三处规定替换；普通／必填 note 子类的五根共10例、world反转五根共5例通过，完整输出经 T0006 验证。输入结构副本及实际 hash 不变。测试恰好九个旧函数局部变化、增加一个子类回归；隔离字符串的空 `__path__` 已核对。
- Pi 的两份934项 full 均与本次源码／测试一致、无 skip/xfail；旧源码与历史冻结材料未变。本轮不重复 full。

因此第1轮 R1 产品缺陷、R2 测试修补已关闭。不能因为下面的流程问题倒推代码错误，也不能把代码通过解释为全部证据合规。

## E1 · P2：额外证据被忽略规则排除

定位：[full/.gitignore](../pi-r1-r2full/.gitignore)、[guards/.gitignore](../pi-r1-r2guards/.gitignore)第1行起。
它们共隐藏 **26 个非临时文件**：full目录4个；guards目录22个（包括汇总、五个副本的结果／输出／源码）。
这两个目录不在 R2 冻结清单，也不属于获准新增的 `pi-r2*`。

[R2 checker](../check_rework_r2.py)第48行起只从 `git ls-files --cached --others --exclude-standard` 检查范围，
因此忽略文件没有进入范围检查；docs PASS 不能证明真实目录范围完整，也不能保证普通暂存会保留这些证据。
[完整审计](../review-r2-evidence/result.json)与[补充审计](../review-r2-evidence3/result.json)记录了原件哈希、忽略规则和可核验结果。
原始文件目前仍存在，不能写成“已经丢失”；本报告不推断添加规则的意图。

最小修复：保留目录名、record／stdout／stderr／guards／副本源码等原始字节。
只在上述两个 `.gitignore` 末尾，按原行顺序追加每条模式对应的 `!模式`，恢复所有26项的 Git 可见性。
原模式保留，`.gitignore` 自身也要变为可见；父级 `pytest-tmp/`、`__pycache__/` 排除不变。
此次是明确授权的归档范围纠正，不把此前越界改称合规。不得删除／移动目录、用强制暂存掩盖规则或补造缺失 record。

## E2 · P2：漏列时序及错误归属仍未更正

原件显示：

| 时间（UTC，2026-09-25） | 原件 | 产品／测试版本及结果 |
|---|---|---|
| 14:21:52.592063 | [pi-r1-r2full](../pi-r1-r2full/record.json) | 已是最终 R2 两个 hash，934 passed |
| 14:31:24.596029 | [pi-r2-regression](../pi-r2-regression/record.json) | R1 产品 `2127c103…`＋最终 R2 测试，子类例失败、16过 |
| 14:31:53.805110 | [pi-r2-focused](../pi-r2-focused/record.json) | 最终 R2 两个 hash，17 passed |
| 14:32:18.622221 | [pi-r2-full](../pi-r2-full/record.json) | 最终 R2 两个 hash，934 passed |

据此须在**新** `pi-r3/provenance.md` 追加以下更正，旧说明不改写：

1. 当前版本已有两份 full；撤回“R2 full仅一次”。遗漏的 `pi-r1-r2full` 也列入本次返工证据，不能仅凭名称把它当作首轮旧实现。
2. regression 是在旧产品字节上真实复现的失败，但之前已有当前修复版通过 full；不能称已证明“首次修复前先失败”。实际版本序列为 R2→R1→R2；切换方式／操作者未被记录时保持 unknown。
3. 未找到 R2 preflight 原件，不能称规定的编码前核对已录制完成。无原件的历史标记 unknown/not_recorded；不要现在回切版本补跑一个冒充过去的 preflight。
4. 额外 `pi-r1-r2guards` 有可核验的内部结果，但没有外层 record/stdout/stderr，其启动时间、外层命令退出码、执行环境不能补写为已录制事实。保留“完整外层录制”与“仅内部产物”两类。
5. [R2 provenance 第15/18行](../pi-r2/provenance.md)、提交前 README／状态里的“独立17项”来源不成立。Pi 17项是自检；**本报告的**17项才是此次独立复验，二者时间与来源分开。本轮已核验 Pi934，不等于 Codex 重跑934。
6. 原规划冻结清单为3088项，R2冻结清单为3167项；不要将3167称作原规划数。模型归属仍 unknown：授权为 bonsai2-27b，旧文字自述 Qwen；现有录制器不独立采集模型，用户当前确认继续 Bonsai 不能证明过去会话的实际模型。

已完成且有外层record的Pi目录共13个（R1七个＋本次六个），另有上述无外层record的guards目录。
完整列表由审计 JSON/下一轮 checker 自动索引，不在多处手抄计数。

## A1–A7

| 项 | 结论 |
|---|---|
| A1–A5 | 通过，产品／测试问题关闭并冻结 |
| A6 | 934回归及旧文件冻结核验通过；E1归档范围／可见性待纠正 |
| A7 | E1/E2待关闭；保留缺失preflight、历史时序与模型来源限制，不要求重造历史 |

本次证据审计由非产品作者完成。补充审计的 `review-r2-evidence2` exit1 是 **Codex helper** 将26误写为27；
失败原件保留，新 helper／新 `review-r2-evidence3` 已修正并通过，不算 Pi 缺陷。
该审计两份原样快照继承了 `.gitignore` 的排除行为，不把它们称为 Git 可见归档；
本次另在 `review-r2/hidden-evidence-snapshot/` 保存可见副本，规则原文以 `.gitignore.txt` 命名。

下一轮的三步操作和两个检查命令见 [交接文档](../../../docs/handoffs/T0015-proof-subtree.md)末尾。
T0015完成前继续原方式交回Codex，不启动Codinator或模型联调。
