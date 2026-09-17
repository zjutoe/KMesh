# T0007：Codex 第 2 轮验收

2026-09-17。结论：**accepted**，R1/R2 关闭，A1–A7 通过；历史留证限制继续保留。未 commit/push。

## 接受版本

基线 HEAD `74a96f3735831d16a14dedffbaa6e0654f8b7658`，分支 T0007-relation-dag。

- dependency.py：`4b01df6f08e243c649f0459a23e6e8a68f946fc0eec41814f889e65cd972ca3f`，与首轮相同。
- test_dependency.py：`722869ef49a4884d52c1423d3743d4802264bd55ebc7a84521f9433d74ba6313`，只补 generator 诊断断言与获准的注释修正；fixture 和 44 项测试数不变。

见 [输入冻结](../review-r2-freeze/audit.json)与 [实际差异](../review-r2-freeze/tests.diff)。未参与 Pi 实施的 Codex 直接复核修正；A1–A4／A6 的原验收继续有效。

## R1：测试缺口关闭

[独立定向回归](../review-r2-focused/)为 **44 passed in 0.11s**，退出 0，stderr 空，无 skip/xfail，独占 basetemp。[针对性探针](../review-r2-probes/findings.json)直接调用提交的测试：冻结产品通过；内存中分别删去错误原因或类型名，两种错误诊断均被新断言拒绝。没有修改磁盘产品／测试。

首轮 [482 项完整回归](../review-r1-full/)与 [512 个小图核验](../review-r1-probes/findings.json)仍有效；本轮没有重复 full 或 doctor，也不把旧结果列作本轮新运行。

## R2：记录更正与证据边界

- 三个 Pi R2 RUN 的完整命令、前后源码哈希、stdout/stderr 哈希、退出码与时间字段核对通过，定向命令含独占 basetemp。旧 832 文件冻结清单及首轮审阅产物未改，本轮再冻结 875 个历史报告文件。
- [新 provenance](../pi-r2-focused/provenance.md)已撤回错误版本、CPU 机器推断、GPU 抖动与“无其他偏差”；补充缺 basetemp、命令变化、stderr 警告、快照计数、测试分组和时间定义。R1 正文仅补更正指向注记，旧说法仍可读；旧 RUN 和旧 provenance 未重写。
- `/tmp/t7d3.json` 在审阅时确实存在，已逐字保存为 [补充报告](../review-r2-freeze/supplement/t7d3.json)，SHA-256 `866f9a3949f1637f4f4b6dbc889aad7e73b2bbf3d71d692ed594c6c068f231da`。内容记录 2026-09-17T04:58:09.601679 UTC、torch 2.10.0+cu126、status=ok、1 张 RTX 3090。这支持一份 GPU 可用报告，不补证原命令／环境或另外两次尝试。工具／模型完整别名按 Pi 自述记录。
- 依 Pi 自述，失败 RUN 从 pi-r1-full 改名后复用了 pi-r1-full；若该叙述准确，属于移动旧 RUN／复用名称的偏差。实际动作无法从现存原始证据还原，不认定全过程合规，不要求重建或搬回旧目录。
- Codex 最终卫生检查按各 Markdown 文件所在目录解析相对链接，不采用 Pi 脚本的多根目录回退。A7 关闭表示当前证据充分、限制已披露，不抹去未归档尝试与违规自述；不为不可恢复的历史再安排返工。

## 范围

仅接受离线关系 DAG 条件与确定性顺序。证明生成／枚举、唯一性、完整 world 审计、模型读取图和神经训练仍属后续任务，不据此声称研究假设成立。
