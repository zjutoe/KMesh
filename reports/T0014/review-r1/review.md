# T0014 第 1 轮验收：needs_changes

2026-09-24，Codex + gpt-6-astra，xhigh。基线 `0e407ed9b3f270143f8587a301fa34fabf465b6b`，分支 T0014-proof-motif；审阅原契约与实际提交，未改产品／测试，未 commit/push。

结论：核心算法在本轮有界独立检查中未发现功能错误；测试守卫及交付叙述有实质缺口，暂不 accepted。产品 SHA-256 `23d175e8865b3ace1d4ffd4094b67fcb18c8c36ae986f3b44b2e148fde80476f`，提交测试 `c61001cb492cfb84c06fc608c64d950510df671920b85e1014fe6e72829b81f0`。原件已保存于 [input-snapshot](input-snapshot/)，全量文件清单为 [frozen-inputs.json](frozen-inputs.json)。

## 已核验的结果

- [inventory](../review-r1-inventory/record.json)：2693 项冻结规划／旧源码测试／历史证据未变，提交范围合规；6 个 Pi RUN 的 stdout/stderr hash 与 record 相符，preflight 的产品／测试确为 null。各 RUN 前后源码哈希不变；编码前及未录开发过程不由此得到证明。
- [完整回归](../review-r1-full/record.json)：Codex 独立 **925 passed in 16.15s**，十四文件、独占 basetemp、无 skip/xfail，stderr 空。Pi full 的925项原件也真实存在（16.31s pytest，16.599s recorded elapsed）。
- [独立产品探针](../review-r1-probe/probe.json)：三个冻结字面量、真实同拼写命名空间、M6 改名／共享／方向位、JOIN/M5 联合交换、真正 M7 关系复用、三组纯度、原异常身份／优先级、外层生成器、精确预算／4300 位数限制、全部1201 header 与 README COPY 原样执行通过。此为有限检查，不宣称穷尽证明。
- [独立硬隔离](../review-r1-isolation/record.json)：五根及子模块真实拦截自检、准确源码定位、finder 保持至 fact/JOIN 和完整 sys.modules 扫描，产品通过。这不能代替提交测试应具备的回归保护。
- 非产品／测试作者 `/root/design_t0012` 只读审阅 A–F 覆盖及 provenance，未运行检查；其发现已与主代理核对，归入下述 R1–R4。

## R1（P1）：恢复实际硬隔离

定位：`tests/test_motif.py:538–599`。没有 MetaPathFinder；产品先导入，普通 find_spec 只查询模块是否可发现。对一个无关空包的 probe 得到 None，不是阻断导入。源码只检查 basename，PYTHONPATH 指向仓库根而非 src；根名漏写 `kmesh.logic.reference_engine`；只执行 fact，没有 JOIN；最终扫描漏 `proof_enumeration`；未核对子进程 returncode。

安装有 torch/yaml 和求解器不构成放宽契约理由。按原 F 恢复五根／点前缀 ImportError 拦截、每根及占位包子模块的实际 import 自测、精确完整 sentinel、finally 清理，finder 从产品导入之前持续保留到 fact/JOIN 和最终扫描之后。不得直接调用 finder 冒充 import；不得 mock T0012/verifier。测试须拒绝 `import_forbidden_enumerator` 副本。

## R2（P2）：身份、共享与纯度用例缺口

- `:242–249` 注释声称 p(p,a)，实际仍 p(a,b)。补真实同拼写独立命名空间例。
- `:307–331` 两个重排测试是相同构造，都同时改变世界和步骤。拆成独立的步骤重排（世界不变）与世界重排（步骤结论／refs 顺序不变、只映射 clause_index）。补 JOIN body＋refs 真联合交换。
- `:344–358` 未比较输入前后，未计算 hash；副本也交给产品调用，未使用 `_hashable` 不能保护纯度。三组在首次调用前保存不再传给产品的完整副本和 hash，真实执行 JOIN→fact→M6→JOIN 后比较全部输入。
- M3 只有三步链，补两步 COPY/INV。现有 M5 AB≠BA 合法有效，不需重写 fixture；补 AB、BA 各自 body＋refs 联合交换不变性。
- M6 AA/AB 对照已有，AA 删除未引用事实不影响结论；须补 AB 的指定关系／实体改名，验证原0/1/4索引使用稠密位号。它应拒绝 `sparse_direction_bits`。
- `:185–193,377–383` 实际证明 p→q→r；q→p 只是未引用条款，不检验关系复用。恢复原契约合法有限 p→q→p 与 p→q→r 的不等对照。正反例均先真实 verifier True，改动字段和引用映射必须实际成立。

## R3（P2）：委托、错误及长链断言不完整

