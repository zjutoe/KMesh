# T0012 第 3 轮 Codex 复验：needs_changes

2026-09-23，Codex + `gpt-6-astra` / xhigh。独立复核 R3 diff，另有非作者代理只读复核步骤 1–3；未改产品／测试，未 commit/push。**本轮有实质进展，但部分明确要求仍未落实，暂不能 accepted。**

## 已完成并保留的成果

- [冻结审计](../review-r3-freeze/input-audit.json)：2008 个保护文件未变，HEAD 为 `56b41de11a2651da615230117f0d96bd6e0d6e92`。产品 SHA `92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`，测试 SHA `96d08b9b7fadcb226e8b10d9c0f5f62b9b65f4cfd346fd8167242afaaef9f1a6`。
- [独立 focused](../review-r3-focused/record.json)：**54 passed**，stderr 空，无 skip/xfail。产品未变，不重新运行 full，沿用 Codex R1 840 项证据。
- [独立守卫](../review-r3-guards/guards.json)：原十个违约副本全被拒绝，异常原实例问题与直接导入 engine/dependency 的问题已得到有效覆盖。
- K4–K8 完整手算键、K1/K3/K4/K5/K6/K8 实际 oracle、T0009 逐树 verifier 与完整手算集合对照已落实。不要重写这些正确部分。
- 两类具名异常 sentinel `is`、非默认预算和一次调用、主要非法输入经新 API、共享／无关步骤先验证再拒绝均已落实。
- 不同关系的 1201 步长链完整 header、原生排序、字典哈希及预算已落实。K1 README 可执行例未改，Pi 新 RUN 有成功原件，沿用 Codex R2 的独立验证。
- README 已修复 T0011 依赖和扁平表示的主要错误。Codex 此轮顺手将描述中的位置预算改为 `max_steps=max_steps`，关闭 R4，不再为此安排测试返工。

## 尚未关闭的具体项

### P2 / R1：生成器副作用与少量入口回归

[第 785 行的生成器测试](../../../tests/test_proof_key.py)没有消费标记。新错误副本 `consume_generator_before_verify` 在拒绝生成器前先取走一个元素，**全部 54 项仍通过**；它违反原输入不得预扫描的契约。

第 817 行 `try/finally: del big` 只删除变量，不是设置／恢复 Python 整数转字符串限制。仍缺固定 4300 限制下的巨整数非法外层和负预算；原 missing/extra/unknown keyword TypeError 测试在 D 组重写时删除。世界非法先于本层扫描的叠加例也未补。

最小修补：生成器有 `consumed` 标记，调用新 API 后精确诊断且未消费；局部 fixture 保存、设为 4300、finally 恢复，用 `10**5000` 和短 ids 测非法外层／负预算／正预算；恢复原签名回归和上述错误优先级。保留已经正确的 sentinel，不再重做异常身份。

### P2 / R2：变换矩阵及实际符号保持仍不完整

B 组除类型检查外仍主要沿用旧例；C 新增的两个变换不能覆盖原矩阵。下表是明确剩余项，不要求重写已通过的手算／oracle／枚举部分。

| 剩余要求 | 当前缺口 |
|---|---|
| 局部变量改名 | 缺 K3、K5、K6；已有 K1、K4 |
| 世界重排且重映射 index | 缺 K4、K5、K6；已有 K1、K3 |
| body/ref 联合交换 | 真正 K3 JOIN、K4 的 schema＋refs 尚缺；现第 593 行所谓 K3-style 是同参数 AND，不是桥接 JOIN；K5 应保留 AB 并补 BA 对照 |
| 来源、实际符号 | 重复 COPY 来源仍缺（现只复制 fact）；实际谓词／常量大小写及非对称改名区别仍缺 |
| 稳定性与真实变换 | K3→K0→K5→K3 未实施；补输入字段／hash 前后快照；适用变换明确实际发生变化并先验证 |

`lowercase_actual_symbols` 副本把实际谓词和常量统一小写，**全部 54 项仍通过**。大小写保持是原契约，不能只靠全小写 fixture 核验。独立错误副本日志及 diff 均在本轮 guards。

