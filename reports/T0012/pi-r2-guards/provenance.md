# T0012 R2 返工 provenance（Pi，awaiting_review）

- 模型/来源：Pi，`PI_MODEL=bonsai2-27b`（用户已授权）。
- 基线 HEAD：`56b41de11a2651da6151da615230117f0d96bd6e0d6e92`（T0011 冻结基线）；分支 `T0012-proof-key`；未 commit/push。
- 产品冻结：`src/kmesh/logic/proof_key.py` 未修改，SHA-256 `92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`。
- 测试：`tests/test_proof_key.py` 因新增守卫测试而变，SHA-256 `8e1df17c4035d4790028dccdadc21f1c05a58e59b3609fe5bdc0dcbf0b7d3551`。

## 新 RUN（每条新 RUN、未复用；record.json 均留存于对应目录）

| RUN dir | 原始命令 | exit | elapsed_s | started_at_utc |
|---|---|---:|---:|---|
| pi-r2-preflight | `record_check.py pi-r2-preflight -- .venv/bin/python reports/T0012/review-r1/check_rework.py preflight` | 0 | 0.23 | 2026-09-22T02:19:34 |
| pi-r2-readme | `record_check.py pi-r2-readme -- .venv/bin/python reports/T0012/review-r1/check_rework.py readme` | 0 | 0.26 | 2026-09-22T02:33:34 |
| pi-r2-guards | `record_check.py pi-r2-guards -- .venv/bin/python reports/T0012/review-r1/guards.py reports/T0012/pi-r2-guards --enforce` | 0 | 5.63 | 2026-09-22T03:16:51 |
| pi-r2-docs | `record_check.py pi-r2-docs -- .venv/bin/python reports/T0012/review-r1/check_rework.py docs` | 0 | — | 2026-09-22T（docs RUN，本文件所在 RUN 前） |

（pi-r2-docs 为当前 RUN，run-index.json 生成于该 RUN；此处仅引用其存在。finish/end 时间各 record.json 留存，见相应目录。）

## 结果证据

- guards：`all_guards_valid=True`；8 个违约副本全拒（allow_unused_steps, float_variable_number, coerce_clauses, rebuild_exception, lazy_forbidden_import, diagnostic_suffix, ignore_deep_tie, always_sort_children）；submitted 控制 exit 0。
- README：K1 代码块原样可运行（readme RUN exit 0）。
- 测试：focused 52/52；十二文件 847/847（840 原 + 7 新增守卫）。

## R5 更正与保留（不重写旧原件）

- R1 的 6 类守卫漏过、README 示例失败、执行史“108 项复验”无原始 RUN 原件：已标为自述/unknown；本 R2 以新 RUN 留证，不删除/移动/重录旧 RUN。
- 旧 Pi/Codex RUN、`pi-r1-full/provenance.md`、规划材料冻结，不改。
- 未来 Codex 复验结论：未预填（`not_run`/`Codex` 待填）。
