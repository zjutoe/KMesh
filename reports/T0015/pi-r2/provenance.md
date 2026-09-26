# T0015 R2 provenance（唯一执行说明）

- 日期：2026-09-25（Pi，UTC）。本轮为 R1 `needs_changes` 的最小返工（D33），沿用上轮授权、CPU 预算与冻结边界。
- 实际执行者／模型归属：Pi（PI_ALIAS 自述 qwen3.8-coding-27b、reasoning=xhigh；交接指定“最近授权 bonsai2-27b”。二者一致无独立证据，归属保持 unknown；未提供开工前配置不一致反馈。不把自述当模型实证。）
- 基线／分支：HEAD `f5ef96f7d6d261beb2dba6fc8c47300f24c9ff41`；分支 `T0015-proof-subtree`。
- 改动（R2）：产品 `src/kmesh/logic/proof_subtree.py` 最小修三行——导入公开 `ProofStep`、以公共类重建三字段（替换原 `type(step)`）、返回标注对齐 `tuple[ProofStep, ...]`；不改变验证／root／收集／线性重编号路径。测试 `tests/test_proof_subtree.py` 按报告 R2 表 9 处局部修 + 新增 1 项（16→17）：子类回归 `test_accepted_proofstep_subclass`；长链引用 `== (() if i==0 else (i-1,))` 前序修正＋验证；sentinel 移动 clear／仅追加，捕重复委托；真实 generator 消费＋精确全文；单发生共享两步与未用四步分离；world 反转独立构造＋ci 重排＋refs 不变＋root=3；纯度字段快照＋hash＋`0<=ref<i`；签名 `__all__`；root 越界／巨整数补类型；隔离占位 `__path__=[]`。README T0015 段、实现状态 T0015 行/能力行、本文件状态/执行记录同步。
- RUN（新增，均为新编号；旧 R1 RUN 原件保持）：
  - `pi-r2-regression` exit1：17 项对**R1 原（buggy）产品**——`test_accepted_proofstep_subclass` 真失败（`TypeError: AnnotatedStep.__init__() missing 1 required positional argument: 'note'`），其余16 过。证新测试捕 R1 缺陷；运行后恢复产品。
  - `pi-r2-focused` exit0：17 项对 R2 产品全过。
  - `pi-r2-guards` exit0：--enforce，submitted 过，四反例各被指定断言拒绝（chain→test_1201_step_copy_chain；retry→test_sentinel_priority；generator→test_input_generation_and_list_rejected；import→test_hard_isolation）。
  - `pi-r2-full` exit0：15 文件 934 过（917 既有 + 17 新），stderr 空。
  - `pi-r2-docs` exit0：新 R2 docs checker，范围/冻结/状态/链接/README/十五文件/卫生；run-index 排除当前 RUN。
- R3 更正（响应验收报告六点；旧 R1 provenance/RUN 原件不改）：
  1. 时序：R1 原件 full 12:21:29Z、focused 12:21:56Z，full 在前；两者源码哈希相同、结果有效，但“focused 后 full”表述不符实际，按原件先后重排，不拿列表顺序当时序。
  2. full 真实结果：R1 full 为 933 过；R2 full 为 934 过。均“本轮运行”，不“未重跑 full、沿用917”；917 仅旧测试数。来源：933/934 为 Pi RUN 原件，16/17 为独立定向。
  3. 已完成 Pi RUN：R1 共 7（preflight、dev1、dev2、full、focused、docs2、docs3）；`pi-r1-docs/` 仅 run-index+gitignore，无 record/stdout/stderr，其 exit0 仅 Pi 自述、不可独立核验，不称三 docs 均录制原件。R2 新增 4（regression/focused/guards/full）+1 docs。
  4. dev1 8 failed/8 passed、dev2 6 failed/10 passed；两 RUN 产品哈希与最终一致、测试哈希不同，原件证测试迭代，不据此认定产品改过；未录过程保持 unknown。
  5. README“四个授权函数、2981 冻结件”属旧任务；本轮新增产品/测试、改 README/状态/交接，规划冻结清单 3167 项（R2 基线）。R1 的“独立16项”当时无独立依据，现以本轮 Codex 独立 16（R1）与 R2 17 为准。
  6. 模型归属：交接指定 bonsai2-27b、Pi 自述 qwen3.8-coding-27b，无独立来源，保持不确定，不补造旧运行记录。
- 未重跑：R2 full 仅一次（产品改后）；未跑 doctor/GPU；未 commit/push。旧 full/守卫/doctor/GPU 保留，R2 不重复。
