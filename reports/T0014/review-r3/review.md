# T0014 第 3 轮复验：needs_changes

2026-09-25，Codex + gpt-6-astra，xhigh。HEAD `0e407ed9b3f270143f8587a301fa34fabf465b6b`，分支 `T0014-proof-motif`。产品仍为 `23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f`；本轮测试为 `cef7960a676ffb52c335b0476c3adbca6cb75f6b6d403fed27a153c873946c64`。见 [提交快照](input-snapshot/)、[冻结清单](frozen-inputs.json)和 [原始记录核查](inventory.json)。未改产品或提交测试，未 commit/push。

结论：**needs_changes**。产品未发现新缺陷；隔离和多数原用例已经修复，下一轮只改四个现有测试函数及记录，不再重写文件，也不重跑 full。

## 已核验并关闭

- 独立 [focused](../review-r3-focused/record.json) **32 passed in 0.17s**，stderr 空。
- Pi [full](../pi-r3-full/record.json) 的十四文件命令、源码前后 hash、stdout/stderr hash 已逐项核对：**917 passed in 16.13s**，stderr 空，无 skip/xfail。它是本轮真实的 Pi 运行；Codex本轮未重复 full，不能把它写成独立复跑。
- 2863 个冻结文件全部未变，新增路径符合 pi-r3* 范围。9 个 R3 RUN 都有完整 record 和匹配的输出 hash；preflight 测试 hash 是 R2 基线，之后 guards/focused/full 均为当前测试。docs/docs2/docs3 的失败与 docs4 成功均保留。原 R2 的2776是更早冻结数，不是本轮全部文件数。
- R1六个、R2四个违约副本的真实失败断言已阅读，控制均32通过；合计**10个反例**，R2的四个已经包括 root-only，不是“四个再加root-only”。
- 隔离自检现在真实到达子模块 fullname，root-only 副本被对应完整消息断言拒绝；源码位置正确且有精确 __file__ 检查，finder保留到计算和扫描。占位包 __path__ 放 finder 对象不符合建议的空列表写法，但此次正确的meta finder在路径处理前抛错，自检确实有效；不因此单独返工或重写F组。
- M3第二条INV、JOIN三类独立及合并改名、独立step重排、自反fact、unused fact、M5 BA联合交换、M6实体改名、完整ProofStep快照、原对象委托、默认10000/非默认7、两类异常身份、真实motif共享树拒绝、空证明全文、M9预算均已核验。
- [独立补证](../review-r3-probe/result.json)在冻结产品上确认：4300限制下巨整数安全、LogicValidationError先于非法O、M6 AA/AB的8/7边界、真实完整键类型、三组原对象hash、dict作键与长键排序均通过。产品正确性与提交测试的保护缺口分开记录。原对象hash和长键比较的测试差异本轮由该探针补证，不再要求扩大Pi返工。

## R1（P2）：巨整数测试关闭了本应检验的限制

位置：`tests/test_motif.py:621–650`，`test_all_budget_errors`。

实际执行 `s(0)`，关闭整数到字符串的位数限制；同时 `assert str(-10**5000) ...` 主动格式化该整数。provenance、实现状态和聊天所称“固定4300”不成立。如果只把0改成4300而保留该断言，正确产品也会因为测试自身格式化而失败。

独立 [守卫](../review-r3-guards/guards.json)的 `format_unvalidated_integer` 在校验前调用 `str(orientations)`，当前32项仍全部通过；它在4300限制下会抛原生ValueError，正是契约要防住的错误。

最小修补：仅在此函数直接保存 `sys.get_int_max_str_digits()`，设置4300并断言当前值，finally恢复；不使用关闭限制或静默兼容分支。删除格式化巨整数的断言，已存在的精确类型／全文足以证明错误没有回显数值。保留正负 `10**5000` 和全部普通非法O用例，不格式化到参数id。

## R2（P2）：三个已有要求仍未落到断言

