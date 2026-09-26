# T0015 第3轮验收：accepted

2026-09-26，Codex；基线 `f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41`，分支 `T0015-proof-subtree`。

**E1/E2关闭，T0015接受。** 本轮仅核验证据与文档，继续原手工流程，未启动Codinator、模型或产品测试。产品及测试沿用第2轮接受的字节：

- `src/kmesh/logic/proof_subtree.py`：`8c6c439269961f5de53c760b6d38660effd5dfade5804154b1d2543f6cf9fe6c`。
- `tests/test_proof_subtree.py`：`955ca72abf90b0574afcd75b7ccc0bfe3a3c0a114c063534b5cc24d7440c3bce`。

## 本轮核验

[独立证据检查](../review-r3-evidence/result.json)与[原始输出](../review-r3-evidence/stdout.txt)确认：

- R3基线3374项中，除3份授权文档及2份忽略规则，3369项逐文件SHA-256未变；产品、测试、历史记录及规划材料保持冻结，新增范围符合本轮契约。
- 两份 `.gitignore` 恰好追加规定的反向模式，26项原件全部Git可见；其中24个记录／输出／副本文件字节未变，另外2个为按契约修改的忽略规则。父级pytest临时目录和缓存排除仍有效。
- `pi-r3-preflight` 于2026-09-25 15:58:52 UTC执行，`pi-r3-docs` 于16:13:56 UTC执行，均exit0、stderr空、原始输出hash一致。前者运行冻结的preflight路径，核对原忽略规则及in_progress；后者检查恢复可见性及awaiting_review。两条录制命令均不执行产品测试或模型。
- 新执行说明已承认两份934项full的真实时序、在旧产品上重现的regression、缺失R2 preflight、额外guards缺少外层record、自检／独立验证来源及历史模型unknown。没有用新记录冒充过去的执行。

沿用[第2轮验收](../review-r2/review.md)：Codex独立17项、四个错误副本守卫、15个输出探针通过；Pi两份934项full原件已核验。本轮不重复这些检查。

## Codex补充澄清

Pi原文保留，下列小范围表述误差在本验收记录统一澄清，不再增加返工轮次：

1. [R3自动索引](../pi-r3-docs/run-index.json)实际列出**14**个此前完成的Pi RUN；包含本次docs后共15个。“13个”是R2结束时的口径，不是R3最终总数。
2. “26项字节未改”应读作“26项恢复可见；24个原始证据文件不变，2份 `.gitignore` 仅追加”。其原始模式仍保留。
3. [Pi R3说明](../pi-r3/provenance.md)第5点复制了“本报告的17项”，该独立结果实际属于**Codex第2轮**，证据是[review-r2-focused](../review-r2-focused/record.json)；Pi R3没有执行17项测试，也没有进行独立验收。
4. “prefill”为“preflight”的笔误；README总述／实现状态旧句中的“待恢复／needs_changes”在本次当前状态更新中同步纠正。

R2缺少preflight原件、额外guards无外层record、修复版full先于旧版regression、历史模型归属unknown，均作为永久证据限制保留。接受的是当前实现及可核查证据，不追认历史流程全部合规。

## 验收与范围

A1–A5沿用第2轮通过；A6确认回归及冻结范围、此次归档纠正；A7以准确来源、原件保存和上述限制关闭。未发现需要继续阻塞接受的产品、测试或证据问题。

本能力是给定证明中某一步的完整支持子树抽取；不代表world泄漏审计、数据划分或LLM训练假设已验证。未commit/push。本任务按原方式闭环，后续任务可按用户授权使用Codinator；本轮没有调度下一项任务。

后续范围检查应同时核对Git可见清单和证据目录实际文件，防止局部忽略规则遗漏原件；自动索引应直接引用，避免手抄计数和跨角色复制“本报告”。

准确核验命令：

```bash
.venv/bin/python reports/T0015/record_check.py review-r3-evidence -- .venv/bin/python reports/T0015/review_r3_check.py audit
.venv/bin/python reports/T0015/record_check.py review-r3-close -- .venv/bin/python reports/T0015/review_r3_check.py close
```

最终文档、产品／测试版本及结论见本目录 `final-audit.json`；收尾命令退出码以 `review-r3-close/record.json` 为准。
