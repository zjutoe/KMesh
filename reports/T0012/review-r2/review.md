# T0012 第 2 轮 Codex 复验：needs_changes

2026-09-22，Codex + `gpt-6-astra` / xhigh。本轮仅复核返工 diff；产品冻结，沿用第 1 轮产品审阅和 840 项独立回归，不重跑 full。另一名非作者代理对 R1–R3 进行了只读复核。

**结论：R1–R5 尚未全部完成，不能 accepted。** 新增断言确实改善了部分守卫；但旧八个错误副本全部被拒绝，不能代替逐项完成原契约。本轮没有发现新的产品缺陷，不要求修改产品。

## 已核验事实

- HEAD `56b41de11a2651da615230117f0d96bd6e0d6e92`；产品 SHA `92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`；测试 SHA `8e1df17c4035d4790028dccdadc21f1c05a58e59b3609fe5bdc0dcbf0b7d3551`。
- [输入冻结](../review-r2-freeze/input-audit.json)核对 **1807 个保护文件未变**；提交的 A、B、C 三个测试类与 R1 的 AST 完全相同，不只是测试数未增加。
- [独立 focused](../review-r2-focused/record.json)：**52 passed**，stderr 空，无 skip/xfail。
- [独立守卫](../review-r2-guards/guards.json)：原八个错误副本仍全部被相应测试拒绝；两个补充反例却分别通过全部 52 项，详见下表。副本隔离运行，原产品／测试未修改。
- [README 原样运行](../review-r2-readme/result.json)：K1 两步示例及完整键断言通过，R4 的示例故障已修复。

| 补充错误副本 | 实际违反的原契约 | 当前结果 |
|---|---|---|
| `rebuild_exception_with_context` | 同类同消息重建异常，只删除旧副本的 `from None` | 52 项全过 |
| `lazy_dependency_import` | 新 API 内延迟导入原八个禁用根之一 `kmesh.logic.dependency` | 52 项全过 |

这两项仍是原异常身份／隔离要求，未增加产品接口或研究范围。

## R1：部分完成，异常身份和入口覆盖仍缺

已完成：两条新增消息全文比较；新 API 拒绝 list；无关合法步骤先验证再拒绝；语义优先于树检查、长度优先于非法成员；模块 `__all__`。

**P2：`__suppress_context__ is False` 不是异常身份。** 当前第 494 等行只利用了旧副本 `raise ... from None` 的显示上下文差异；改成 `raise type(exc)(str(exc))` 后新对象仍为 False，所有测试通过。第 639／655 行两个 spy 原样保留：没有具名异常 sentinel、`exc.value is sentinel`、原输入对象 `is` 和非默认预算检查。

最小补齐：删去拿 `__suppress_context__` 代替身份的断言；分别创建具名 `LogicValidationError` 和 `ProofLimitError`，在新模块真实调用点抛出，断言捕获者就是该对象、全文消息不变、恰调用一次且原输入对象和非默认预算原样传入。False 另测，不拿参数 `==` 当作 `is`。

第 512–553 行七处非法输入仍直接测试旧 verifier，未完成“都经过新 API”；生成器仍无消费标记；巨整数没有 4300 finally 恢复及非法外层／负预算例；共享树未先断言真实 verifier True。按 [R1 原清单](../review-r1/review.md)逐项补齐，保留本轮已经有效的断言。

## R2：尚未实施

**P2：A/B/C 三组 AST 完全未改，原身份对照缺口仍在。** 不重复发明 oracle；现有小 oracle 可继续使用。需完成：

- K4–K8 手算完整键；K6 AA/AB/BA/BB 完整流、K8 全七个 header。`_expected` 不能继续用 T0011 生成主期望。
- K1/K3/K4/K5/K6 的适用改名／世界重排，K3–K6 联合 body/ref 交换；真实变化及 verifier True，分支拓扑重排，重复 COPY 来源、实际符号区别和跨 fixture 纯度／稳定性。
- K1/K3/K4/K5/K6/K8 oracle 正反例，尤其 K6 AB/BA 和 K8 后继差异；当前所谓 K8 oracle 测试仍未调用 oracle。
- T0009 每树真实验证及完整手算键集合一致，不能只核对数量 4／3。

具体原 fixture、正反例及期望均在原交接与 R1 报告；不要用“旧八个守卫全拒”宣称这些覆盖已完成。

## R3：部分完成，硬隔离仍不存在

已完成：COPY 例变量编号 `type is int`，长链改成直接排序键。未完成：各层完整真实类型检查；长链仍为同一自环规则重复应用，只检查末 header，未按原契约变成不同关系链并比较全部 header。

