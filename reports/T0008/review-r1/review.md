# T0008 第 1 轮 Codex 验收

2026-09-18；Codex + gpt-6-astra，xhigh；未参与 Pi 产品实施。结论：**needs_changes**。本轮未发现冻结产品的实现缺陷，返工集中于测试和文档／记录；不得据此直接接受任务。

## 冻结输入与验证

- HEAD `a9441250626f087dc8dbc1f560b7fbe3fe92488b`，分支 `T0008-ground-derivations`。
- 产品 `src/kmesh/logic/derivations.py`：`32634248f401865d068b13758e133037a7a9bc3dcfa409526bc7df86a9aaf29b`。
- 测试 `tests/test_derivations.py`：`694c255ad5251ac1813b07ec335787b96a14e33b020a6aaaf865ac081c338fc0`。
- [冻结记录](../review-r1-freeze/audit.json)保存审阅输入、历史文件哈希、每个 Pi RUN 的实际 argv／退出码／源码哈希和输出完整性；旧源码与规划基线一致，18 份 Pi record.json 的两路输出哈希均一致（含嵌套 RUN）。这证明当前可见原件的一致性，不证明所有目录从未移动或所有尝试都已归档。
- [独立全回归](../review-r1-full/)：合同文件顺序 **604 passed in 4.44s**，退出 0，stderr 空，无 skip/xfail。
- [README 顺序复现](../review-r1-readme-order/)：同一批测试按 README 顺序收集，**退出 2，1 个 collection error**，原因是 tests/test_derivations.py:33 的模块导入顺序断言。
- [独立探针](../review-r1-probes/findings.json)：seed 20260918 的 **128 个 DAG 世界、1,934 条记录**，用旧参考闭包加全变量域绑定枚举作为独立 oracle，Counter 与结论集合均完全一致；含任意 head 层事实、常量／变量混合、重复 clause 和原 clause 重排。不是正式数据生成或性能实验。
- 同一探针对两种错误实现在内存中运行实际提交测试，**各仍为 122 passed**。产品与测试文件始终未修改，两个缺失正例在冻结产品上均通过。
- `/root/review_t0008_design` 对原契约和提交测试作非作者只读审查；主代理用上述变异验证其关键发现。

## R1（P2）：隔离测试破坏收集顺序，且未检查子模块

位置：`tests/test_derivations.py:26–33, 672–744`；README 测试命令见 `README.md:183`。

模块顶层的 sys.modules 断言会拒绝其他测试先合法导入 engine/reference_engine/proof，导致 README 命令不能执行。它检验的是整个 pytest 进程历史，不能证明新产品是否引入了这些依赖。

现有子进程只把五个根设为 None、最后检查根值，缺少契约指定的 finder、自检和全部子模块扫描；临时脚本还写入 tests 目录。[修正后的隔离探针](../review-r1-isolation-probe/findings.json)在最终扫描**之前**插入禁用子模块，提交脚本仍打印 ISOLATION_OK，而完整子模块扫描对照退出 1。

最小修复：删除顶层断言；在干净 `python -c` 子进程里用 finder 阻断五个精确根及点前缀子模块，对每个根显式 import 并断言 ImportError 自检，再执行 API 例子／超限路径；最后扫描全部 sys.modules。不要清除或伪装其他测试合法导入的模块，不靠调换 README 顺序规避问题，不写共享 tests 临时文件。

## R2（P2）：两个关键匹配规则缺少能识别错误实现的测试

1. `tests/test_derivations.py:298–307` 的所谓 empty_binding 例使用 `?x/?y/?u/?v`，绑定非空。内存变异把双前提路径两处 None 判断改成真值判断后，仍为 **122 passed**。应保留当前独立变量例并准确命名，另加原契约的 `p(a,b), q(c,d), [p(a,b),q(c,d)]→r(e,f)`，完整三记录、C=2／D=3 及 C−1／D−1 超限。
2. `tests/test_derivations.py:261–272` 的候选按 args 排序后先成功后失败，且失败未先写入新变量；其他 JOIN 例的新变量值也不足以区分绑定共享。内存变异将 `binding = dict(partial)` 改成 `binding = partial` 后，仍为 **122 passed**。加 `p(a,b), q(b,c), q(b,d), [p(x,y),q(y,z)]→r(x,z)`，完整五记录且含 r(a,c)/r(a,d)，C=3／D=5。再将原“失败后成功”例改成 `p(a,b),q(c,a),q(d,b), [p(x,y),q(z,y)]→r(x,z)`：第一个 q 先绑定 z=c 后因 y 冲突失败，第二个 q 必须独立得到 z=d；完整四记录、C=3／D=4。

