# T0012 规划审阅（2026-09-21）

结论：设计可交 Pi 实施，状态 ready；**产品验收 not_run**。任务只实现单棵有效出现树的规范键，唯一性计数、motif 与 world 审计继续后拆。

独立设计审阅由 `/root/design_t0012`（`gpt-6-astra`、xhigh）只读完成，未写产品或运行检查；Codex 主代理负责下述记录化手算核验。审阅确认平坦前序流可以从 clause body 的 arity 唯一解析；两个合法完整子树流不存在严格前缀关系，因此相同有序 schema 的 AB/BA 候选可以用完整子树流比较来选择。schema 不同则先按 schema 选择并同步配对子树，不允许任意排序。

原草稿两项发现均已落实：

1. K1 单链不能执行非空前提交换／独立分支重排，B 组已明确各变换适用范围；ground 子句和重复 schema 不要求不存在的改动。
2. 新增 K8：两个子树根 header 相同、后继支持不同，必须继续向下比较；七步证明 AB=BA、AA≠AB，拒绝只比较首 header 的错误实现。

其他确定边界：verify_proof 恰一次及原异常传播；随后以引用次数限定出现树；不拒绝合法交错拓扑编号或有限循环规则证明；新模块有私有 ordered-clause 编码，不调用 T0011 私有函数。输出恒定嵌套深度，显式栈比较／展开，无整子树缓存。一个新产品文件与一个测试文件、六个实施步骤，无需另拆节点键任务。

主代理核验原件：

- [planning-preflight](planning-preflight/record.json)：接受的 T0011 产品／测试与历史哈希一致；当前 HEAD `4c457e21899f81274999855d905e66b2ba574798`，保留未提交工作树；新模块／测试不存在。
- [planning-examples](planning-examples/examples.json)：15 个完整手算键对独立小规模全变量赋值／body 排列 oracle 全部通过。真实 T0009 在 K5/K6、C=3/D=4/S=20 下各返回 4 棵树，全部经 T0006 核验，oracle 键集合分别为 4／3，与手算全部集合相同。
- [planning-deep-example](planning-deep-example/example.json)：K8 的同头／不同后继场景、完整七 header 手算流和 AB=BA、AA≠AB 通过。

这些只是规划 fixture 与既有接口核验，没有实现或验收 `canonical_proof_key`；Pi 必须自行写新产品和测试，不能导入规划 oracle 充作其测试。原型 oracle 只处理小树并枚举所有赋值，与产品要求的最多两候选／显式栈算法不同。

交付材料另提供冻结驱动与 docs 自动 RUN 索引，减少手写命令／哈希误差。规划最后检查源码／旧材料保护、所有本地链接、文本与 Python 语法；完成后生成 planning-files.json 固定内容。原 T0011 记录保持不变，用户未授权 commit/push，本轮未执行。
