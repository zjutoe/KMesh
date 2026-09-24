# T0013 规划审阅（2026-09-23）

目标是一个薄组合 API：完整枚举、逐树验证／规范化、精确计数。产品与新测试尚未实施，产品验收 not_run；规划核验不能当作新 API 已通过。

独立设计审阅由非作者 `/root/design_t0012`（继承 `gpt-6-astra` / xhigh）只读完成。主要确认：

- 该范围符合研究计划 §4.5／§5.2 与既有 `proof_identity_v1`，无需改变身份等价、数据准入、模型信息白名单或 E0/E1 版本。
- 0／1／多条必须以全部成功为前提；无关关系环、枚举超限、后续单树失败都不能被转换成结果。
- T0009 返回树长度不超过累计 S；将 S 透传给 T0012 `max_steps` 合理。不用实际万步长链测该参数，避免 T0009 子证明累计复制成本；用非默认 S=20001 的调用 spy 即可。
- 原始树计数与规范数不同：重复来源应归并，对称槽的 AB/BA 可归并，非对称槽的 AB/BA 不可归并。保留实际支持实体与规则差异。
- 不重复 verifier，不重写规范化／oracle，不新增第二预算、摘要类型、CLI 或通用 mutation 框架。计数不是 world 重复准入或 motif 审计。

具体交接二次静态审阅结论：四步、一个产品模块与一个测试文件适合一次实施；调用 spy 与真实 fixture 互补，README 定位和一份 provenance 流程自洽。审阅指出显式 basetemp 不会自动生成忽略规则，可能被 docs 范围检查误拦；主代理同期已写入任务级 [.gitignore](.gitignore)，最终检查明确核对其 `pytest-tmp`／`__pycache__` 路径规则。该文件也纳入冻结清单，保留临时文件而不要求 Pi 删除原件。无其他必须修改项；审阅者未执行检查。

主代理经不可覆盖的新 RUN 完成：

| RUN | 结果 | 原件 |
|---|---|---|
| planning-preflight | 接受的 T0012 与 e576c77 相符；tracked 基线干净，新产品／测试不存在；环境已记录 | [record.json](planning-preflight/record.json) |
| planning-examples | U0–U8 九个手算计数、U6 三种精确预算失败、两个无关环例均通过 | [examples.json](planning-examples/examples.json) |
| planning-collection | 既有十二文件共 864 项，仅收集，未执行回归 | [record.json](planning-collection/record.json) |

本次沿用用户已授权的 Pi + bonsai2-27b；实际运行模型仍须由执行者如实标注来源。为减少前轮的重复返工，交接直接给出少量真实 fixture、失败消息、实际 patch 位置和唯一验证入口；文档检查自动执行 README U3 并生成精确 RUN 索引，不要求手抄全套日志或反复回填 docs 自身结束时间。

任务规划状态见 [交接文档](../../docs/handoffs/T0013-proof-count.md)；最终卫生检查原件为 [planning-final/record.json](planning-final/record.json)，仅覆盖规划基线、改动范围、脚本语法、临时目录忽略、文档链接及文本格式。原始失败输出与冻结证据保持原字节；新的源码／维护文档直接检查末尾换行和行尾空白，避免用全仓 `git diff --check` 误判保存的原始 traceback／diff。
