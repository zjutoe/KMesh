# T0016：逐发生位置的完整有根子树 motif 目录

## 任务信息

- 任务编号／修订号：T0016 / r1。
- 状态：accepted
- 所属阶段：M1 数据审计前置原语；研究计划 v0.1.3，E0 `e0_v2` / E1 `e1_v3` 不变。
- 规划者／验收者：Codex + `gpt-6-astra`，`xhigh`；执行者：Pi + `bonsai2-27b`，`xhigh`。
- 基线：`011fc81cd6c6396a1de8cd0179ef7f658aae0fa0`，分支 `T0016-subtree-motifs`。
- 工作目录：`/home/mye/data/kmesh-worktrees/T0016-subtree-motifs`。
- 发布前已有 Codex 规划改动：AGENTS、decisions、README、implementation_status、本交接、handoffs/TEMPLATE及 reports/T0016；均在控制器 intake 中冻结，Pi 不修改。
- 前置依赖：[T0014](T0014-proof-motif.md)、[T0015](T0015-proof-subtree.md) 均已 accepted；T0015 的17项定向检查与已核验934项回归见其验收记录。本任务新环境的934项基线与样例核对见 [规划记录](../../reports/T0016/planning-checks/)。
- 必读：[AGENTS §8](../../AGENTS.md)、[D34/D35](../decisions.md)、[motif 定义](../motif_identity_v1.md)、`src/kmesh/logic/motif.py`、`src/kmesh/logic/proof_subtree.py`、`src/kmesh/logic/proof.py`。

## 目标、范围与交付物

单一目标：给定一棵合法证明，返回其每个发生位置对应的**完整支持子树**的现有 motif 键。

Pi 仅可新建／修改：

1. `src/kmesh/logic/subtree_motifs.py`
2. `tests/test_subtree_motifs.py`

不得修改现有产品／测试、包初始化、依赖、规划／报告文件。Pi 的逐轮汇总和完成标识写入控制器提示指定的外部 `delivery/summary.md` 与 `completion.json`，不写入本交接。终态由 Codex 同步回仓库。该自动流程覆盖旧任务的手工状态和 record_check 留证方式，见 AGENTS §8。

不属于本项：任意裁剪片段匹配、世界级泄漏审计、跨样本 split、证明搜索／枚举、唯一性计数、模型输入、训练、CLI、持久缓存或摘要哈希。

## 前提、成本与停止条件

- Python 3.13.9、kmesh 0.1.0 editable、pytest 8.4.2；`.venv/bin/python` 已指向此工作区源码，无需安装。
- 只用标准库与已验收公共依赖；合成内存 fixture，无数据集／网络／GPU／模型下载访问。实际 Pi/Codex 身份由控制器记录，不能以模型自述替代。
- T0014 接受的有限合法循环证明、ProofStep 子类仍可使用；本层不新加关系 DAG 限制。
- 返回目录与原证明存储顺序相关，**不是规范整树键**。同 motif 的多个发生仍分别保留。
- 所有子树输出总长度为 `sum(size(subtree_i))`；n 步链有 n(n+1)/2 个 Header。公共依赖会重复验证；参考版本允许该成本，不声称线性时间。T0014 自身方向枚举成本仍存在。
- 控制器最多4轮，任务墙钟4小时，单阶段1小时；检查每条最多180秒。只做小规模CPU检查，不跑1200步的全部子树目录。依赖契约矛盾、越界或基础设施错误交回 blocked，不擅改预算／研究设计。

## 接口与算法契约

```python
# src/kmesh/logic/subtree_motifs.py
__all__ = ["proof_subtree_motif_keys"]

def proof_subtree_motif_keys(
    clauses, query, proof, *, max_steps=10_000, max_orientations=100_000
) -> tuple[tuple, ...]: ...
```

只需一个公开函数。不新增异常、验证器、通用遍历器或 motif 编码实现。

1. 第一项业务操作恰一次调用 T0014 `canonical_motif_key(clauses, query, proof, max_steps=max_steps, max_orientations=max_orientations)`；三个对象和预算原样传递，保存整树键。此前不得 `len`、遍历、转 tuple、复制或自行校验输入。
2. 成功后令 `n=len(proof)`。按 `i=0..n-2`，调用 T0015 `extract_proof_subtree(clauses, query, proof, i, max_steps=max_steps)`，再调用 T0014 `canonical_motif_key(clauses, proof[i].conclusion, sub, max_steps=max_steps, max_orientations=max_orientations)`；其中 `sub` 就是抽取返回的原对象。
3. 按以上次序收集键，最后附加第1步已保存的整树键，返回真正 tuple。不再抽取／计算末根，不排序、不去重。

一次成功调用共 n 次 T0014、n−1 次 T0015；单事实为1次／0次。所有依赖异常实例直接传播，不捕获、重建、重试或部分返回。输入错误及优先级完全沿用首次 T0014 调用；函数签名错误仍为普通 TypeError。

