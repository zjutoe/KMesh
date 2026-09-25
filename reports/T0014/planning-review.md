# T0014 规划与独立设计审阅

2026-09-24，规划者 Codex + gpt-6-astra、xhigh。基线 master `0e407ed9b3f270143f8587a301fa34fabf465b6b`；规划前工作树干净，T0012/T0013 已合并推送。当前任务仅准备交接，未实施 motif 产品／新测试，未 commit/push。

## 独立设计结论

非作者 reviewer `/root/design_t0012`（继承本线程模型与推理设置）先审算法提案，再只读审阅 [完整表示契约](../../docs/motif_identity_v1.md)与 [任务交接](../../docs/handoffs/T0014-proof-motif.md)。其最终结论为“静态设计可交实施，未发现阻塞问题”；未执行 fixture 或回归检查。下面是本文件对其返回意见的转述，不是伪造工具运行记录。

- 固定有序树用独立关系／实体首现表消除全局双射，再枚举全部联合槽位方向，覆盖所需等价关系；无需符号全排列。T0012 的初始字典序不限制新表示。
- 三个完整手算键、M3/M5–M9 和1201 header 数学式静态核对通过。特别是 M5：根 head 要求保留 x 的角色，交换两个不对称槽又会要求 x 对应另一变量，故即使跨世界重命名，AB/BA 仍不同。
- 按建议明确：二槽节点要用稠密位号而非节点索引；反序栈解析的 pop 次序不再反转；新增预算在 T0012 成功后校验；重复槽仍计方向；三组纯度快照均取于各自首次调用前。
- 按建议使 docs 驱动先生成本轮索引、后检查指向索引的链接；当前未完成的 docs RUN 不进入自身索引。

## 主代理的可核查规划检查

| 检查 | 证据与结果 | 限制 |
|---|---|---|
| 合并基线／环境／前置接受哈希 | [planning-baseline](planning-baseline/record.json)，exit0；2672个跟踪文件清单、Python与包路径 | 不重新验收旧产品 |
| 规划 fixture 前提 | [planning-examples](planning-examples/record.json)，exit0；15个合法证明，含1201步链；共享引用由T0012拒绝；实际JOIN改名使T0012槽位翻转，M6二槽原索引为0/1/4 | 只调用既有 verifier/T0012；**没有执行新 motif 算法** |
| 既有测试收集 | [planning-collect](planning-collect/record.json)，exit0；原十三文件885项 | 仅 collect-only，不是 full 通过 |

完整 fixture 输出见 [examples.json](planning-examples/examples.json)。规划静态检查由 `check_planning.py` 通过新 RUN 保存：审计原源码／测试／历史保持原hash，规划文档本地链接／卫生、helper AST 与 ready 状态。不以审阅代理的静态分析冒充该脚本结果。

## 决定与剩余工作

T0014 一项即可：一个单树参考模块、一个测试文件、最少文档同步，五步实施。冻结 `[proof_motif_v1]` 编码，不改变 E0/E1、同世界证明计数或输入白名单。方向枚举有指数成本，预算不足须拒绝完整审计；优化需另验，不在本任务扩大范围。

Pi + 用户授权 bonsai2-27b 可按 ready 契约实施；模型来源由执行时记录。交回后 Codex 仍须独立核验真实 diff、全树改名反例、联合配对、预算、长链和硬隔离。motif 子结构匹配、保留清单、split manifest、world 准入和生成器后续另拆，当前均未完成。本次未得到新的神经训练或成本研究结论。
