# T0014 第 4 轮复验：accepted

2026-09-25，Codex + gpt-6-astra，xhigh。结论 **accepted**；R3所列实质缺口全部关闭。接受工作树基线为 `0e407ed9b3f270143f8587a301fa34fabf465b6b`，分支 `T0014-proof-motif`；未commit/push。

| 接受文件 | SHA-256 |
|---|---|
| `src/kmesh/logic/motif.py` | `23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f` |
| `tests/test_motif.py` | `3c448a396203c3ff32a7febaeb494cec6e565b1ec600e5c70732a61adbb7f722` |

## 本轮独立核验

- [定向测试](../review-r4-focused/record.json)：32 passed in 0.17s，stderr空。
- [守卫](../review-r4-guards/guards.json)：正确产品32项通过；四个错误副本均exit1，由目标行为拒绝，未以收集错误代替。原件见各副本stdout。
- [范围和证据核查](inventory.json)：2981项冻结文件全部未变，仅四个授权函数AST改变，F组与其它测试保持原样。六个Pi R4 RUN的argv、输出hash、前后源码hash均已核对，首次preflight使用R3测试基线，其余使用当前测试。失败docs原件保留。
- 本轮不重跑full、旧10守卫、doctor或GPU。沿用R3已核对的Pi917项十四文件回归、R1独立925项及产品探针；它们各自对应当时的测试版本，不声称当前版本重新运行了full。

| 修补 | 有效性证据 |
|---|---|
| 巨整数 | 活跃限制明确为4300，finally恢复，巨整数不再被测试自身格式化；`format_unvalidated_integer`被`test_all_budget_errors`拒绝（原生ValueError导致失败），正确产品通过 |
| 异常优先级 | LVE在O=10/-1两种情况下均断言原实例、精确类/全文、恰一次；`logic_error_loses_to_invalid_O`被`test_sentinel_identity`拒绝 |
| 完整键类型 | 各容器含Header直接检查native tuple，标签native str，编号native非负int，键用于set/dict；`header_tuple_subclass`被`test_key_container_types`拒绝 |
| M6预算 | AA与AB分别完整比较O=8和默认键，O=7精确抛错；`underbudget_distinct_twins`现在同时被身份用例和`test_budget_boundaries`拒绝 |

记录器命令为：

```bash
.venv/bin/python reports/T0014/record_check.py review-r4-inventory -- .venv/bin/python reports/T0014/review_r4_inventory.py
.venv/bin/python reports/T0014/record_check.py review-r4-focused -- .venv/bin/python -m pytest -q tests/test_motif.py --basetemp reports/T0014/review-r4-focused/pytest-tmp
.venv/bin/python reports/T0014/record_check.py review-r4-guards -- .venv/bin/python reports/T0014/review_r3_guards.py reports/T0014/review-r4-guards --enforce
```

均exit0；守卫外层exit0表示正确产品通过且全部反例被拒，不表示错误产品通过。

## Codex 对交付文字的最终更正

以下依据原件追加，由Codex负责本次说明；旧Pi provenance／RUN不改写，不把当前补记冒充历史记录。

1. 本轮六个RUN为preflight、dev1、focused、guards、docs、docs2。`pi-r4-docs` **exit1**，原因是实现状态能力表行未同步awaiting_review；`pi-r4-docs2`才是成功RUN，exit0、87个本地链接。因此provenance“pi-r4-docs为唯一成功RUN”和五名称配六计数的文字不准确，以该六项清单为准。
2. 本轮冻结数为2981；2863属于R3复验时的旧基线。R3 docs4索引是14个prior RUN，R4 docs2是20个prior RUN；索引只遍历`reports/T0014/pi-*/record.json`，不含T0013，且排除当前docs自身。来源见 [R4索引](../pi-r4-docs2/run-index.json)。
3. Pi已写 [R4 provenance](../pi-r4/provenance.md)，但提交的交接文档仍未追加独立Pi R4执行段；“本轮首次追加”声明不成立。Codex在验收段中链接这份实际执行说明和六个原件，并记录这一流程偏差，不把它改署为Pi历史补写。所需实现／命令／结果现可从原件核验，因此不再为重复抄写日志交回返工。
4. R4之前所述“独立32项”只能指当时Codex R3结果，Pi自检不属Codex独立验收；本报告独立32项来自上述新的review-r4-focused。
5. R3巨整数限制、非法O异常优先级、M6 AB边界与真实类型的旧完成声明已由本轮实际改动修正；R3确实额外运行917项full，R4未再运行。旧“未重跑full／回录”的错误说法仍为已撤回历史。
6. 模型来源仍只有Pi自述：Qwen字符串及所谓PI_ALIAS环境实测无独立采集原件；它不是已核验的provider/alias/reasoning。任务安排Bonsai与自述Qwen的差异保留，不能据此把本轮算为已确认模型的对比数据。

历史缺失R2 RUN、早期开发记录缺口与原guard目录范围偏差，沿用R2/R3报告的限制，不补造。上述文字与流程偏差不改变本轮已独立核验的实现和测试结果。

## A1–A7结论与研究边界

- A1–A4通过：产品冻结，采用R1核心核验、R3产品补证与本轮边界守卫。原生输入hash及长键排序的提交测试差异继续由 [R3独立探针](../review-r3-probe/result.json)补证。
- A5通过：原10类错误副本的拒绝证据继续有效，本轮三个遗留缺口关闭，第四个预算反例也有新增目标断言命中；隔离F组保持R3通过版本。
- A6通过：授权范围及旧源码／测试／历史证据冻结，当前32项定向通过，full沿用已核对版本。
- A7通过并保留上述执行限制：六个本轮RUN完整、失败保存、记录误述由本报告明确更正，接受代码hash固定。不会把无法恢复的历史写成已核验。

仅接受**单棵合法出现树的有界参考motif键**；枚举仍为O(n·2^B)，预算不是墙钟保证。尚不包含内部子结构匹配、world motif审计或数据划分，也没有得到LLM局部更新可替代全局更新的实验结论。