`max_steps` 先约束全输入且全程原样透传；`max_orientations` 是**每棵子树各自**的方向数上限，不做累计扣费。整树含全部双前提节点，最先执行可提前发现整树 O 不足。不引入总目录预算。

## 手算样例（完整字面键）

```python
from kmesh.logic.types import Atom, Clause
from kmesh.logic.proof import ProofStep

def a(pred, x, y):
    return Atom(pred, (x, y))

W = (
    Clause((a("u","?x","?y"), a("v","?y","?z")), a("w","?x","?z")),
    Clause((), a("q","b","c")),
    Clause((a("p","?x","?y"),), a("u","?x","?y")),
    Clause((), a("p","a","b")),
    Clause((a("q","?x","?y"),), a("v","?x","?y")),
)
Q = a("w","a","c")
P = (
    ProofStep(3, (), a("p","a","b")),
    ProofStep(1, (), a("q","b","c")),
    ProofStep(2, (0,), a("u","a","b")),
    ProofStep(4, (1,), a("v","b","c")),
    ProofStep(0, (2,3), Q),
)
FACT_KEY = ("proof_motif_v1", (((0,0,1), (0,("c",0),("c",1)), ()),))
COPY_KEY = ("proof_motif_v1", (
    ((0,0,1), (0,("v",0),("v",1)), ((1,("v",0),("v",1)),)),
    ((1,0,1), (1,("c",0),("c",1)), ()),
))
MAIN_KEY = ("proof_motif_v1", (
    ((0,0,1), (0,("v",0),("v",1)),
     ((1,("v",0),("v",2)), (2,("v",2),("v",1)))),
    ((1,0,2), (1,("v",0),("v",1)), ((3,("v",0),("v",1)),)),
    ((3,0,2), (3,("c",0),("c",2)), ()),
    ((2,2,1), (2,("v",0),("v",1)), ((4,("v",0),("v",1)),)),
    ((4,2,1), (4,("c",2),("c",1)), ()),
))
EXPECTED = (FACT_KEY, FACT_KEY, COPY_KEY, COPY_KEY, MAIN_KEY)
```

主例 `max_steps=5,max_orientations=2` 返回 EXPECTED，共11个 Header；max_steps=4 抛原 ProofLimitError，O=1 抛原 MotifLimitError。单事实返回 `(FACT_KEY,)`。手算键已由 Codex 使用既有依赖核对；测试中直接保留字面量，不从实现生成 expected。

## 实施步骤（五步）

1. 核对分支／基线、环境、允许文件起点，读取契约与现有API；异常交回。不要修改冻结手稿或另建 venv。开发命令通过 Pi 工具运行，其原始事件由控制器保留。
2. 在唯一产品文件实现上述三步组合；公共依赖按名导入，便于在真实调用位置 spy。保持包 `__init__.py` 零导入，不复制依赖算法。
3. 编写下列五组测试。以完整字面量、对象身份、真实变换和错误路径为证，不以测试计数达标。建议合并相关断言，避免庞大生成器和私有 oracle。
4. 运行定向及完整CPU回归。每次开发尝试用不同 `/tmp/kmesh-T0016-dev-N` basetemp；保留所有失败工具事件，修复已明确范围内错误。不要把新成功当旧失败原件。
5. 在外部 delivery 汇总产品／测试、实际命令和失败、自述与结构化检查来源、未运行项、限制；生成控制器要求的 completion.json。不得自行 accepted／commit／push；控制器执行必需检查与独立 Codex 验收，有返工则按原冻结契约继续。

### 五组测试要求

**A，语义与发生位置。** 单事实及完整主例等于上面的字面量；输出类型严格 tuple，键可 hash。将主例步骤按旧序号 `(0,2,1,3,4)` 重排并重映射所有前提引用，独立 verifier 为 True，输出恰为 `(F,C,F,C,R)` 且确实不同于原目录。反转世界 clauses 并仅重映射 clause_index（refs不变）则目录相同。全局关系／常量改名＋各规则局部变量双射改名，实际字段改变、目录不变。调用前后深拷贝字段和 hash 不变。

**B，完整支持与边界。** 同一 fact step 对象占两个位置，规则 `p(x,y),p(x,y)->q(x,y)` 的两 refs 为0/1，输出3键且前两键同F，不去重；O=2成功、O=1失败（全部目录方向成本相加为4，仍只需O=2）。有限合法 `p(a,b)→q(a,b)→p(a,b)` 给出3个键，Header长度1/2/3，不因关系循环被拒。用必填额外 note 的 ProofStep 子类构造主例，仍等于 EXPECTED。32步、不同谓词的 COPY 链给出32键、Header长度1..32，总528；不改递归限制。另构造 `FACT→COPY→INV→INV`，对照独立 `FACT→INV→INV` 的 T0014 键，后者不在前者目录中；证明本API不表示任意内部裁剪片段匹配。此组辅助 expected 可调用已验收 T0014/T0006，但不能替代 A 的手算目录。