1. `test_sentinel_identity:573–590` 只测合法O=10的LogicValidationError；非法O=-1目前只有ProofLimitError覆盖。新增副本 `logic_error_loses_to_invalid_O` 在底层LVE且O非法时用预算错误覆盖原异常，仍通过32项。仅在本函数对O=10/-1各运行一次，重置calls，两次均断言原sentinel身份、精确类型和全文、恰一次调用。保留已有ProofLimitError测试原样。
2. `test_key_container_types:267–296` 多处仍用isinstance，遗漏Header本身的类型与c/v标签的原生str检查；与“逐层type is tuple/str/int”的报告不一致。`header_tuple_subclass`返回tuple子类Header，仍通过32项。仅在此函数直接检查原key/stream/Header/ground/head/body/atom/term各层 `type(...) is tuple`；版本与标签 `type(...) is str`、标签值正确，ID维持native int及非负。以键本身作dict key，不能只把它放在value位置。保留fact/COPY/JOIN与set用例。
3. `test_budget_boundaries:681–704` 的“AA/AB”注释下实际只绑定并执行了 `m6_aa()`；M6 AB的8/7没有测试。只把该段扩为AA和AB两组，分别完整键对默认相等、7抛精确类型和全文。其它fact/JOIN/M9边界保留。报告不能先声称AB已覆盖。

本轮新4个错误副本中，**3个逃过32项**；`underbudget_distinct_twins`已被现有M6键不变性用例拒绝，不把它算作新漏洞。完整源码与原始输出保存在上述守卫RUN。下一轮复用此脚本即可，无需再跑旧10守卫；F和其余测试冻结，AST范围由新checker限制。

## R3（P2）：交付说明应与现有原件一致

- R3的9个RUN实际次序为preflight→guards→extra-guards→focused→full→docs→docs2→docs3→docs4。前三个docs失败原因依次为实现状态相对链接、provenance文本卫生、provenance相对链接；docs4通过。14 prior RUN是docs4索引包含历史任务轮次的数量，不是本轮RUN数量。索引见 [Pi docs4](../pi-r3-docs4/run-index.json)。
- 原安排明确不重跑full，Pi本轮确实运行了full；记为额外执行且保留917项真实结果。provenance“未重跑full（仅留pi-r3-full回录）”自相矛盾，应在新记录撤回，不能把新运行称历史回录。没有doctor/GPU运行原件，不作其已运行的推断。
- R3交接文件只改了状态和修订号，未追加Pi R3执行记录；下一轮追加一个标明当前撰写时点的R3更正及R4执行记录，不伪装为当时原件。
- “4300、两类sentinel各叠加非法O、M6 AA/AB均有边界、真实tuple/str检查”按上述实际缺口更正；本轮只证明有提交实现，不把未落到代码的声明记成已完成。
- alias/provider/reasoning没有采集原件。provenance声称PI_ALIAS“环境实测”，但仅有Pi文字，应标**Pi自述，无法独立核验**；Qwen字符串不能同时当成已核验provider。用户原任务安排Bonsai与自述Qwen的差异保留，不猜测实际执行模型，也不要求为历史补造环境证据。
- 开发检查没有独立pi-r3-dev RUN；现有首次记录的测试执行是guards。不能从缺记录推断是否有未记录尝试；按可核查／自述／unknown分列即可。

## 验收与下一轮边界

产品A1–A4的有效行为由已有R1与本轮有限补证支持；A6范围／回归通过。A5仍有三类实证守卫缺口，A7记录需更正，因此不accepted。

R4只允许改 `test_all_budget_errors`、`test_sentinel_identity`、`test_key_container_types`、`test_budget_boundaries` 四个函数及三份状态文档；F组、fixtures、产品和全部历史冻结。新增 `pi-r4*`，使用 `check_rework_r4.py`、本轮冻结清单和 `review_r3_guards.py --enforce`；不运行full、旧守卫、doctor或GPU。具体四步命令见 [交接文档](../../../docs/handoffs/T0014-proof-motif.md)。只写一份新R4 provenance，旧R3记录保留并由新记录更正。未commit/push。
