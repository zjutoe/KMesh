# T0020 r2 发布准备

基线 master@ffd1bdf4276c4347de6964627863a1368d5ff857 已含 T0019 接受实现；独立工作树和同名分支为 /home/mye/data/kmesh-worktrees/T0020-motif-split-catalogue。原任务工作树与证据不迁移。主仓库未提交的规划材料作为只读 intake 随发布快照保留，Pi 只能修改 manifest 的两个允许文件。

- [环境与完整结果](environment-summary.json)：Python 3.13.5、pytest 8.3.4、离线 editable 安装，新工作树导入路径已核验。
- [新基线输出](baseline-full/stdout.txt)：1082 passed in 33.88s，退出0，stderr空；只读检查前后快照一致，源码无缓存。
- [真实模型预检摘要](model-connectivity.json)：Pi bonsai/bonsai2-27b/xhigh 与 Codex gpt-6-astra/xhigh 均获得预期最小响应及成功终态。预检不是产品实施；原始会话和认证在 /home/mye/data/kmesh-T0020-preparation-ksjxvn_u/models-r1/，不导出到 Git。
- [r1 原契约](prior-contract-r1/handoff.txt)及 [hash](prior-contract-r1/sha256.json)保留。r2 只改变实际基线与运行准备，不变更接口／科学协议。
- [发布 manifest](../task.json)：最多4轮，Pi/Codex单进程各7200秒，总14400秒；三项检查各180秒，两个精确允许路径。

使用已部署的 Codinator user service；指定 Pi 配置 ~/.config/codinator/pi，Pi直连本地Bonsai，Codex使用既有代理。Codinator版本32c187e。发布前的完整快照和 hash 将由控制器冻结；后台状态以 SQLite 为准，原生 Pi 任务不迁移。
