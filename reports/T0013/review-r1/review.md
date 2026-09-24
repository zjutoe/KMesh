# T0013 第 1 轮独立验收（2026-09-24）

结论：`needs_changes`。产品未发现缺陷，保持冻结；返工限测试 A/E 与记录更正。首轮 20 项／完整 884 项通过属实，但不等于交接 A–E 全部覆盖。

## 已核验事实

- HEAD `e576c7793a91f8508ed5c57333f81eb0188a5745`，分支 `T0013-proof-count`；2494 项规划／历史冻结文件哈希全部一致，无前置实现改动。11 个 Pi RUN 的原始 stdout/stderr 哈希及 before/after 源码快照一致，preflight 时新产品／测试确为 null。见 [输入核验](../review-r1-inputs/record.json)、[完整清单与 RUN 内容](evidence-audit.json)。
- 产品 `ac710fd17731bde66e90e8d7737a5eac59486b65454f6bd0fbe9d1ca270eec6d`；提交测试 `b3af8851606836b27689f1ffba6b5061542496d5b6cfba4eceb0d22a6ad55a13`。两者原件及文档保存在 [input-snapshot](input-snapshot/)，全提交文件哈希见 [frozen-inputs.json](frozen-inputs.json)。
- 独立十三文件回归 **884 passed**，无 skip/xfail，stderr 空；见 [review-r1-full](../review-r1-full/record.json)。
- 独立补测真实 U8=0、真正的局部变量改名=2、完整输入对前后不变、README U3 输出 1 全通过；见 [probe.json](../review-r1-probe/probe.json)。这是 Codex 本轮新增证据，不能归为 Pi 首轮已覆盖。
- 有限错误副本：原始树数冒充规范数、截断到 2、遗漏 key 预算、吞掉后续 key 异常均被现有目标断言拒绝；仅保留根名匹配的隔离守卫仍然 **20 passed**。原提交控制组也 20 passed。见 [guards.json](../review-r1-guards/guards.json)，每例原输出同目录留存。仅改隔离副本，未改工作树产品／测试。
- 非作者 `/root/design_t0012` 独立静态核对原交接与 A–E，定位同样的 A/E 缺口；未运行检查。主代理负责上述实证与最终结论。

## R1（P2）：A 组缺项与变换对象错误

定位：[test_proof_count.py](../../../tests/test_proof_count.py) 的 `TestAHandCounted`（约 99–188 行）。

1. 缺少 U8：已有 U0 空世界，不能替代非空、无环且 query 不可推出的正例。补 `p(a,b)` 与 COPY p→q，query `missing(a,b)`，C/D/S=1/2/1，断言精确整数 0。
2. `local_variable_bijection` 实际把事实常量 b/d 改为 e/f，JOIN 的 `?x/?y/?z` 未改。按原契约改为仅 JOIN 内 `?x→?u, ?y→?v, ?z→?w` 一致双射，事实和 query 不变；显式断言原／新 clause 不同、事实相同，结果仍为整数 2。原常量改名不是本项证据，可删除而不扩套件。
3. 按原契约对 U0–U8 各个返回值断言 `type(result) is int`。同处把纯度的 deepcopy 改为完整 `(world, query)` 对并删除末行 query 与自身比较；现有 hash 已含 query，故这处不另列产品纯度缺陷。

## R2（P2）：E 组未真正自测子模块前缀拦截

定位：`TestEIsolation`，约 499–543 行。`torch.nn`／`yaml.safe_load` 导入先触发未加载根包的拦截；两个 kmesh 根也只做根级导入。因此去掉 `name.startswith(root + '.')` 后全套仍过。把 finder 对象插入 `kmesh.logic.__path__` 不会实现注释所说的机制；当前实际阻断来自 sys.meta_path 的 `_BlockFinder`。

最小修复：保留四个原禁用根、硬阻断 finder、真实 U2/U6、当前 src 路径与 sys.modules 扫描。对每个根：

- 先实际 import 根并断言专有错误，消息带完整尝试名称以区分拦在根还是子模块。
- 确保目标未预载，临时在 `sys.modules[root]` 安装 `ModuleType(root)` 且 `__path__=[]`；实际 `importlib.import_module(root + '._t0013_probe')`，必须得到包含完整子模块名的专有 ImportError。只调用 finder 方法不算自测。
- 在 finally 清理占位根／probe，保护已有父包；不要操作 `kmesh.logic.__path__`，不需磁盘临时 torch/yaml 包。四根和点前缀都自测，之后再运行真实产品。

验收时 Codex 再检查“只拦精确根名”的副本必须失败；Pi 无需新建通用变异框架。

## R3（P2）：记录按原件更正

旧 provenance／RUN 原件保持不动，新一份 R2 provenance 追加更正：

- Pi 首轮落盘测试是 U0–U7，没有 U8；局部常量改名不是局部变量双射。README／实现状态的当前覆盖描述应据修复后结果更新，撤回“无未运行项／无实质偏差”的全覆盖暗示。若另有未录制探针，只能标 Pi 自述，不把规划或本轮 Codex 探针当成 Pi 首轮证据。
- `pi-r1-docs2` 的实际失败是相对链接 `pi-r1-docs/record.json` 解析错误；`pi-r1-docs3` 才是 `../pi-r1-docs2/run-index.json` 不存在。其余 docs1、docs4 原因与现说明相符。全部共有 11 RUN（7 成功、4 失败），docs5–docs8 均成功；docs8 自动索引记载前 10 RUN，当前 RUN 自身见 record.json。
- 原交接没有 `--tb=0` 命令或要求 Pi 再收集旧测试；交接中“合同形式无效而等价替换”的说法应撤回。Pi 目录无该收集／失败命令原件，若确实运行则披露为未录制自述；不要倒造历史。
- 实际模型 alias/provider 当前只见 Pi 环境自述，记录器只采集 PYTEST/CUDA 覆盖项；准确区分来源，不要求重新运行或制造历史模型证据。记录中的子命令以 record.json 的 `.venv/bin/python` argv 为准；外层驱动文字不是记录器独立捕获内容。
- 首轮 provenance 放在 pi-r1 而非契约 pi-r1-full，是路径偏差；文件可读且留证有效，接受原位保留，不移动。R2 新记录使用本轮成功 focused 目录。

README 当前限制句补“规范证明计数已实施、待返工复验”，避免仍笼统声称完全未实现；无需重写 README 其他任务历史。测试模块首段未实际使用的 T0011 cross-check／verifier 描述一并删准，不要求为这段错误文案引入新依赖。

## A1–A7 与下一轮范围

| 项 | 判定 |
|---|---|
| A1 | 通过，产品接口／冻结范围符合 |
| A2 | 产品补测通过，Pi A 组待 R1 补齐 |
| A3 | 通过，预算、环、后续真实坏证明和异常不返回计数 |
| A4 | 调用／身份断言有效；完整输入对措辞随 R1 小修 |
| A5 | 四个产品错误副本已拒；前缀守卫待 R2 |
| A6 | 884 独立回归及 README U3 通过；覆盖说明待更正 |
| A7 | 哈希、原始 RUN、preflight 有效；R3 更正后复核 |

按交接追加的四步执行；产品及所有旧 Pi/Codex 证据冻结，仅修改新测试与三份当前维护文档，新增 pi-r2* 证据。无需重跑 full、doctor、GPU 或前置任务；完成后交回 `awaiting_review`，不 commit/push。
