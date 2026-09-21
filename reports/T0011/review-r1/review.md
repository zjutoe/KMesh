# T0011 第 1 轮验收（2026-09-21）

结论：**needs_changes**。产品未发现缺陷；测试有可实证的合同缺口，返工冻结产品，只补测试及相关文档。实施者按用户已授权切换记录为 Pi + `bonsai2-27b`（其执行记录列 provider `bonsai`、reasoning `xhigh`）；不因原规划写 Qwen 判定违约。

## 独立核验

- HEAD `4c457e21899f81274999855d905e66b2ba574798`，分支 `T0011-clause-key`；未 commit/push。
- 产品 SHA-256：`cd5a737a44afe9f4184606e99c9aa8ac5322e91355739762d5592f9b87359084`。
- 被审测试 SHA-256：`a1024156645a2c02622b19f401cbabc21b266d3b2be4a4b97b31366a0c7a200d`。
- [冻结记录](../review-r1-freeze/audit.json)：26 项规划冻结件与既有源码／测试未变；保留送审五文件快照，核验 74 项历史文件。13 个 Pi RUN 的 stdout/stderr 与记录内哈希一致；preflight 前后产品／测试确实不存在。
- [十一文件全量](../review-r1-full/stdout.txt)：Codex 独立 **771 passed in 15.08s**，stderr 空，无 skip/xfail。
- [独立有限 oracle](../review-r1-probe/probe.json)：**3571 次 clause 检查**，其中含 600 对改名＋前提逆序对照；另核验 11 种非法输入的完整消息。oracle 枚举变量到整数的所有双射及 body 排列，未导入送审测试或产品私有 helper；seed `20260921`。全部通过。
- 静态审阅确认最多两个候选、每候选独立编号、head 优先、重复槽位保留、无世界求解或 IO。独立只读审阅代理 `/root/review_t0011_scope` 对原合同和送审实现／测试也未发现产品错误；其意见由 Codex 主审以如下探针核验。

上述是有限验证，不是所有输入的形式证明，也不构成证明唯一性或研究假设成立的证据。

## 需要返工

### R1（P2）：补齐实际变换矩阵和变量双射调用

定位：`tests/test_clause_key.py:243` 附近的 `_rename_clause` 与 C 组。当前只对六个 fixture 各做一种 `?w0...` 改名，没有原合同 B 的 K1–K10「改名／前提逆序／二者组合」矩阵；C 枚举了数值编码，但没有逐双射改成实际合法变量名后调用产品。

隔离错误副本 `conditional_reverse` 将候选条件改为 `len(body) == 2 and body[0].pred <= body[1].pred`：对反序 JOIN 会漏掉应考察的候选，但现有 **39 项全部通过**。补齐原合同矩阵即可抓住它。README 的 COPY `?u/?v` 示例也纳入实际测试输入，不能只声称相同输入。

### R2（P2）：纯度和返回类型必须可判错

定位：`tests/test_clause_key.py:191`。`K3.body == K3.body` 恒真；没有保存输入内容／顺序／hash，最后两次 K3 相等也不能证明与第一次相等。只有 `isinstance(key, tuple)`，没有验证嵌套容器与变量编号的真实类型。

隔离错误副本 `float_variable_number` 返回 `("v", float(number))`，违反整数编号契约，但 Python 的 `0.0 == 0` 使现有 **39 项全部通过**。补调用前后快照、K3→K0→K8→K3 首尾键相等、全层 tuple 及 `type(number) is int` 检查。

### R3（P2）：精确诊断与隔离守卫自检

定位：`tests/test_clause_key.py:268–305`、`:340–346`。D 组 `match=re.escape(...)` 没有锚定，只验证子串；E 组只尝试根名，而且任意 ImportError 都算成功，没有实测点前缀分支。

隔离错误副本 `diagnostic_suffix` 为约定消息追加 ` EXTRA`，现有 **39 项全部通过**。D 组捕获异常后比较整条 `str(exc.value)`；E 组检查守卫特有原因，实际触发根及子模块拦截，保留现有实际三例计算及最终全模块扫描。

### R4（附随记录更正，不单独阻塞验收）

1. 当前实存 **13 个 RUN、13 份 provenance**；其中 9 个 exit 0、4 个失败（focused=2、fix1=1、focused-2=1、docs=1）。`pi-r1-docs3` 输出的 15 文档对应检查当时 12 份 provenance 加三份主文档；它自身的 provenance 在该 RUN 后写入。不能把该时点计数写成最终总数或声称该 RUN 已检查自身事后生成的文件。
2. 原交接记录写 docs 为 `not_run` 是落盘时状态；追加说明实际 docs→docs2→docs3 为 1→0→0。首个 docs 失败原因为当时缺 provenance。保留原记录，不回写旧 RUN。
3. 首轮 full provenance 只有本 RUN 信息，没有合同要求的全部尝试摘要；本次在新 R2 provenance 中合并旧 13 RUN 与本轮 RUN 索引即可，不要求为旧 RUN 补造文档。
4. `/tmp/t0011_fix.py` 在两个 RUN 中使用同一路径，历史脚本正文未归档；退出码、输出、测试前后哈希可核验，但“只改某正则”的逐行脚本改动是 Pi 自述。执行环境变量没有被记录器快照捕获，provider/reasoning 的获取方式亦按 Pi 自述区分；模型切换本身有用户授权。

## 错误副本的原始结果

[guards.json](../review-r1-guards/guards.json) 与同目录 stdout/stderr 保存全部结果；只在各自 `pytest-tmp` 副本变更，工作树产品／测试未改。

| 副本 | pytest exit | 结果 |
|---|---:|---|
| submitted | 0 | 39 passed，原实现对照 |
| diagnostic_suffix | 0 | 39 passed，诊断守卫缺口 |
| float_variable_number | 0 | 39 passed，真实类型守卫缺口 |
| conditional_reverse | 0 | 39 passed，前提交换守卫缺口 |
| no_reverse | 1 | 已有锚点能拒绝完全移除逆序候选 |
| drop_duplicate_premises | 1 | 已有锚点能拒绝删除重复前提 |

外层 guards RUN exit 0 表示检查成功完成；不表示错误副本被全部拒绝。返工用同脚本 `--enforce`，要求原件通过且五个错误副本全部 exit 1，另人工确认分别由相应测试断言拒绝。

## A1–A7 裁定

| 项 | 本轮结果 |
|---|---|
| A1 | 产品 API／格式／诊断通过独立核验；对应回归守卫待 R2/R3 |
| A2 | 手算锚点／独立有限等价对照通过；测试变换覆盖待 R1 |
| A3 | 产品算法符合；纯度回归断言待 R2 |
| A4 | 未通过：三种违约实现存活，隔离自检不完整 |
| A5 | 771 项独立回归通过，前置冻结范围未变 |
| A6 | 研究边界清楚；README 输入对齐待 R1 |
| A7 | 现存失败原件留存、preflight 顺序和 basetemp 可核验；R4 汇总／时点说明待补。状态先行的文件内容没有时点快照，按 Pi 自述保留，不声称已由哈希证明 |

返工步骤及准确命令见 [交接文档](../../../docs/handoffs/T0011-clause-key.md)。下轮保持产品不变时，只需定向套件、五种违约守卫及文档／冻结检查，沿用本轮 771 项回归，不重跑全部旧测试。
