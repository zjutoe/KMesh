# T0019 提交与合并（2026-09-29）

用户明确要求先提交并合入 T0019。两个接受文件已提交为 **ffd1bdf4276c4347de6964627863a1368d5ff857**，从 T0019-motif-candidate-audit 快进合入本地 master；原 HEAD 为 e04706b2fa0541672c15a1ed5d6940784d9d43ae。提交只含 src/kmesh/logic/motif_candidates.py 与 tests/test_motif_candidates.py；未 push，已有规划材料保持未提交。

提交前，控制器为 accepted / round 3 / attempt 3；当前工作树匹配接受快照 0750811878ce82fb4bd14992810ecedb09c74f23ed0c2c5d7fe27b1000de3852，检查证据摘要也匹配。源码、测试的 Git blob 及两个工作目录中的 SHA-256 均与接受值一致。135 个仓外原始证据文件未改变；主仓库原有 80 个改动文件在快进时逐文件保留。详见 [merge.json](merge.json)。

合并后，在只读 bubblewrap 沙箱使用任务解释器和显式主仓库 PYTHONPATH，断言 kmesh 与 motif_candidates 实际导入路径属于 master，再执行定向测试：**32 passed in 15.09s**，退出 0、stderr 空。检查前后主工作区快照一致，见 [准确命令](focused/launch.json)、[输出](focused/stdout.txt)及 [环境与核验结果](verification.json)。未重复全量回归；接受版本原控制器 1082 项通过证据保留。

预提交格式检查发现接受测试第 869 行存在一行尾部空白，首次脚本在 commit 前停止。为保持接受内容逐字一致，记录 [首次停止原因](attempt-1.json)及 [格式提示](accepted-whitespace-warning.txt)，随后仅允许这一已知提示继续提交；不把 git diff --cached --check 写成通过，也未改产品／测试或验收条件。

Git HEAD／索引因授权提交而改变，当前完整工作树 digest 因此不再等于验收前值；文件条目仍完全相同，[merge.json](merge.json)记录了接受快照到 Git commit 的映射。原接受摘要中的 integrated_into_main=false 描述同步验收时点，本页记录后续授权合并。原工作树交接和历史失败记录未改。

T0020 尚未发布。其独立环境与 manifest 准备应以这次合并后的 master 为基线，不再重复注入 T0019 的未提交文件。