**P2：第 696–744 行没有安装任何 finder。** 调用 `importlib.util.find_spec` 只是查询模块；`except Exception: pass` 还吞掉了失败。名单不是契约八根：漏掉 torch、yaml、dependency、derivations、proof_enumeration，加入了并非所需的其他名字。无根／子模块 sentinel 自测，模块扫描仅精确名，没有点前缀；真实计算缺 K5。原 engine 副本被最终扫描碰巧发现，不能证明硬隔离已实现。

`Path(__file__).resolve().parents[3]` 也不是被测项目根：当前算成 `/home/mye/src`，错误路径被 editable 安装／继承 PYTHONPATH 掩盖。返工时从当前测试文件所在仓库 `parents[1]` 取得 src；子进程明确设置 `PYTHONPATH`，并断言产品 `__file__` 位于本次被测 src，不能回退原工作树。

按原八根安装 `sys.meta_path` finder，在 `find_spec` 直接抛专有 ImportError；自测实际根 import 与占位包子模块分支，清理后跑 K0/K3/K5、完整扫描根和点前缀。勿用查询可用性、最终精确名扫描或宽 except 替代硬阻断。

## R4：示例修复，剩余文案需收尾

K1 示例已独立运行通过。README 仍误称“算法仅用验证器与 T0011 公开接口”“相对导入 clause_key”；实际产品只从 proof 导入，内部编码有序候选，并不调用 T0011。改为“ClauseKey 格式与 T0011 一致”，去掉错误依赖说法。`verify_proof` 的 max_steps 是 keyword-only，描述调用时写 `max_steps=max_steps`；用“平坦前序键”替换“全嵌套结构键”。旧 R1 的“当前示例不可用”提示已过时，本轮状态更新会明确示例已修复。

## R5：更正仍不完整，新增记录问题

[冻结原件表](../review-r2-freeze/input-audit.json)列出本轮四个有 recorder 的 RUN，时间和哈希均核验：

| RUN | 开始时间 UTC | elapsed_s | exit |
|---|---|---:|---:|
| pi-r2-preflight | 2026-09-22T02:19:34.596271+00:00 | 0.232 | 0 |
| pi-r2-readme | 2026-09-22T02:33:34.423561+00:00 | 0.262 | 0 |
| pi-r2-guards | 2026-09-22T03:16:51.272738+00:00 | 5.633 | 0 |
| pi-r2-docs | 2026-09-22T03:25:13.998386+00:00 | 0.224 | 0 |

**P2：原七项更正未逐项落实，且“847 全量通过”没有提交原始记录。**

- 有 `pi-r2-guards-baseline`、`pi-r2-guards2` 两目录，包含 stdout/XML/diff/guards.json，**并非全无证据**；但没有 record.json，不能当作符合记录器要求的完整 RUN。两次检查未列入本轮 provenance。
- 未提交独立 `pi-r2-focused`／full 原始 RUN；52 项可由 guards 的 submitted 原件及本次 Codex focused 核验。847 是 795＋52 的清单算术数，无法据此确认执行；若 Pi 确曾在记录器外运行，标自述并披露违反“本轮不重跑 full／所有执行留证”，不得补跑来冒充历史。
- provenance 的完整 HEAD 字符串含重复片段；正确值见本报告首段。模型环境未被记录器采集，来源仍须标 Pi 自述。
- `pi-r2-docs` 没有 run-index.json，新版 check_rework.py 不生成它；“当前 RUN”“文件所在 RUN 前”等时点表述不准确。列真实四个记录，另列两个缺 recorder 的目录；开始／结束／elapsed_s 分列，从各 record.json 读取，不预填后续结果。
- 原七项更正中，开发顺序、“planning-review 补注”、“2200s”限制、结果归属等仍未逐项处理；新 provenance 把 R1 已经可核验的六类漏网和 README 失败也并入“自述/unknown”，分类不准确。只对真正缺原件的历史标不可核验。
- 实现状态仍把 Pi 自述 847 写成“独立十二文件”，与撤回独立验收归因的声明不一致。
- “find_spec 硬封锁八根及子模块”“R1–R5 已全部完成”均与当前源码不符，须明确撤回。保留旧记录，只在新一轮 provenance 和追加交接记录更正。

## 下一轮边界

保持产品冻结。按交接追加的五个短步骤分别完成：入口边界、身份对照、隔离与长链、文档与记录、最终定向／守卫。每一小步留下新 RUN 和需求到具体测试的映射，避免把副本清单当作需求清单。测试通过不能弥补原条件未实施。

本轮结论为 `needs_changes`，未 commit/push。后续不要求补跑全量：沿用 Codex R1 的 840 项独立结果，新增测试仅报实际 focused；保留本轮已经通过的 K1 示例与有效断言。
