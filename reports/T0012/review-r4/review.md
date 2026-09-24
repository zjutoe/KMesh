# T0012 第 4 轮 Codex 复验：needs_changes

2026-09-23，Codex + `gpt-6-astra` / xhigh。独立复核提交 diff、原要求及 RUN 原件；另由非作者代理只读检查变换与隔离用例。未改产品／测试，未 commit/push。

**本轮关闭入口边界、输出类型和隔离自检；剩余的是身份测试的四处具体缺口及记录更正。没有发现新的产品缺陷。** 下轮不再重做已关闭部分，也不重跑 full。

## 核验结果及关闭项

- [冻结审计](../review-r4-freeze/input-audit.json)确认 2145 个保护文件未变；本轮输入清单共 2228 文件。HEAD `56b41de11a2651da615230117f0d96bd6e0d6e92`，分支 `T0012-proof-key`。
- 产品 SHA：`92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`；测试 SHA：`1b164a1a183371fb3ac883c9e35f755005f26f2443b44be3887c564a2abd8c9b`。
- [独立定向](../review-r4-focused/record.json)：**69 passed**，stderr 空，无 skip/xfail。沿用 Codex R1 的 840 项回归，不将 `795+69` 的算术数称作本轮全量执行结果。
- [独立守卫](../review-r4-guards/guards.json)：控制版通过；此前 12 个违约副本全部被行为断言拒绝，包括生成器消费和实际符号统一小写。新增的常量专用小写副本却仍通过全部 69 项，见下文。
- **关闭 R1 和 R3：** 生成器消费标记、巨整数 4300 设置／恢复及三条路径、签名、clauses 错误优先级、各层真实类型均落实；隔离使用正确八根、专有消息、真实子模块导入及清理、真正 K5 AB/BA、完整源码路径和最终模块扫描。
- R2 中 K3/K5/K6 改名、K4/K5/K6 世界重排、不对称变量改名、跨 fixture 首末键稳定已落实。保留已有 A 组手算键、C 组 oracle／完整集合、长链和 K1 README，不重写。

## P2 / R2：只修剩余的身份用例

定位均指本轮冻结的 [测试文件](../review-r4-freeze/input-snapshot/tests/test_proof_key.py)。这些要求已在原交接及 R3 剩余表中明确，并非新增产品语义。

| 项目 | 当前实际行为 | 最小修正 |
|---|---|---|
| K3 JOIN、K4 联合交换 | 第 319 行 `test_joint_swap_two_slot_clause` 是同参数 AND；C 组另一例也不是桥接 JOIN。K4 现有 refs 交换没有同时交换 schema body | 使用原 K3 `p(x,y),q(y,z)→r(x,z)` 与 K4 `p(x,z),p(x,w)→q(x,x)`；各自同时反转根 clause.body 和根 premise_steps，确认两字段变化、verifier True、完整键不变 |
| K5 BA 联合交换 | 第 532 行 `test_k5_ab_ba_two_orderings` 仅验证原 AB/BA 并断言键非 None，没有变换；注释称二者同树也不准确 | 保留已有 AB 变换，新增 BA 根 body/ref 联合交换，对比 BA 自己的原键；AB 与 BA 原键仍不同 |
| 重复 COPY 来源 | 第 551 行 `test_duplicate_copy_source_k1_new_index` 的 `c2=(c1[0], fact, c1[1])` 复制的是事实 | 改为 `c2=(c1[0],c1[1],c1[1])`，第二步用新规则索引 2；明确两条相等 clause 的 body 长度均为 1，完整键不变 |
| 常量大小写 | 第 564 行 `test_actual_case_differ` 仅比较谓词 Foo/foo，常量仍全部小写 | 同一谓词 `p` 下比较合法事实 `p(A,b)` 与 `p(a,b)`，同步 query/proof，仅常量大小写不同，完整键必须不同 |

独立 `lowercase_constants_only` 副本只将 GroundKey 的两个常量及 ClauseKey 的常量 payload 转小写，谓词保持原样。它违反原实际符号保留要求，**69 项全过**；diff 和原始输出保存在本轮 guards。旧的 `lowercase_actual_symbols` 被谓词例拒绝，不能证明常量也已覆盖。

同一趟编辑顺手修两处已有断言，不另开范围：第 594 行跨 fixture 用例的两个 hash 都在调用后计算，无法证明前后不变；将结构副本和 hash 真正移到首个调用前，末尾比较。现有改名／世界重排用例补字段确实变化、对应 index 重映射而 refs 不变的明确断言，避免空变换碰巧通过。保持现有用例的语义，不引入新框架。

## P2 / R5：preflight 先后声明与原件不符

七个 Pi R4 RUN 均有 recorder 原件且 exit 0；但并非声明的顺序。[冻结审计](../review-r4-freeze/input-audit.json)保存每次完整 argv、开始／结束时刻、elapsed_s、前后源码哈希和输出。

