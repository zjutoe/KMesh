# T0010 第 3 轮验收，2026-09-20

结论：**accepted**。剩余 R1.1、R1.2、R2.1 已关闭，原 R3／R4 关闭结论继续有效；当前无待修复的实质问题。Codex + `gpt-6-astra`（`xhigh`）作为非 Pi 作者复核限定 diff 并独立运行守卫，未修改产品或测试。

## 接受版本与修补核验

分支 `T0010-minimum-depth`，HEAD `153295c28788f27ef37e794c7c0ea19841accaa8`。接受的是该基线上的未提交文件，未 commit／push。

| 文件 | 接受 SHA-256 |
|---|---|
| `src/kmesh/logic/depth.py` | `0361a37e8fbfcceb69ac55336c8578176ab96f1c94a86fa50a98aaa2a839bf5d` |
| `tests/test_depth.py` | `648d815a986634ef53adfc85015bd6b8571e71fa1b134b7eb290b6d68da2ae01` |

[输入冻结与核对](../review-r3-freeze/audit.json)确认产品未变、188 项此前材料哈希一致、原规划与既有源码不变。与 R2 快照逐行及 AST 比对，测试改动仅限四个指定函数，其余测试／fixture／导入均未变。

| 原问题 | 本轮实际修补 | 独立核验 |
|---|---|---|
| R1.1 异常身份 | 改用 `LogicValidationError(DCE)`，检查异常类、实例 `is` 与完整消息；DLE 分支保留 | 重建同类同消息的新异常副本被 `test_d2b_exception_instance_identity` 拒绝 |
| R1.2 错误优先级 | 加入非 ground query 与双非法预算、ground query 与双非法预算；保留零下游调用断言 | ground 后置、D 先于 C 两个副本均被 `test_c4_validation_priority` 拒绝 |
| R2.1 H8 交换无效 | 所有双前提规则均交换；显式比较 H8 的新旧 body，随后执行深度不变性检查 | helper 空操作副本被 `test_depth_invariant_under_transformations` 拒绝 |

## 验证与 A1–A7

独立命令均通过原记录器，以全新 RUN 留存：

```bash
.venv/bin/python reports/T0010/record_check.py review-r3-freeze -- .venv/bin/python reports/T0010/review-r3/freeze.py
.venv/bin/python reports/T0010/record_check.py review-r3-guards -- .venv/bin/python reports/T0010/review-r2/rework_guards.py reports/T0010/review-r3-guards
```

[独立守卫原件](../review-r3-guards/guards.json)：原提交 **53 passed in 0.32s**；四个故意违约副本均 exit 1，分别由指定测试失败，5/5 `guard_valid=true`。这四次失败是隔离副本中的预期反证，不是提交产品失败；外层 exit 0、stderr 空。

| 验收项 | 结论与依据 |
|---|---|
| A1 接口／输入 | 通过；原 R2 边界守卫保留，本轮补齐两种重叠错误优先级 |
| A2 最短深度 | 通过；产品、H0–H12 手算断言未变，53 项套件通过 |
| A3 完整性／预算 | 通过；原预算、单次调用和 DLE 身份断言保留，补齐真正 LogicValidationError 身份守卫 |
| A4 算法／规模 | 通过；冻结产品，1200 长链、16 层重复来源仍在本轮定向套件中通过 |
| A5 测试可信 | 通过；H8 实际交换已证实，64 次 query／60 棵原始证明的既有对照及硬隔离继续有效；对照共享 T0008，不是独立验证其全部语义 |
| A6 回归／范围 | 通过；四函数限定 diff，旧源码不变。沿用已核对原件／哈希的 Pi R2 **732 项**完整回归；本轮只独立跑当前 53 项及新守卫，没有重跑全量 |
| A7 交付证据 | 当前验收证据可核验，以下历史限制明确保留；不声称历次执行完全合规 |

Pi 的 preflight、dev1、guards、docs 共四个 R3 RUN 均核对 exit 0、原始输出哈希及前后源码快照；preflight 对应旧 R2 测试，其余对应接受测试。首轮 Codex 的 719 项完整回归和第 2 轮旧守卫证据保留为各自时点结果。

## 记录澄清与限制

以下为 Codex 对 [Pi R3 provenance](../pi-r3-guards/provenance.md)和交接记录的追加澄清，原件不回写；不要求再为文字进行一轮返工。

1. 最终共有四个 Pi R3 RUN；provenance 中的“三个”对应 docs 前的记录，不能作为最终总数。`pi-r3-dev1` 确实是额外 focused，53 项通过；“未跑额外 focused”不成立。没有重跑旧 guards 或全量 732 项。
2. Pi 自述录制前运行过 `py_compile`，但无该命令的归档原件；“全部自检录制／无新增未录制开发”不能成立。编译成功、两次编辑失误及修正过程仅作为 Pi 自述，当前源码与已录制检查结果已独立核验。
3. A14＋B15＋C12＋D6＋E2＋F2＋G1 为 52，另有独立的变换测试 1 项，合计 53。总数与实际输出一致。
4. R3 执行工具／模型及“经用户确认”的表述不由记录器证明；沿用执行者自述与此前完整别名／历史映射限制，不补造服务端记录。R1／R2 未归档历史的限制不因本轮通过而消失。

验收范围仅单查询最短证明深度这一离线审计接口。规范证明身份、唯一性、motif、完整 world 审计和模型训练仍未完成；本次没有产生支持最终局部训练假设的新实验结论。
