# T0006：Codex 第 1 轮验收

日期：2026-09-16。结论：**needs_changes**，不接受为已完成任务。审阅者为 Codex + gpt-6-astra（xhigh）；非实施作者的独立静态审阅由 /root/review_t0006_tests 完成。

产品实现暂未发现实质逻辑错误。本轮问题集中在持久测试的有效性／覆盖与交付记录，不能用 422 passed 替代契约证据。

## 已核验事实

- review-r1-freeze：退出 0；冻结提交输入及 673 个历史报告文件；16 个 Pi RUN 的两路日志哈希及运行前后源码哈希均一致；15 个已跟踪旧产品／测试／依赖文件与 HEAD 一致。记录器与 .gitignore 对照 planning-final-check 未改。原始冻结见 ../review-r1-freeze/audit.json 及 input-snapshot/。
- review-r1-full：退出 0，422 passed in 4.00s，无 skip/xfail；六文件精确回归命令，使用独占 basetemp。
- review-r1-probes：退出 0；16 个独立产品边界检查通过，包括外部校验优先于长度、长度优先于 proof 成员、4300 限制下全部目标巨整数路径及大正整数范围。正确的四类根模块／子模块隔离子进程、FACT/COPY 与 README 主例均通过。
- 源码 SHA-256：008bdd3633a5d2327cd711b7c9de7149df86b588632db659a23bf34207963daa。
- 测试 SHA-256：857dd21dc6e3d573d8a363d4932e08bbbdabf85a6235356b23b235cf360de32b。
- 核验只读产品／测试，没有改动 Pi 的冻结实现。有限证明中的重复步骤、重复引用均允许；上限优先于 proof 成员校验，但不优先于入口参数校验。

## R1（P2）：隔离守卫实际不拦截求解器

tests/test_proof.py:37–38、681–682 使用 list 的 parts[:3] 与 tuple 比较，条件恒为 False。子进程最后仅检查两个精确 solver 名，没有检查 torch/yaml 和子模块。独立探针实际调用两套 finder，确认 solver 返回 None；正确 guard 下现有产品仍可验证 FACT/COPY，故这是验收测试缺陷，不是已发现的产品违规导入。

返工：修正完整名称／点前缀匹配；四类根 torch、yaml、kmesh.logic.engine、kmesh.logic.reference_engine 及各自子模块均受保护；在新子进程自校验 guard 后导入 proof 并验证 FACT/COPY，检查所有对应 sys.modules 名称。修复／清理模块级 autouse guard 时不得污染旧回归的导入状态。

## R2（P2）：语义反例和“改名”未测试声称的行为

- tests/test_proof.py:343–345 的错误替代路径先把 p(d,c) 引用到 p(b,c) 的 fact，随后把 JOIN 引用到 fact。False 提前来自伪造事实，未检验“世界中存在正确答案，但提交错前提”。探针确认这组正反例可同时通过一个只检查事实前缀、完全忽略规则证据的错误 verifier。
- :227–233 的“引用不足”同时使最终 conclusion 与 query 不同，不能作为仅违反前提数量的反例。
- :383–395 的“改名”拆掉 JOIN 的共享变量并改变 head 参数位置，实际上换了规则；不是一致改名的不变性测试。

返工：使用契约 C 组 p(a,b)、q(b,c)、q(d,c) 与 JOIN 世界，事实各指向正确 clause，JOIN 始终指向规则；合法／非法证明只改变所选已验证前提。让引用不足例只违反目标规则。对一个已成功的 fixture 做双射实体／谓词和 clause 内一致变量改名，保留共享变量关系、head 位置与引用，并同时验证原例和改名例。用守卫探针确认修正后的关键反例不再接受上述错误 verifier。

## R3（P2）：预算异常优先级与巨整数缺少持久覆盖

tests/test_proof.py:617–661 的 6 个预算测试均使用合法成员。独立探针把验证器替换为“先扫描成员，再交给真实实现检查长度”的错误顺序，全部 6 个测试仍通过。

返工至少覆盖：

- 相同 proof=(合法步骤, 非 ProofStep)：max_steps=1 为 ProofLimitError，消息含 verify.max_steps/exceeds；max_steps=2 为 LogicValidationError，消息含 verify.proof[1]/ProofStep。
- 错误 query 与过长 proof 并存时先报 verify.query/Atom，不能将“超限先于任何异常”写为契约；容器／长度先于 premise 成员的构造边界也用单点例核验。
- 使用局部 fixture 将 sys.set_int_max_str_digits 设为 4300，finally 恢复；所有大整数测试使用 10**5000 与短 id，不输出整数值。
- 补全负大 clause/premise 索引、巨整数 conclusion、verify.clauses/proof 成员、query、非正预算；逐例断言异常类别、准确字段与完整原因。现有巨大 query 测试还须断言 Atom。
- 大正 clause_index / premise reference 可构造而验证 False，大正 max_steps 可接受；不得添加产品数值上限。当前产品在上述独立探针中全部通过，返工只补持久测试。

现有文件没有 set_int_max_str_digits 子进程或 fixture。用户交回摘要中“设为 100 再 import”的说法与文件不符；实测此解释器拒绝 100，抛 ValueError，不能当作已运行测试。

## R4（P2）：API 文档和证据陈述须纠正

- README.md:115 将默认 max_steps 写成 1_000，实际与契约均为 10_000；测试命令漏 tests/test_proof.py。修正这两处，并将旧 T0005 段的“证明验证器尚未实施”限定为当时验收范围。
- 截至冻结时可核验的是 16 个 pi-*/record.json，而非摘要中的 19 个 RUN；首次漏 -- 的记录器启动在建目录前退出，现有归档没有该失败的原始记录。它与未走记录器的单行探针均保留为自述限制，不得说所有尝试已完整留存。
- pi-r1-preflight 的 record.json 内实际命令与契约一致，原始版本输出及 before/after 的 git 快照完整；没有“嵌套引号截断”证据。若该描述指另一次外层 shell 尝试，必须说明无法由这个 RUN 核验。preflight-r2 是实施完成后的补充检查，不是新的实施前基线。
- “索引不重复”“超步数先于任何异常”“零导入”“AGENTS 有未提交改动”等陈述与契约／文件不一致。应分别写为允许合法重复、入口校验先于长度、仅标准库+types／无禁止依赖，以及准确的变更时点；D21 在任务开始前已有，D22–D24 为后续研究修订。
- README 小例的本轮独立运行由 Codex 完成，不能追溯记作 Pi 已运行。新一轮 provenance 放在新的 full RUN 内，列实际命令、开始／结束与 elapsed_s、模型、偏差及历史不可核验项；保留旧 provenance 和执行记录，用追加更正而非覆盖历史。

## A1–A7

| 项 | 结论 |
|---|---|
| A1 | 当前产品边界通过独立探针；持久测试缺口见 R3 |
| A2 | 指定 clause、已验证前提、局部绑定与结论核验通过当前审查 |
| A3 | 当前实现行为通过；针对性反例需 R2 修复 |
| A4 | 当前实现边界通过；异常顺序持久测试需 R3 |
| A5 | needs_changes：R2/R3，422 项通过不足以接受现有测试质量 |
| A6 | 产品独立隔离通过；提交隔离测试需 R1 |
| A7 | needs_changes：R4；已有日志哈希真实且历史保留，不能据此补造缺失尝试 |

返工限定为测试及相关文档／新证据。冻结 proof.py，除非新回归揭示真实实现缺陷并先报告。研究计划 v0.1.2 不改变本任务 E0 契约；其他工作树改动和所有历史 RUN 保留。未 commit/push。