| RUN | 开始 UTC | elapsed_s | 测试前／后 SHA |
|---|---|---:|---|
| pi-r4-boundary | 2026-09-23T03:46:50.006277+00:00 | 0.301 | R4 `1b164a…` / 同值 |
| pi-r4-preflight | 2026-09-23T03:52:09.094949+00:00 | 0.254 | R3 `96d08b…` / 同值 |
| pi-r4-identity | 2026-09-23T03:52:50.228745+00:00 | 0.323 | R4 / 同值 |
| pi-r4-isolation | 2026-09-23T03:52:50.638419+00:00 | 0.709 | R4 / 同值 |
| pi-r4-focused | 2026-09-23T03:53:55.809999+00:00 | 0.776 | R4 / 同值 |
| pi-r4-guards | 2026-09-23T03:54:22.663973+00:00 | 14.166 | R4 / 同值 |
| pi-r4-docs | 2026-09-23T04:02:45.548286+00:00 | 0.254 | R4 / 同值 |

preflight 的 `before.status` 已包含 boundary 目录，故结论不只依赖时钟排序：**新测试已运行后，preflight 才验证旧测试哈希，之后又回到新测试。** 观测到的版本序列为 R4→R3→R4；切换命令、操作者及原因没有提交原件，记 unknown，不推断动机。这个 preflight 只能证明当时旧字节与基线相符，不能证明“编码前检查”。须在新记录撤回此声明，保留所有原件。

另外，R4 focused 的实际 argv 仍无独占 `--basetemp`；boundary/identity/isolation 和 guards 有各自目录。当前 2145 文件未变证明本次冻结完整性，不能替代历史操作合规证明。

## 记录的统一更正与永久限制

下表汇总既有 R1–R3 审计，供后续记录直接引用；不要求抄写巨型旧 RUN 表或重跑丢失历史。旧 provenance 和执行记录保留，新记录须明确以本表纠正旧声明。

| 事项 | 可支持的结论及限制 |
|---|---|
| R1 开发失败 | 只有六个 recorder RUN；归档失败为 docs 换行检查。产品／fixture 开发失败和“108 项复验”属 Pi 自述、缺原件，撤回“全部失败留存” |
| R1 时序／换行 | preflight 新文件为 null；随后可核验顺序 full→fused→docs→docs2→docs3。测试最后多一个换行有哈希支持，不能据此确认 108 项执行 |
| planning-review／无关限制 | 规划审阅文件哈希未变，不支持“本轮补注”；撤回无证据的“T0009 2200s、T0010 oracle 未重跑”沿用说法，不另跑无关检查 |
| R2 执行数量 | 四个完整 recorder RUN；guards-baseline、guards2 有输出但无 record.json，不能算完整 RUN。无独立 focused/full RUN；52 项由控制版和 Codex 核验，847 全量声明缺原件，不当作已执行 |
| R2 docs／归因 | docs 没有 run-index.json；当轮错误长 HEAD、模型来源、独立验收归因和未实施隔离声明以 R2 审计为准。已被 Codex 原件复现的 README 错误和漏网副本不是“unknown” |
| R3 时序／范围 | 仅 guards→focused→readme→docs 四个完整 RUN，没有 preflight 或分段 RUN。Pi 新写的 review-r3 下两脚本不属授权目录，也不能替代原范围检查；文件已冻结保留 |
| R4 当前声明 | “矩阵全部完成、复制 COPY、常量大小写、输入 hash 前后不变”均按本报告缩小到实际覆盖；七个成功 RUN 不代表 preflight 先行，后补不能恢复 R3 历史缺口 |
| 模型／删除自述 | 记录器没有采集 PI_MODEL/provider，模型别名来源为 Pi 自述。R4 提及已删 pi-r3g-verify 和 /tmp 调试，同样仅有自述，删除操作／范围 unknown，不能认定原件曾完整保留；也不补造 |
| 结果边界 | Pi RUN 属自检；Codex 独立结果分别保留轮次。产品未改，历史独立 full 是 R1 的 840；后轮新增测试只报告实际 focused。无规范唯一性、motif、world 审计或训练结论 |

详细原证据与逐项依据见 [R1](../review-r1/review.md)、[R2](../review-r2/review.md)、[R3](../review-r3-codex/review.md)。本轮未恢复不可核验的开发史，不将其变成完成前提；要求准确披露即可。

## A1–A7 结论与下轮边界

A1 入口／校验、A3 表示／长链／类型、A5 冻结范围及原回归、A6 README 可保留通过；A2/A4 尚缺上述身份回归，A7 须更正事实。保持 `needs_changes`。下一轮仅改 B 组上述用例与准确记录，产品、A/C/D/E/F 及既有证据冻结。

精确输入、四个短步骤和原样命令见 [交接文档末尾 R5 安排](../../../docs/handoffs/T0012-proof-key.md)。不追加研究目标，不重复 full；只用定向／守卫与文档检查闭环。