**C，调用次序与预算。** 在本模块的真实调用点 monkeypatch spy：首次是全树T0014，然后T0015根0..3各紧跟对应子树T0014，末根不抽取／重算。用 `is` 检查原W/Q/P、子查询是原步骤结论、sub为抽取返回对象；断言默认预算10000/100000和非默认7/2原样传递；n=1无抽取。三种位置（首次T0014／后续抽取／后续子树T0014）的哨兵异常必须原实例传播，调用在故障处停止，无重试／后续调用。

**D，输入委托。** 用真实API确认空proof、proof生成器、clauses列表、非法O以及主例max_steps=4失败；生成器 body 的 consumed 标记保持空，主例5/2成功。完整异常类／消息与直接T0014对照；非法proof叠加非法O保持首次T0014优先级。签名缺参、多余位置／未知keyword为TypeError，__all__精确。不要为已委托校验重写整个T0014输入矩阵。

**E，硬导入隔离。** 干净子进程 `python -I -c ...`，显式将此工作区src绝对路径插入sys.path，断言实际模块__file__精确匹配。finder阻断 `torch`、`yaml`、`kmesh.logic.engine`、`kmesh.logic.reference_engine`、`kmesh.logic.proof_enumeration` 的根和点前缀。自检真正import根和占位包 `__path__=[]` 下子模块（准确完整ImportError消息、finally清理），finder保持到产品真实主例调用结束；扫描sys.modules无上述根／前缀。不得用找不到的私有模块或手调find_spec冒充硬阻断；不用这些禁用模块构造fixture。

## 验证命令与控制器

工作目录同任务信息。控制器 [manifest](../../reports/T0016/task.json) 以参数数组运行以下两项，禁写工作树；每次控制器进程有独立 `/tmp`：

```bash
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0016-focused tests/test_subtree_motifs.py
env CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p no:cacheprovider --basetemp /tmp/kmesh-T0016-full tests
```

期望：两项退出0，无skip/xfail；full为既有934＋实际新增收集数。产品／测试只在2条允许路径，旧件哈希由控制器快照保护。无随机试验seed（N/A）；只有显式固定fixture。控制器的真实执行模型身份、快照和必需检查结果是权威记录，Pi自述不是独立验收。

## 验收标准

- A1：公开接口、精确委托序列／对象／预算、异常身份符合契约；无额外校验／搜索／编码。
- A2：手算完整目录、原位置、重复发生、真实变换／纯度通过。
- A3：全输入S边界与单子树O边界、共享对象发生、循环证明、必填note子类通过。
- A4：32链与裁剪片段负例通过，成本／研究范围陈述准确。
- A5：调用守卫、错误委托、签名、导入隔离的断言实际生效，无测试自误或空操作。
- A6：新测试和934既有回归成功，无范围越界；独立审阅实际diff，不以全绿代替审阅。
- A7：控制器记录身份／进程退出／协议完成／交付／提交摘要一致，留存失败与偏差。Codex只接受绑定本轮快照的产物。

## 执行与验收记录

自 T0016 起按 AGENTS §8：本文发布后对 Pi 和自动审计器只读。逐轮 Pi 汇总在状态目录 `tasks/T0016-subtree-motifs/attempt-NNNN/delivery/summary.md`；结构化审计在同轮 `review-delivery/verdict.json`，自动返工在下一attempt。Codex主会话在终态后追加脱敏摘要与本地证据位置，原始发布契约在 intake 中永久保留。

发布时尚未实施；下列终态记录由 Codex 依据控制器原件同步，Pi 未回写冻结契约。

### Codex 终态同步：2026-09-26

控制器已于14:26:15 UTC标记 **accepted**（round 2 / attempt 3），事件 `T0016-subtree-motifs:3:accepted`。attempt 1的Pi交付和检查成功，Codex额度中断；用户授权仅审计恢复到attempt 2，发现一处异常路径测试守卫缺口 `T0016-R1`。控制器自动安排attempt 3，仅补强测试，产品未改，26项定向／960项完整回归通过，独立审计再次26项通过并验证错误实现会被拒绝，关闭R1，A1–A7接受，无遗留问题。

接受产品 `2898ef24…fbde`、测试 `d1034e59…e851`，完整hash／提交快照、命令结果引用和研究限制见 [验收报告](../../reports/T0016/acceptance/review.md)与 [结构化摘要](../../reports/T0016/acceptance/summary.json)。[发布时契约原件](../../reports/T0016/acceptance/published-handoff.txt)保留；全文状态及本节为接受后的Codex记录，不改变原验收标准。

主会话已核对接受快照、过程退出／事件／hash及最终判定，本次没有重新实施、调用模型或复跑检查。产品／测试保持接受版本，未commit/push/merge。结果位于T0016独立worktree，不自动合并到主工作区。
