# T0014 第 2 轮复验：needs_changes

2026-09-25，Codex + gpt-6-astra，xhigh。HEAD仍为 `0e407ed9b3f270143f8587a301fa34fabf465b6b`；产品 `23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f` 未变，提交测试 `0e1b16f1d617a77168337be2968d6bb25708c2cf59facd1fb0baa582a32af12a`。原件见 [快照](input-snapshot/)及 [冻结清单](frozen-inputs.json)。未改产品／测试，未 commit/push。

本轮确实修复了若干关键测试，但整文件重写同时删除／弱化了原覆盖；六个旧守卫全拒不等于原契约全部满足，状态继续 `needs_changes`。产品继续冻结，不要求重写测试文件或重跑 full。

## 已关闭与可核查结果

- [inventory](inventory.json)：R1交回的2776个冻结文件全部未变，包括产品、旧证据和两份checker。独立 [focused](../review-r2-focused/record.json) **31 passed in 0.17s**、stderr空。
- `guard-r3` 的测试hash与提交一致，七份源码副本hash与JSON一致；raw stdout显示控制31通过、六个错误副本由相应行为断言拒绝。各副本包括异常身份、方向位、消费generator、禁用枚举器和长链body的断言命中均已阅读。缺记录器前后状态／时间链的限制另述。
- 真命名空间碰撞、JOIN body/ref联合交换、M6关系改名、M7实际 p→q→p 与 p→q→r 区别、长链全部body内容已经补上。
- 本轮不再运行旧产品探针、旧六守卫或full：产品未变，沿用R1独立925项full及产品核验。本轮Pi所述916项full没有找到原始RUN，不计入独立或已核查结果。
- 非作者 `/root/design_t0012` 对原契约和本轮测试作只读静态审阅，未运行检查；其覆盖发现与主代理核对后归入下述三组。

## R1（P1）：子模块隔离自检仍会漏过错误 finder

定位 `tests/test_motif.py:609–691`。

1. 现在已有主动阻断且保持到计算后，是真实进步。但 `import root.submod` 时 root 并未在 sys.modules 中，实际先被根名拦截；`str(e)`只查通用片段，无法证明点前缀分支被执行。必须按原契约安装该 root 的临时占位包＋空 __path__，实际导入 `root._t0014_probe`，精确比较包含完整子模块名的异常全文，finally清理。
2. `Path(__file__).resolve().parents[2] / "src"` 错了一层，实际应为 parents[1]/src；没有对 `motif.__file__` 做精确resolved路径断言。当前通过可能依赖cwd／editable安装，不证明运行的是指定副本。
3. 异常可改为单参数 `ImportError("t0014-blocked: " + fullname)`，根和子模块均比较完整字符串；现有双位置参数 ModuleNotFoundError 的str是tuple式内容，勿只匹配片段。保持现有匹配条件，补真实自测即可。

独立 [额外守卫](../review-r2-guards/guards.json)将finder改为仅匹配根名，**当前隔离测试仍通过**（1 passed、30 deselected），直接证明缺口。fact/JOIN和完整sys.modules扫描已有，保留。

## R2（P2）：补回原要求，按函数局部修改

下表是已有契约的剩余部分，按所列函数补丁修改，不能再删掉已有正确用例来缩减测试数。

| 位置 | 缺口 | 最小修正 |
|---|---|---|
| `m3_extend_inv:122–124` | 实际INV→COPY | 第二条也改INV；与COPY→COPY对照，保持每例verifier True |
| `test_join_rename_invariant:310` | 只合并改关系+实体；局部变量改名和独立改名已丢 | 恢复关系／实体／局部变量分别改及三者合并，每个确有字段变化、键不变 |
| `test_join_world_step_swap:347` | 只做世界重排，独立step重排缺失 | 保留当前世界重排，另加世界不变的独立事实步骤交换并重映射refs |
| 原A/B有效用例被删 | 自反fact区别、unused事实不变 | 补回 p(a,a)≠p(a,b) 和追加unused(U,V)后键不变 |
| `test_m5_ab_ba:397` | 只交换AB | 对现有BA也联合交换body/refs，确认真变化、verifier True、仍为原BA键且不同于AB |
| `test_m6_ab:409` | 仅改关系 | 增加实体全树一致改名，AA/AB共享关系及query同步保留 |
| `_snapshot:235–240` | proof只保留conclusion | 把每步clause_index、premise_steps一起保存；三组原输入hash也在首次调用前取并末尾比较，不能只hash不完整JSON |
| `test_key_container_types:267` | 仅fact，tolist式转换掩盖真实tuple类型，变量路径不覆盖 | 直接检查fact/COPY/JOIN的原始键；逐层type is tuple/str/int及非负编号，检查hash/set/dict；不要经tolist转换再检查类型 |
| `test_delegation_once_identity:463` | clauses/proof只查相等 | 三原对象均用is，预算7精确；默认函数同样原对象、恰一次、预算必须10000，不能接受None |
| `test_sentinel_identity:498`、`test_delegate_before_O:514` | 两次都LogicValidationError；缺ProofLimitError | 分别用两类sentinel，原实例is、精确类和消息、一次调用；各与非法O叠加证明委托优先级 |
| `test_m9_shared_refs_rejected:454` | 直接测试旧canonical_proof_key，绕过新API | 先verifier True，再调用motif；精确LogicValidationError及单出现树全文 |
| `test_empty_proof_error:529` | 允许两种类，无消息 | 只允许LogicValidationError，全文 `proof_key.proof must be a valid proof of query` |
| `test_all_budget_errors:535` | 比R1还弱，几乎只查类 | 所列非法O均精确类及全文；4300位数限制fixture保存／设置／finally恢复；±10**5000不格式化到id／消息；正预算完整键等于fact字面量 |
| `test_generator_consumed:550` | 已用真实单元素generator的剩余元素证明未消费 | 本项关闭；行为等价有效，不为改成consumed列表单独返工 |
| `test_signature_type:562` | 缺参／额外位置测试被删 | 恢复两种TypeError，保留未知keyword |
| `test_budget_boundaries:574` | 缺M9的2/1、M6 AB的8/7 | 恢复；所有成功比较完整默认键，失败精确类／全文 |
| `test_long_chain:591` | 完整header已正确，仍无hash/比较 | 在原始完整键上补hash／排序与独立公式期望比较；保留逐header检查 |