逐层类型检查已有进步；收尾时把 term 的 `c`/`v` payload 分开检查，并按原要求用真实 tuple/str/非 bool int 类型。无需新增数据类型或抽象框架。

### P2 / R3：隔离器已存在，隔离自检仍不完整

当前 `sys.meta_path` finder 已能阻断非白名单导入；这比 R2 明显进步。尚未完成原有的可验证条件：

- 子模块检查仍直接调用 `_f.find_spec`，没有占位包之后的实际子模块 import；根 import 只捕获任意 ImportError，未匹配专有消息，无法区分正确阻断与模块本身导入失败。
- 自测名单把 depth 换成 clause_key；宽拦截器实际上也阻断 depth，但原八根并未逐项实测。按原八根定义匹配；clause_key 不是原禁止项。
- 变量 `k5a/k5b` 装的是 K1 COPY 改名例，不是非对称 K5；应实际构造原 K5 AB/BA，并核对二者不同。
- 缺最终 sys.modules 根／点前缀扫描；源码只检查路径尾缀，改为与本次 src 的完整路径相等。

最小修补集中在现有隔离函数：原八根、专有消息、实际子模块路径、清理、K0/K3/真正 K5、最终扫描。保留真实 verifier。不要另建更宽的导入白名单设计。

### P2 / R5：流程与记录仍需如实更正

本轮只有下列四个 recorder 原件；[完整时间、argv、哈希及输出](../review-r3-freeze/input-audit.json)均已核对。没有 preflight、boundary、identity、isolation 的 RUN，不能写成按五步执行完毕。

| RUN | 开始 UTC | elapsed_s | exit |
|---|---|---:|---:|
| pi-r3-guards2 | 2026-09-22T18:20:13.104342+00:00 | 11.265 | 0 |
| pi-r3-focused | 2026-09-22T18:21:18.649495+00:00 | 0.749 | 0 |
| pi-r3-readme | 2026-09-22T18:22:37.953846+00:00 | 0.088 | 0 |
| pi-r3-docs | 2026-09-22T18:32:13.039661+00:00 | 0.046 | 0 |

- **替代检查与范围偏差：** `reports/T0012/review-r3/check_readme.py`、`check_docs.py` 是本次 Pi 新增，原授权仅允许新 `pi-r3*`。它们不是 Codex 验收材料。docs 脚本只验 HEAD、状态、几个硬编码链接和文本卫生，没有原驱动的历史哈希／授权范围／全部文档链接检查。成功不能代替约定检查。
- 上述两文件原样保留并冻结，防止破坏证据；因此真正 Codex 本轮材料使用 `review-r3-codex/`。后续不得修改、移动或删除它们来掩盖偏差，也不要继续使用其宽松检查交付。
- focused 没有独占 `--basetemp`，实际顺序为 guards→focused→readme→docs。未归档的检查／状态先行只写自述或 unknown，不补造历史。2008 文件核对说明当前冻结件确实未变，不能证明历史每一步均合规。
- 新 provenance 继续使用含重复片段的错误 HEAD；开始时间被截短、结束时间未列、docs 时点仍为占位式描述。模型环境未被记录器采集，来源明确为 Pi 自述。
- 原 R5 七项更正及 R2 新增问题没有逐项完成；R3 执行记录又声明已完成重复 COPY、跨 fixture 稳定性等实际不存在的检查。须逐项撤回／更正，不把所有缺口笼统写“自述/unknown”。
- 实现状态把 Pi 的 54 项称为“独立定向”，本轮 Codex 复验后才有独立结果；结果归属须区分。`guards` 是 1 个成功控制＋10 个失败副本，不能称“11 项全 reject”。

## 结论与下一步

保持 `needs_changes`。**异常实例、手算键、oracle、枚举集合、长链、README 主体已关闭对应缺口**；下一轮只补上述入口残项、变换矩阵、隔离自检及真实记录。原十个守卫通过有价值，但不足以代表所有需求已完成。

产品保持冻结，不重复全量、不新增研究目标。后续准确范围与命令见 [交接文档追加的 R4 收尾安排](../../../docs/handoffs/T0012-proof-key.md)。所有原件保留，未 commit/push。
