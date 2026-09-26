# T0016 自动闭环验收摘要

- 结论：**accepted**，2026-09-26 14:26:15 UTC；实施 round 2，attempt 3。
- 事件：`T0016-subtree-motifs:3:accepted`。本次只处理该终态一次，没有重新调度任务或重跑测试。
- 工作区：`/home/mye/data/kmesh-worktrees/T0016-subtree-motifs`，分支 `T0016-subtree-motifs`，HEAD `011fc81cd6c6396a1de8cd0179ef7f658aae0fa0`；未 commit/push/merge。

## 执行与恢复

1. attempt 1：Pi + Bonsai 完成两个允许路径的实现／测试，控制器26项定向和960项全量通过；Codex因使用额度耗尽退出，没有验收结论。首轮开发探针曾失败，原始工具事件保留在外部state；不把Pi汇总当作独立检查。
2. attempt 2：用户授权 `resume --review-only --extra-seconds 3600`，复用attempt 1冻结提交和成功检查。本轮没有Pi进程或控制器checks目录。独立Codex判 `needs_changes`：首次T0014失败后，原测试未监测抽取依赖，错误实现仍可多调用一次而通过测试。见 [原验收意见](attempt-0002.verdict.json)。
3. attempt 3：控制器自动交回Pi；仅修改 `test_sentinel_first_whole_tree`，加入抽取spy并恢复两个依赖绑定。产品哈希与attempt 1一致。新26项／960项检查均退出0，独立Codex复跑26项并用错误版本核验守卫有效，关闭 `T0016-R1`，无遗留问题。见 [最终意见](attempt-0003.verdict.json)。

本次跑通的是真实“仅审计恢复 → 独立审计 → 自动返工 → 再审通过”流程，最初额度中断仍需人工显式恢复，不声称全过程无人干预。

## 核验与接受版本

Codex主会话在写回文档前，核对整个工作区快照与控制器接受摘要一致，并核对产品／测试、各进程结果和stdout/stderr哈希。Codex审计进程退出0且包含成功终态事件，无失败终态；verdict与outcome一致，绑定正确提交。所有关闭阶段操作均为读取或文档同步，没有重新调用模型／pytest。

- 产品：`2898ef24c55d9a00768192ecf907563accee2d49842d3fe6462b2ab7df32fbde`
- 测试：`d1034e59e3046b5d00157509a5e31411cf9872aa12f5fd9ed5aafa99f96fe851`
- 提交快照：`9233146eebdd82a3a76286269a4182b568876a8d615ec39c93cc7239443f7fda`
- 控制器 [定向26项](focused.stdout.txt)、[完整960项](full.stdout.txt)；后者为934既有＋26新增，无skip/xfail。独立审计的26项复跑与反例结果详见最终意见，完整原始事件在外部state。
- Pi身份来自RPC客户端记录 `bonsai / bonsai2-27b / xhigh`，不等于服务端权重证明；审计CLI指定 `gpt-6-astra / xhigh`。

[结构化摘要](summary.json)保存原始目录位置、过程结果hash和原发布契约hash；[原发布契约](published-handoff.txt)完整保留。未将认证副本或大体积原始模型日志放入Git。当前文档状态在接受后由Codex同步，因此文档变更不属于原接受快照；产品和测试保持接受版本。

## 研究范围

只完成逐发生位置的完整有根支持子树motif目录，保留重复发生和原步骤顺序。仍是小规模离线审计原语，输出可能平方增长；不表示任意裁剪片段匹配、world无泄漏、数据划分、模型训练或LLM局部更新假设成立。
