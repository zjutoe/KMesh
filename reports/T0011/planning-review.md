# T0011 规划审阅

- 日期：2026-09-20；规划者 Codex + `gpt-6-astra`，`xhigh`。
- 独立非作者审阅：`/root/review_t0011_scope`，`gpt-6-astra`，`xhigh`；读取研究计划、D18／D26–D29、身份规范及具体交接，手算 K0–K10。初审要求下述三项澄清；完成后再次只读核对三项修正、固定驱动及交付检查器，最终结论：**无阻塞，可以 ready**。未写产品、未运行产品测试。
- [基线](planning-baseline.json)：`4c457e21899f81274999855d905e66b2ba574798`，与 `origin/T0010-minimum-depth` 一致。[planning-preflight](planning-preflight/) exit 0：T0010 接受源码／测试哈希、Python／包版本及路径符合，新产品／测试尚不存在。旧完整回归未重跑。

## 范围与审阅处理

1. T0011 仅一个局部规范键 API、一个测试文件，六步实施。它只规范变量名和 body 顺序，保留实际符号与 schema 参数关系；不实现 proof key、唯一性或 motif。最多两次候选编码，不需要图同构或变量阶乘搜索。
2. 同世界证明身份与跨世界 motif 分层，联合槽位置换、重复出现、对称映射、多条实体桥接支持均明确；完整树算法和正式划分仍另拆。研究计划 v0.1.3／D29 登记 `proof_identity_v1`，E0 主协议仍为 `e0_v2`，未生成数据或改变模型输入。
3. **审阅意见 1 已修：** 原 K8 恰好能被错误的原名排序方法算对，不能单独作为该反例；加入 K8a `p(?a,?z),p(?z,?b)->q(?z,?z)`，相同期望使该错误暴露。
4. **审阅意见 2 已修：** 不等价例限定为单个出现位置的符号变化，a/b 对调限定 K0。加入 ground 对称前提交换例，避免把任意符号改名一概判成不同键。
5. **审阅意见 3 已修：** 证明规范中 `(A,A)` 与 `(A,B)` 的区分明确以 A、B 不等价为前提；不与重复等价来源的归并冲突。
6. 五组测试含完整手算结构、有效正反变换、独立有限穷举、输入诊断及实际计算时的硬隔离。穷举最多 48 候选，只在测试／规划端使用，不镜像产品首现编号算法。

## 规划核验与留证

- [planning_examples.py](planning_examples.py) 是有限双射穷举的设计 oracle，不是产品实现；不导入新 API。首个 [planning-examples](planning-examples/) 核对 11 个手算锚点通过；审阅后增加 K8a／ground 对称例，再以新 [planning-examples-r2](planning-examples-r2/) 运行通过，旧 RUN 未覆盖。当前脚本对应 r2 的扩充范围。
- [planning_check.py](planning_check.py) 校验规划变更范围、旧源码冻结、文档／链接／ready 状态、helper 语法、驱动四阶段命令与 basetemp。它模拟命令构造，不假称已跑新增测试；实际核验留存在 [planning-check](planning-check/)。最终 `planning-files.json` 在记录器完成后生成，避免哈希活动记录。
- Pi 使用固定驱动，编码前 preflight，状态先行，每个尝试使用新 RUN，失败不得改名覆盖。源码／文档卫生与原始日志保真分开检查；历史日志的原生尾空白不要求重写。

[交接](../../docs/handoffs/T0011-clause-key.md)在上述核验通过后为 ready；产品实现／新增测试均 **not_run**。本次仅规划，未 commit／push。Pi 实施后再由 Codex 对实际 diff 和 A1–A7 验收。
