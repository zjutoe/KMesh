# T0011 第 2 轮验收（2026-09-21）

结论：**accepted，R1–R4 关闭**。本轮仅补强测试与记录，产品保持冻结；未发现新的实质问题。Codex 独立运行原 guards 的 submitted 对照 **63 passed**，五个违约副本均被对应断言拒绝。未重跑 full，沿用第 1 轮已核验的 **771 项回归**与 **3571 次有限 oracle 检查**。

## 接受版本与范围

- HEAD：`4c457e21899f81274999855d905e66b2ba574798`；分支 `T0011-clause-key`；接受的是该基线上的未提交工作树，没有 commit/push。
- 产品：`src/kmesh/logic/clause_key.py`，SHA-256 `cd5a737a44afe9f4184606e99c9aa8ac5322e91355739762d5592f9b87359084`。
- 测试：`tests/test_clause_key.py`，SHA-256 `a6aa60571d7c3e7b3ccb7060364572283a2859968de88bbd9a1439f3ce8d14f2`。
- [送审冻结记录](../review-r2-freeze/audit.json)保存五文件快照及 159 项本任务既有材料哈希；前置源码／测试、规划件和第 1 轮验收材料均核对未变。六个 Pi R2 RUN 的原始输出哈希、产品前后哈希及 preflight 测试起点一致；失败原件保留。
- 实施者为用户已授权的 Pi + `bonsai2-27b`；provider `bonsai`／reasoning `xhigh` 的来源仍按 Pi 自述记录，不冒充记录器环境快照。

## R1–R4 复验

| 项目 | 核验与结论 |
|---|---|
| R1 变换和双射 | K1–K10 三种实际变换、K3/K8 非空操作检查、README `?u/?v` 输入齐全；C 逐个实际名字映射调用产品，旧独立整数赋值 oracle 保留。关闭。 |
| R2 纯度和类型 | head/body 对象身份、全部谓词与参数字符串的有序快照前后保持不变，首尾 K3 键相等；每层 tuple 和变量真实 int 类型有效，完整自环键及 set/dict 检查通过。关闭，具体实现说明见下文。 |
| R3 诊断和隔离 | 十一种非法输入比较完整消息；生成器不消费、巨整数限制恢复保留。九根自检与占位包下真实子模块 import 均核对完整 sentinel，清理后实际执行三例并扫描全部模块。关闭。 |
| R4 记录 | 原 R4 四项更正已经追加，历史自述边界保留；本轮尚有命令／哈希文字误差，由以下 Codex 补充说明纠正，不要求单独返工。关闭。 |

纯度测试实际比较的是完整内容快照与 `hash(pre_terms)`，结构副本在调用后构造；**没有直接保存并比较 `hash(clause)`，也不是在调用前构造副本**。这与返工建议的具体写法不同，但冻结的 Atom/Clause 类型只有已快照的内容字段，head/body 身份与全部字段／顺序不变已覆盖实际输入改写，因此不构成剩余实质缺口。保留旧的恒真断言不产生额外证明力；新快照断言才是关闭 R2 的依据。

独立只读审阅代理 `/root/review_t0011_scope` 对本轮差异与原合同给出相同结论；主审另执行下列记录化验证。代理没有执行测试或修改任何文件。

## 独立验证结果

[guards.json](../review-r2-guards/guards.json)及同目录各副本 stdout/stderr 保存真实结果。测试使用隔离源码／测试副本和独占 basetemp，未更改工作树产品／测试。

| 副本 | pytest exit | 实际结果及对应断言 |
|---|---:|---|
| submitted | 0 | 63 passed in 0.21s，无 skip/xfail |
| diagnostic_suffix | 1 | 11 failed / 52 passed；D 组完整消息比较 |
| float_variable_number | 1 | 1 failed / 62 passed；`test_R2_key_type_structure` |
| conditional_reverse | 1 | 5 failed / 58 passed；三变换矩阵及 K3 真实逆序 |
| no_reverse | 1 | 13 failed / 50 passed；锚点、变换矩阵、oracle 等 |
| drop_duplicate_premises | 1 | 2 failed / 61 passed；完整锚点及前提数量不等价 |

五个失败均由预期断言触发，不是收集或导入错误。原件对照与各副本 stderr 为空。提交代码的定向回归已包含在 submitted 中，本轮未再重复跑一次相同 focused。

命令（全部经原记录器，新 RUN）：

```bash
.venv/bin/python reports/T0011/record_check.py review-r2-freeze -- .venv/bin/python reports/T0011/review-r2/audit.py freeze
.venv/bin/python reports/T0011/record_check.py review-r2-guards -- .venv/bin/python reports/T0011/review-r1/guards.py reports/T0011/review-r2-guards --enforce
```

文档落盘后用同记录器的 `review-r2-close` 运行 `audit.py close`，检查接受哈希、旧材料、链接／文本卫生、状态一致性，并生成本轮 final-audit.json；结果以该 RUN 原件为准。

## 记录补充说明（保留 Pi 原件）

本轮实存 **6 个 Pi RUN：4 个成功、2 个失败**，不是聊天摘要所写的 docs 首次通过：

| RUN | exit | 事实 |
|---|---:|---|
| pi-r2-preflight | 0 | `record.json.argv` 实际为 `.venv/bin/python reports/T0011/review-r1/check_rework.py preflight`，符合返工契约；交接执行记录写成旧 `run_checks.py ... preflight` 是文字错误 |
| pi-r2-focused | 1 | 62 passed / 1 failed；对无变量 K7 断言必须发生改名，属于测试错误 |
| pi-r2-focused2 | 0 | 修正只对含变量的子句检查实际改名，63 passed |
| pi-r2-guards | 0 | submitted=0，五个错误副本=1；与本轮独立复跑相符 |
| pi-r2-docs | 1 | 误用旧驱动，旧范围检查拒绝已有 Codex 验收文件 |
| pi-r2-docs2 | 0 | 使用正确 `check_rework.py docs`，5 文档／72 本地链接检查通过 |

Pi 第 2 轮交接已记录 docs 的失败与纠正；聊天摘要仍过时。`pi-r2-guards/provenance.md` 写于 docs 前，只列前四个 RUN；其 Test SHA-256 行缺字，正确完整值以上述实际文件和 record.json 为准。该 provenance 的旧 R1 汇总只给总数及失败项，完整 13 RUN 索引以保留的 [第 1 轮审计](../review-r1-freeze/audit.json)为准。本次不修改这些历史文件，也不把缩短哈希作为版本标识。

实现状态中“三种违约副本仍通过现有39项”的表述属于上一轮，现已更新。引用第 1 轮 771 项结果仅覆盖当时套件，本轮新增 24 项由独立定向 63 项核验，不声称已执行 795 项全量。

## A1–A7 与研究边界

A1 接口／类型／诊断、A2 等价关系、A3 算法／纯度、A4 有效守卫、A5 冻结范围／回归、A6 文档边界、A7 原件与更正均满足本任务验收。原第 1 轮临时修复脚本正文未归档、环境来源及状态切换时点无法由记录器文件内容快照独立还原的限制继续保留。

本次完成的是**单条 clause 的内容身份键**，仅消除变量改名与双前提顺序差异；完整证明身份／唯一性、motif、world 审计和训练实验仍未完成，不能据此推断 LLM 局部更新假设成立。
