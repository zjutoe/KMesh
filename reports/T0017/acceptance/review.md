# T0017 自动闭环验收摘要

- 结论：**accepted**，2026-09-27 04:53:11 UTC；round 3 / attempt 4，无遗留问题。
- 终态事件：`T0017-query-motifs:4:accepted`；本次关闭仅核对证据和同步文档，没有重新调度、调用模型或复跑pytest。
- 验收基线：`783cdd2dd00643815f084d97fbd1038265a2003c`，分支 `T0017-query-motifs`。本报告在用户授权提交／合并／推送的收尾阶段生成。

## 执行与返工

1. attempt 1：Pi达到原3600秒阶段预算，进程被停止；没有控制器检查或Codex验收结果。失败原件保留。
2. 用户授权以后单次7200秒，并显式恢复本任务、延长总窗口。原manifest不改写，运行时覆盖及恢复事件留在控制器中。attempt 2：48项定向／1008项全量通过；独立Codex未发现产品缺陷，但提出巨整数位数限制、异常传播、枚举前无输入探查、Q6变换四项测试缺口，判 [needs_changes](attempt-0002.verdict.json)。
3. attempt 3：自动返工，只改测试；51项／1011项检查通过。独立审查关闭R1/R3/R4；R2中异常消息比较仍读取同一对象的两个实时值，不能拒绝原对象的消息被改写，见 [第2轮意见](attempt-0003.verdict.json)。
4. attempt 4：两处异常场景在调用前保存预期消息，产品保持不变。控制器51项／1011项通过；独立Codex定向51项通过，六个消息变异反例全部被拒，R2关闭，见 [最终意见](attempt-0004.verdict.json)。

首轮需要用户显式恢复，之后返工／审查由控制器自动运行。本任务使用原有后台模式，并非新Pi主界面的真实模型联调。

## 接受版本与证据核对

- 产品 SHA-256：`3feb1fb5801e5504fd9d79e6087bab06e159ec69f098ed3168aeb950e6e456f9`。
- 测试 SHA-256：`17c022f05acd7751b2e6677f8a1e698c99479a50c9b64d67baf9dfe6141cc59c`。
- 接受快照：`638f5ded2c0b8ec2e01de33824b7deb13e37a0b6c5d14f9acc012072e41c8456`。
- 控制器原始结果：[定向51项](focused.stdout.txt)、[全量1011项](full.stdout.txt)，后者为960既有＋51新增，两个进程退出0且stderr为空。
- 主会话写回前核对完整工作区与接受快照相同、产品自attempt 2起未改、Pi／checks／Codex结果成功、各stdout/stderr哈希一致、verdict与outcome一致、Codex有成功终态且无失败终态。

[结构化记录](summary.json)包含轮次、运行时模型身份、各进程结果hash、原始state位置及预算恢复信息。Pi身份为RPC记录的 `bonsai / bonsai2-27b / xhigh`，不等于服务端权重证明；审查CLI指定 `gpt-6-astra / xhigh`。Pi汇总中的“50原有＋3新增＝51”等计数表述不采信，以控制器原始stdout的48→51为准。

[原发布契约](published-handoff.txt)字节已保留，SHA-256为 `32bdd08f50149203586b6dfe9196adca8505fff7795edbeec29185726f9f75ff`。当前README、实现状态及交接终态记录是验收后同步，产品／测试保持接受版本；不改写原state、失败attempt或历史交付。认证副本与大体积模型事件未入Git。

## 研究范围

本项完成单查询全部原始证明的完整有根子树motif联集，任一预算失败均表示未完成审计，不表示无泄漏。尚未实现任意裁剪片段匹配、正式保留清单、world准入／数据划分、训练或LLM局部更新研究。