同轮补原契约的有限边界遗漏：max_derivations=True／1.5、`enumerate_derivations(10**5000)`、负巨整数 max_derivations，均断言完整目标诊断；将“cycle + 坏成员”fixture 的坏成员移到循环规则之后，完整断言相应成员路径／原因。沿用局部 4300 上限恢复，避免格式化巨整数。

无需改产品、改弱旧断言或扩大随机框架。64 世界实际精确 tuple 比较可检查完整内容和重复输出，借用已验收拓扑顺序不削弱其来源预期；无需仅为 Counter 形式返工。

## R3（P2）：README 反向描述预算边界和候选顺序

位置：`README.md:159`。当前写“任一预算恰好耗尽时……抛”，而契约／实现是**恰好完成可成功，仅再需操作时超限**；“候选首现序”也应为桶内 args 字典序。只改这两处行为说明，保留直接推导不是完整证明的边界；返回状态和真实测试结果同步即可。

## R4（P2）：执行摘要多处与原始 RUN 相矛盾

位置：`docs/handoffs/T0008-ground-derivations.md:202–225`、`reports/T0008/pi-r1-full/provenance.md:6–18`。在**新** provenance 和追加 Pi 记录中更正，旧 RUN／provenance 不改写，不移动任何目录：

| 原表述 | 原件可核查事实 |
|---|---|
| 相对 `.venv/bin/python` 在 shell=False 下不能用，全程绝对路径 | `pi-r1-preflight-dev1` 08:59 UTC 使用相对解释器，退出 0；`preflight-verify-dev1` 09:01 也退出 0。裸 python 的首次 focused 无 kmesh；两个 launch 127 是把脚本放在 argv[0]，不是相对解释器解析失败。 |
| pi-r1-preflight 是版本探测，exit 0 | 现 `pi-r1-preflight` 12:23 实际执行 check_preflight.py，exit 1；`pi-r1-preflight-verify` 12:24 也 exit 1，因为新源码已非 null。原先真正开工前的成功版本／基线检查在上述两个 dev1 目录。 |
| focused-dev1 是 helper 参数错误 | 外层 dev1 是裸 python 无 kmesh；helper 构造错误在嵌套 `pi-r1-focused-dev1/pi-r1-focused/`，应分别列明。 |
| bucket 缺陷 dev4→dev5 修复 | dev2 产品为 `19a9ccc4…`，原输出含下游记录缺失；dev3 起已是当前 `32634248…`，dev4/dev5 产品也相同。可确认源码更改在 dev2 与 dev3 之间，不能写在 dev4→dev5。旧源码未归档，不能据此宣称完整恢复所有实施细节。 |
| “失败先保存”允许改名后复用合同 RUN | AGENTS 与原契约明确禁止移动／重用，包括成功 RUN。现目录结构和 Pi 自述表明这不是合规做法；具体 mv 命令／动作历史没有归档，按自述／unknown 说明，不反向移动以修饰历史。 |
| 开发命令／basetemp 均按契约 | focused dev 链额外运行 dependency，共 166 项；使用同一 `pi-r1-basetemp`，不是每 RUN 独占。最终合同 full 13:47 早于 focused 13:49，需如实说明实际顺序，dev7 的 166 项不能称最终 full。 |
| 每 RUN 有 command.json、run.env | 实际记录器为 record.json、stdout.txt、stderr.txt；argv／退出码／19 项哈希在 record.json。不要列不存在的文件。 |
| C/D=0/1 只测合法最小预算是偏差 | 原契约本就如此规定；属于合规处理。64 世界使用 tuple 而非 Counter 是等效实现差异，区别于留证违约。 |

按原件列出实际开始／结束时间和 elapsed_s，区分原始证据、Pi 自述及未知。现有失败记录保留有价值，但不能把不准确摘要写成全部过程合规；本轮不要求补造历史。当前产品可复验与历史记录是否充分分开判断。

## 各验收项与复验范围

| 项 | 本轮结果 |
|---|---|
| A1–A4 | 冻结产品审阅、完整回归和独立 oracle 范围内通过；未发现实现缺陷 |
| A5 | needs_changes：测试顺序故障及两个有实证的匹配覆盖缺口 |
| A6 | needs_changes：产品依赖合规，但隔离守卫不满足契约 |
| A7 | needs_changes：README 行为说明和执行记录须更正 |

返工限 tests/test_derivations.py、README、实现状态、交接的状态／追加记录、新 pi-r2* 材料；产品和全部历史证据保持冻结。准确步骤和复验命令见交接末尾的第 1 轮返工要求。

## Codex 自检说明

最初 review-r1/probe.py 的子模块注入放在最后扫描之后，那个隔离子探针不足以支持诊断；已保留原件，并用独立新 RUN `review-r1-isolation-probe` 在扫描前注入及完整扫描对照更正。原 RUN 的 128 世界 oracle 与两项匹配变异结果有效。未修改产品／测试，未 commit/push。
