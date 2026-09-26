# T0015 设计审阅

2026-09-25，Codex + gpt-6-astra，xhigh。

主代理对研究计划§5.2、T0006/T0012接口和T0014接受记录做依赖检查。非作者`/root/design_t0012`独立只读审阅提案，结论可交实施；其未修改文件、未运行检查，不把本记录归为Pi结果。

采纳的澄清：max_steps始终约束完整输入；输出验证的query是原选中步骤结论；按原位置线性过滤，不sort或DFS重排；允许从proof导入ProofStep但不再次调用verifier；不要求输出对象身份；补上JOIN外再接COPY、选择非末内部JOIN的交错存储反例。

仅定义完整有根支持子树，去掉祖先和外部上下文；不定义一般裁剪、边界变量或正式保留规则，因此不改变E0/E1／证明身份／motif版本。不能把未来子树motif当成一般结构覆盖或无泄漏的证明。

主代理使用已验收T0006/T0012核查手算输入与预期子证明，见 [主例](planning-examples/result.json)、[补充例](planning-edge-examples/result.json)。这些是前提／fixture检查，不是新API验收；没有创建产品或测试。

前置十四文件仅collect-only收集917项，见 [收集RUN](planning-collect/record.json)；未重跑full。任务driver给Pi唯一命令入口，状态／provenance链接和十五文件列表由checker核查，减少重复手抄日志的误差。所有helper与规划材料在planning-files.json冻结。