R1已有效的M3/M5/M6/M9完整字面量断言被整体重写删除，可直接从冻结R1恢复到相应现有测试，不重造oracle；三主锚点保持。

所有 `verify_proof(...)` 调用要断言 `is True`，不能丢弃返回值。已有合法fixture不要大幅重构。上述功能对应原R1报告／任务A–F，不要求增加通用oracle或扩大数据。

独立额外守卫还实证：**给新增O诊断加错误后缀、重建底层ProofLimitError、错误接受共享树**，三个产品副本均通过当前31项。连同root-only测试副本，共4个新反例逃过检查。见 [guards.json](../review-r2-guards/guards.json)和保存的源码／stdout；它们不是产品发现的新缺陷，而是已有要求缺少保护。

## R3（P2）：工具和留证没有按交接使用

- 原返工四步明确给了 `check_rework_r2.py`，也给了新baseline；该文件在开工前已经存在且现hash未变。调用旧 `check_delivery.py` 的失败不说明缺少可用工具，不能绕过规定检查。
- 本地 `pi-r2-docs/` **为空目录**，没有record/stdout/stderr；没有R2 preflight／focused／full记录，没有R2 provenance。聊天中的916 passed、docs exit1和“独立验证链接”等只记Pi自述；本轮不补跑full来冒充历史。
- `guard-r2/guard-r3` 有真实输出与guard JSON，但未通过记录器，没有record.json。这44个新文件在R2允许的 `pi-r2*` 路径之外，**不在原2776项 rework-baseline 中**。先保留，Codex现将其作为已知历史纳入下一轮冻结；不删除／移动／改原manifest来让scope通过。
- guard-r2实际上是**4/6**错误副本被拒（generator和enumerator两者通过），不是5/6；guard-r3才是6/6。分组自述5+6+9+9+1+1+1=32，与31也不符，后续从实际收集结果填写或直接只报总数。
- README:347在T0013的十三文件命令尾加motif；T0014:385自己的命令仍少proof_count。需要修改的是**T0014节**，按原driver的十四文件顺序；恢复T0013旧命令。README头部awaiting_review但下方仍写当前needs_changes的状态也要一致。
- handoff R2署名Qwen，任务安排Bonsai；证据未采集模型，不能替其猜测。新记录注明实际alias/provider/reasoning及来源；无法核验的部分标自述／unknown。合同修订号不由测试数量决定，Pi当前r2标记不代表研究协议变化。
- 继续保留此前“规范笔误”撤回；补齐开发未录制、自行重跑full（原安排明确不需）、未按步骤预检／状态切换证据及本轮工具误用的更正。只有已记录的内容才称可核验。

## 后续验收边界

本轮不accepted。R1产品结论／925项full仍可沿用；当前31项定向通过不等于原契约覆盖完整，916项仅Pi自述。下一轮按交接追加的四步局部修补，冻结产品、原文件快照、所有旧RUN及guard-r2/guard-r3。

只新增 `pi-r3*`，使用新 `check_rework_r3.py` 和 `review-r2/rework-baseline.json`。新守卫脚本 `review_r2_guards.py` 为固定四类反例；F中现有 `if fullname == r or fullname.startswith(r + "."):` 判断本来正确，应保留，仅修正自测/路径/消息，便于同一root-only副本复核。六个原守卫继续使用原脚本。不得自改checker/guard、回切源码补造preflight，也不再全文件重写；不commit/push。
