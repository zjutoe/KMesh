# T0010 第 2 轮验收：needs_changes（三处最小修补）

2026-09-20，Codex + `gpt-6-astra`，`xhigh`；非 Pi 作者，`/root/review_t0009_design` 另行只读复核测试。**本轮主体返工有效，R3／R4 关闭；R1／R2 各有明确契约残留，产品无需修改。**

## 已核验并关闭的部分

- HEAD 仍为 `153295c28788f27ef37e794c7c0ea19841accaa8`。产品 `0361a37e8fbfcceb69ac55336c8578176ab96f1c94a86fa50a98aaa2a839bf5d` 完全冻结；测试为 `ddc238a67816c94fee35b122f1690bc441bff657f2d5b5fc8b22047b0e111a2a`。输入及实际 diff 见 [review-r2-freeze](../review-r2-freeze/audit.json)。115 项旧材料／本轮 Pi 原件冻结，旧 review 和规划未变。
- 五个 Pi R2 RUN 的 stdout／stderr 哈希、前后源码与退出码一致；preflight 使用 R1 测试，后四个使用本轮测试。Pi 的 [完整回归](../pi-r2-full/)为 **732 passed in 15.08s**，stderr 空；本轮未机械重跑旧679项。
- [独立重跑原守卫](../review-r2-guards/guards.json)：当前提交 **53 passed**，旧四种违约副本均由指定测试拒绝，5/5 guard_valid。巨整数及恢复、非法输入调用哨兵、H表精确预算与类型、全世界环／预算、主要变换和恢复路径均已补强。
- **R3 关闭：** 干净子进程在 find_spec 阻断六根及子模块，真实执行 fact/COPY/JOIN 后扫描 sys.modules；已能拒绝函数内部导入 solver 的变体。
- **R4 关闭，保留历史限制：** 新 provenance 已纠正 R1 的 RUN 计数、预算／fixture、自述边界和 README 等；当前示例是 H4，命令顺序一致。完整别名已记录，历史服务版本映射 unknown。本轮仍自述有未录制开发 pytest，不能称全过程均经记录器或证明完整开发史；五个归档 RUN 可独立核查。不要求补造历史。

## 剩余三处（均 P2，原契约要求）

### R1.1：异常实例身份仍没有测试正确的异常类型

`tests/test_depth.py:546` 的 `cycle_error = RuntimeError("sentinel-cycle")` 只验证了 RuntimeError 透传；T0008 的循环错误实际是 `LogicValidationError`。只对该类型重建同消息异常的违约副本仍 **53 passed**，见 [reconstruct_logic_error](../review-r2-probes/reconstruct_logic_error.stdout)。

仅在 `test_d2b_exception_instance_identity`：将哨兵改为 `LogicValidationError(DCE)`；相应 `pytest.raises(LogicValidationError)`，保留实例 `is` 并断言 `str(e1.value) == DCE`。DerivationLimitError 分支保留。产品当前原样传播，无需改产品。

### R1.2：重写测试时丢掉了已有的叠加错误优先级

`test_c4_validation_priority`（334–362）没有“非 ground query＋非法预算”及“C、D 同时非法”。把预算检查移到 ground 检查前，或把 D 检查放到 C 前，两种违约副本各自 **53 passed**，见 [probe findings](../review-r2-probes/findings.json)。这是原 C 组和首轮已有断言的回退，不是新要求。

仅在该函数补两例，继续使用真实调用位置的 spy：

1. 合法 world `(fact("p"),)`，query `atom("p", "?x", "?y")`，`c=0,d=-1`；完整消息必须为 `depth.query must be a ground Atom`。
2. 同一 world，ground query `atom("p")`，`c=0,d=-1`；完整消息必须为 `depth.max_fact_checks must be a non-bool positive integer; got int`。

末尾已有 `calls == []` 覆盖新例；不要删除原断言。

### R2.1：H8 的 JOIN 前提交换是一次空操作

`_swap_twin_premises`（724–731）仅在两个前提 `.args` 相同才交换；H8 的参数是 `(?x,?y)` 和 `(?y,?z)`，故整个世界原样返回。独立探针实测 `before == after` 为 True；真正交换后的产品仍返回 1。

仅去掉 `.args` 相等条件，对所有 `len(body)==2` 的规则交换。保留 helper 名字以便既定守卫定位。在 `test_depth_invariant_under_transformations` 增加 H8 fixture 自检：明确断言新末条 body 等于 `(旧body[1],旧body[0])` 且不同于旧body，再进行既有的深度不变性检查。不要只比较新旧深度，让未变换 fixture 蒙混通过。

## 验收边界与下一轮范围

新增 [独立探针](../review-r2-probes/findings.json)的三种产品违约副本均通过全部53项，证明当前残留；根工作树产品／测试未修改。不能因已给出的四个 mutation 守卫全绿就忽略契约其他项。除此之外未发现新的产品问题。

规模规则仍为固定参数的 ground COPY 特例；常量保持、重复来源、精确预算及规模目标已覆盖，变量 COPY 另有用例，不再要求为此改写测试。

- A1 的当前产品正确性判断保留，但优先级／异常身份回归待补；A2–A4 已核验范围通过；A5 尚因上述三处未通过；A6 的 Pi732项原件／冻结校验通过；A7 可核验结果通过并保留未录制历史限制。
- 下一轮只修改上述三个测试函数及一个交换 helper，产品和其余测试冻结。三个测试仍可保持原53项总数，不整文件重写。
- 运行给定新 guards：原提交完整定向套件作对照；三个产品错误副本和一个交换 helper 空操作副本仅运行受影响的三个测试。原产品应通过，错误副本应失败。**不要求重新运行全量732项，也不要求重跑已关闭的旧四个守卫。**
- 当前状态仍为 needs_changes，修复后交回复验；不 commit/push。精确步骤／命令见交接文档末尾。
