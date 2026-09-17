# T0006：Codex 第 2 轮复验

日期：2026-09-17。结论：**needs_changes**。产品仍未发现实质逻辑错误，返工缩小为两个测试 fixture 和少量记录更正。

## 验证与已关闭项

- review-r2-freeze 退出 0：产品 SHA-256 保持 008bdd3633a5d2327cd711b7c9de7149df86b588632db659a23bf34207963daa，测试为 21e099b8939e35f90e188062973d0b5e553e07e50f86127441d399a8848897c3。六个 Pi R2 RUN 的日志／前后源码哈希一致，失败输出支持先失败再修复的叙述。
- 对照第 1 轮冻结清单，旧报告变化仅根 provenance.md 的追加更正，原文字节前缀保留；旧 RUN、记录器和 Codex 第 1 轮审阅产物未覆盖。当前冻结 721 个历史报告文件，原有跟踪源码／测试／AGENTS／依赖未改。
- review-r2-full 退出 0：**438 passed in 4.05s**，无 skip/xfail；六文件完整回归，独占 basetemp。
- review-r2-probes 退出 0：两套 guard 的四类根与子模块阻断、无近似前缀误伤、autouse 导入状态恢复通过；C 组合法／坏 JOIN、双射改名、三个预算／构造优先级测试通过。两个剩余缺口经内存变体复现，不修改源码／测试。
- 非实施作者 /root/review_t0006_tests 独立只读复验，同样确认下述两个 fixture 问题，其余指定测试修复可接受。

R1 隔离守卫关闭，A6 通过。R2 的 C 组及改名已修复；R3 的异常顺序、七条巨整数诊断和 4300 恢复已补。R4 的 README 默认预算／命令与首轮历史更正已落实，不要求重做这些部分。

## R2 剩余（P2）：引用不足仍有其他失败原因

[tests/test_proof.py:252](../../../tests/test_proof.py#L252) 的世界是 JOIN 得到 r(a,c)，提交的结论与 query 却都为 r(a,b)。删掉第二个引用后，head 的 ?z 又没有绑定。即使错误实现放行前提不足、按 zip 截断检查，仍会因错误 head 返回 False。

动态证据：把产品的引用数校验在内存中从“不相等”改成“仅过多时拒绝”，当前测试仍通过。用 head 变量均来自第一前提的双前提规则，完整证明 True、仅删一个引用 False，则能拒绝该错误实现。

最小修正：p(a,b)、q(b,c)，规则 p(?x,?y), q(?y,?z) -> r(?x,?y)。保留两条合法事实步骤，完整规则步骤引用 (0,1) 时 True；只将此步骤引用改成 (0,) 时 False。query 和提交结论始终 r(a,b)，其他字段不动。

## R3 剩余（P2）：大正 premise 引用未到达索引检查

[tests/test_proof.py:928](../../../tests/test_proof.py#L928) 在 FACT 上放一个大正引用。实现先因前提数不符返回 False，完全没有执行 ref >= i。

动态证据：在内存中于 ref >= i 前插入 str(ref)，制造超过 4300 位时会逸出 ValueError 的错误实现；当前测试仍通过。合法 FACT＋单前提 COPY 的正确 fixture 可发现该缺陷，当前真实产品则正确返回 False。

最小修正：p(a,b) fact、p(?x,?y) -> q(?x,?y) COPY。两步证明中第一步为合法 fact，第二步指 COPY；引用 (0,) 时 True，只改为 (10**5000,) 时 False。保留 int_limit_4300 fixture 与恢复逻辑，其余字段、前提数量和最终 query 都合法。

## R4 剩余（P3）：新记录中的小范围错误

- pi-r2-full/provenance.md:31 与交接 R2 执行记录将四类根写成包含 kmesh.utils.environment，却漏了 yaml。实际为 torch、yaml、kmesh.logic.engine、kmesh.logic.reference_engine。
- 巨整数专组实际共 10 个测试：7 条诊断＋3 条正值路径，不是“10 条诊断再加 3 条”；其中正 premise 路径本轮仍未有效覆盖。
- pi-r2-full/provenance.md 的两处 ../../provenance.md 指向不存在的 reports/provenance.md；同任务根 provenance 的相对路径是 ../provenance.md。第 1 轮探针脚本实际为 reports/T0006/review-r1/probe.py，不是 review-r1-probes/probe.py。
- 交接 R2 RUN 清单把 pi-r2-diff-check 写成已包含卫生脚本，但该 record.json 仅执行 git diff --check；卫生脚本实际在 pi-r2-diff-check-r2 执行。新 provenance 表格本身已正确区分。

不要改写已冻结 R2 证据；在新 full/provenance 与新一轮执行记录中追加更正，提供可解析链接。新记录的链接检查需覆盖该新 provenance。这些是文档准确性问题，不表示产品导入了错误依赖或测试日志虚假。

## 验收范围

- A1–A4 先前产品核验继续有效；源码未变，未重复扩大产品审查。
- A5 等待上述两个有区分力 fixture；A6 本轮通过；A7 等待小范围记录更正。
- 本轮没有改产品或测试、没有 commit/push；修复后的两个 fixture 已在独立探针中验证真实产品的预期行为，不需人为制造产品失败。
