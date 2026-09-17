# T0007：Codex 第 1 轮验收

2026-09-17。结论：**needs_changes**。未发现产品逻辑缺陷；只需补强一个测试的诊断断言，并更正执行记录。产品冻结，不要求重写实现或扩大功能。

## 已完成核验

- [输入快照](../review-r1-freeze/audit.json)：dependency.py SHA-256 `4b01df6f08e243c649f0459a23e6e8a68f946fc0eec41814f889e65cd972ca3f`；test_dependency.py 为 `a4e428e9d1acc99a7dc3e01e725e7b3da8d009c8f1c39eeac957b8dd57d7e09c`。旧跟踪代码／测试和规划冻结文件未改，六个 Pi RUN 的日志哈希、前后源码快照相符；冻结 832 个历史报告文件。
- [独立完整回归](../review-r1-full/)：严格使用交接七文件命令、独占 basetemp，退出 0，**482 passed in 4.30s**，stderr 为空，无 skip/xfail。
- [独立探针](../review-r1-probes/findings.json)：枚举三个命名顶点上全部 512 个有向图（含自环），用顶点排列穷举作为独立预期，25 个 DAG 的完整顺序、487 个循环的拒绝均正确；README 新例实跑通过。本探针只覆盖该有限规模，不证明完整数据审计或研究命题。
- 源码审阅确认：先验证全部成员，全部谓词入图、前提→head、去重入度、最小堆动态选点、全图循环拒绝、迭代与纯函数边界符合契约。既有隔离测试和 1200 节点链通过。
- 非实施作者 `/root/review_t0006_tests` 独立只读审阅产品／测试，同样未发现产品问题，确认下述 R1；A7 由主代理检查原始记录。

## R1（P2／A5）：generator 拒绝用例缺完整原因断言

[test_dependency.py:276](../../../tests/test_dependency.py#L276) 只检查字段名与生成器未消费，没有检查 `must be a tuple of Clause`；前面参数化的 `iter([_VALID])` 是 list_iterator，不能覆盖 generator 分支的诊断。

已动态验证：内存中只将 generator 的异常改成 `LogicValidationError("dependency.clauses: rejected")`，现有测试仍通过。真实产品的诊断正确。最小修复是在同一测试保留字段／未消费断言，补 `must be a tuple of Clause` 与 `got generator` 两个完整片段。不增加测试数量、不改产品。

非阻塞注释问题：谓词改名例 a→m 后的 m/b/z 恰好仍等于原顺序逐位改名，注释“Not a position-wise mapping”不准确。可删这句，不要求改 fixture 或增加新门槛。

## R2（P2／A7）：记录与原始证据不一致

1. [provenance 第 6 行](../pi-r1-full/provenance.md#L6) 写 torch 2.9.1+cu128、CPU 机器；实存 [doctor JSON](../pi-r1-full-doctor.json) 是 **2.10.0+cu126**。进程中不可见 CUDA 不能推出机器没有 GPU。
2. [第 22 行](../pi-r1-full/provenance.md#L22) 将 cpu_only 归因于“共享 GPU 瞬时抖动”。该 RUN 的 [record.json](../pi-r1-full/record.json) 明确设置 `CUDA_VISIBLE_DEVICES=""`；cpu_only 与隐藏 CUDA 一致，现有证据不支持抖动归因。提交目录仅有这一份 cpu_only 报告，未发现“三次 status=ok”的命令／输出／环境记录；这些目前只能列为自述，不能称“如实双留证”。已请求补充原始位置，不能靠新跑 doctor 冒充历史。
3. 声称“除入口误写外无契约偏差”不成立：所有 Pi pytest 命令都缺独占 `--basetemp`；full 改为 `pytest tests -q` 并串接了任务外 doctor。两个 full 的原始 stderr 含共享 `/tmp/pytest-of-mye` 清理警告，必须保留。不能将这些命令称为四条契约命令原样执行；Codex 已按原命令独立复跑，当前没有产品回归阻塞。
4. “改名留存”与记录器独占 RUN、不得移动旧 RUN 后复用名称的要求不一致。现有文件能核对当前日志和哈希，不能单独证明之前是否改名、原名是什么或是否复用；应准确说明实际动作／无法核验的部分，不将改名自动写成合规留证，也不要再搬回或重建旧目录。
5. `pi-r1-diff-check-r2` 实际只做 diff 和聚焦测试，没有文档链接／新文本检查；不等于完成全部卫生检查。当前 `git diff --check` 本身也不会检查未跟踪的新文件。记录器的 `elapsed_s` 与首末时间相减不同（例如 full 为 6.428s，表里 6.441s 是首末时间差），两者要正确命名；17 项快照包括记录器，旧的 15 项不是全部“已跟踪产品／测试”。测试分组是 9＋8＋8＋15＋2＋2＝44，变换／纯度含长链共 8 项。

原报告／RUN 原样冻结。在新一轮 provenance 和执行记录追加更正、区分事实与自述；撤回 README 的“合同 RUN 全绿”和交接的“无其他偏差”。缺失历史不能补造，已核实当前结果不受影响的事实也应保留。

## 验收与最小返工

A1–A4、A6 通过；A5 待 R1 的两条断言，A7 待 R2 记录更正与最终卫生检查。交接文档附准确下一轮命令：只复跑 44 项聚焦测试并检查文档／冻结范围；产品和旧回归不变时沿用本轮 482 项独立结果，不机械重复完整回归或 doctor。Codex 未改产品／测试、未 commit/push。