- `:417–439` spy 没断言实际 max_steps 值；分别验证默认10000、显式7、单次调用和原对象身份。删除无用 `patcher`／未断言的id记录，使用可信 fact key 作 spy 返回。
- `:496–504` 名称有 identity，实际无 sentinel、无 `is`。两种底层异常均以哨兵验证原实例、一次调用，并叠加非法 O 核验委托优先级。补真实空 proof 的精确错误；真实 shared-M9 也断言精确错误。
- `:458–462` 传的是包含 generator 的 tuple，不是 generator 外层。改成 body 内写 consumed 的真正 generator；拒绝后 consumed 必须空。
- `:440–457` 没有设置整数转字符串限制；4300 误当成 O。局部 fixture 保存／设置4300／finally恢复，对±10**5000走原契约路径。非法 O 用精确类对象与全文。
- `:474–495` 超方向预算需精确异常类／全文；M6 成功需完整键等于默认，不能只看非 None。B=2 注释更正为3；重复槽 M9 边界保留。
- `:521–532` 缺1200个 body 的内容断言。按原数学式比较完整1201 header，并检查 hash／排序；不需重复跑默认 O 长链。真实 tuple／int类型及 `__all__` 顺序按契约补齐，删除改动产生的无用代码。

## 测试有效性实证

[guard结果](../review-r1-guards/guards.json)用隔离源码／测试副本和独占 basetemp 运行；原文件未改。submitted 为40通过；6个错误副本中**5个也40通过**：

| 副本 | 违反的行为 | 提交测试 |
|---|---|---|
| sparse_direction_bits | 位号改为节点索引，漏深层方向 | 未拒绝 |
| rebuild_logic_exception | 重建底层异常，丢失实例身份 | 未拒绝 |
| consume_generator | 委托前消费外层生成器 | 未拒绝 |
| import_forbidden_enumerator | 实际导入 proof_enumeration | 未拒绝 |
| corrupt_long_chain_body | 长链所有 body 关系改9999 | 未拒绝 |
| mix_symbol_namespaces | 符号碰撞时混淆两命名空间 | 已拒绝 |

返工应使六个错误副本均由目标行为断言拒绝，同时 submitted 全通过。不是为了提高数量，也不要求给原正确产品伪造失败。

## R4（P2）：更正记录与 README

1. 规范 [§4](../../../docs/motif_identity_v1.md#4-手算完整键)从规划时就给出事实 c0/c1、JOIN head v0/v1；2693项冻结核对和独立字面量比较均证实未改。所谓“契约两处笔误”不存在。删除测试注释中的错误归因；旧 Pi provenance/执行记录保留，在新 R2 provenance及追加记录明确撤回。
2. “15个冻结fixtures均由40项覆盖”“硬隔离完成”“异常实例原样检查”“稳定hash检查”不由原测试支持，按本审阅实情更正。规划15例是 Codex 前提核验，不是 Pi motif 对照结果。
3. Pi 自述开发期多次失败，但现有6个 RUN 只有 docs 一次失败，无开发失败原件。相关命令、次数／时间、是否从首版未改实现仅能记自述／unknown，不补造。不写所有尝试均 immutable 留存。
4. 首次 docs 实际因越界 `.tmp_trim.py` 失败；其清理后 docs2/docs3 成功。`pi-r1-docs/run-index.json` 不存在，首个索引在 docs2；最终 docs3 索引记录5个前序 RUN。修正旧记录“仍在运行”、遗漏docs3及混写列表等过时叙述；在新记录更正，不回写旧原件。2693是文件数，不是所谓4070行。
5. [README:385](../../../README.md)声称既有回归，实际少了 `tests/test_proof_count.py`。按驱动列十四文件；“把同世界不同支持归为同一motif”改为“结构等价的不同支持可能具有同一motif”，避免把所有不同支持一概归并。已有 COPY 示例确实可运行。模型alias/reasoning来源仍为Pi自述，未由RUN采集。

## 验收与返工边界

| 项 | 本轮结果 |
|---|---|
| A1／A2／A3／A4 | 产品有限独立核验通过；对应提交测试需按R2/R3补齐 |
| A5 | 不通过：R1–R3及错误副本实证 |
| A6 | 提交范围／冻结／925全回归通过；README漏一文件另修 |
| A7 | 部分不通过：R4记录／归因／开发留证缺口 |

产品 `motif.py` 保持冻结，返工限 `tests/test_motif.py`、README、本任务状态／执行记录和新 `reports/T0014/pi-r2*`。源码79–82/100–101的可信内部格式额外检查对合法T0012输出不可达；本轮不据此要求重写产品或增加错误格式测试。

原始记录、规划、Codex报告与所有旧RUN均不改。一次完成下述交接追加的四步，不扩大实验范围，不重跑 full／doctor／GPU；沿用本轮独立925项full，新增测试以R2定向和守卫核验，不能宣称未来885+N全回归已跑。
