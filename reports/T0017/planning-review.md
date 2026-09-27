# T0017 发布前设计核验

2026-09-26，主会话Codex准备设计，非作者 `/root/review_t0017_design`（gpt-6-astra／xhigh）两轮只读核对现有契约与具体草稿，结论为修正两处表述后可ready：Q9只排除无关证明的motif收集，不跳过全世界推导；文件不存在前提限定首轮，返工继续指定快照。两处已修订。该审阅未修改产品／测试、未调用模型或复跑pytest，不作产品验收。

设计保留T0009完整枚举、逐原始树T0016调用、末尾完整键集合去重；空枚举O校验、首枚举错误优先、晚失败无部分结果、O不累计、S原样透传等均已明确。直接禁止调用与既有间接依赖区分，隔离只禁无关四根。未改变身份等价关系／E0/E1／数据准入或正式split。

Codex主会话在新工作区以已验收公共API执行 [planning_probe.py](planning_probe.py)：11行手算完整键、C/D/S精确边界、先事实后JOIN的晚O超限与“3条规范证明只有2个结构键”均通过。原始命令／输出／源码前后hash见 [fixture RUN](planning-fixtures-r1/record.json)与 [stdout](planning-fixtures-r1/stdout.txt)；该脚本不是待实现API或新测试oracle。另在该工作树CPU环境复跑 [960项基线](planning-baseline-r1/stdout.txt)，退出0、stderr空、源码／测试前后hash不变，见 [record](planning-baseline-r1/record.json)。没有T0017实现／验收结果。

基线master为783cdd2dd00643815f084d97fbd1038265a2003c，独立工作区为 `/home/mye/data/kmesh-worktrees/T0017-query-motifs`。独立venv经 `--system-site-packages` 创建，`pip install --no-index --no-build-isolation --no-deps -e .` 成功，无下载；Python3.13.9／kmesh0.1.0／pytest8.4.2与精确editable路径在fixture输出中。首次pip只提示缓存目录不可写而自动禁用缓存，安装退出0。

发布前Codinator队列仅有accepted T0016；服务active/running，Codex代理为localhost:8888，Pi子进程仍清除代理直连。只读进程检查未发现pi/node进程。本次用户已授权拆分并运行下一项，不调用其他模型；清单4轮／4小时／单agent1小时，仅两个实现路径。不授权commit/push/merge。发布后冻结工作树，终态再同步文档；历史T0016验收原件不改写。
