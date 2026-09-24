# T0012 R3 返工 provenance（Pi，awaiting_review）

- 模型/来源：Pi，`PI_MODEL=bonsai2-27b`（用户已授权）。记录实际 provider/模型完整名；无法独立采集的标自述。
- 基线 HEAD：`56b41de11a2651da6151da615230117f0d96bd6e0d6e92`（T0011 冻结基线）；分支 `T0012-proof-key`；未 commit/push。
- 产品冻结：`src/kmesh/logic/proof_key.py` 未修改，SHA-256 `92dce0d424a60ae3f1f0d46a49da989eb8367258c287107a68ac541b637e03c1`。
- 测试：`tests/test_proof_key.py` 因新增身份/长链/类型断言而变，SHA-256 `96d08b9b7fadcb226e8b10d9c0f5f62b9b65f4cfd346fd8167242afaaef9f1a6`。

## 新 RUN（每条新 RUN、未复用；record.json 均留存于对应目录）

| RUN dir | 原始命令 | exit | elapsed_s | started_at_utc |
|---|---|---:|---:|---|
| pi-r3-guards2 | `record_check.py pi-r3-guards2 -- .venv/bin/python reports/T0012/review-r2/guards.py reports/T0012/pi-r3-guards2 --enforce` | 0 | 11.265 | 2026-09-22T18:20:13 |
| pi-r3-focused | `record_check.py pi-r3-focused -- .venv/bin/python -m pytest -q tests/test_proof_key.py` | 0 | 0.749 | 2026-09-22T18:21:18 |
| pi-r3-readme | `record_check.py pi-r3-readme -- .venv/bin/python reports/T0012/review-r3/check_readme.py` | 0 | 0.088 | 2026-09-22T18:22:37 |
| pi-r3-docs | `record_check.py pi-r3-docs -- .venv/bin/python reports/T0012/review-r3/check_docs.py` | 0 | — | 2026-09-22T（docs RUN，本文件所在 RUN 前） |

（`pi-r3-docs` 为最终 RUN，在 docs/provenance 落盘后运行；其 record.json 生成于该 RUN，此处仅引用其存在。finish/end 时间各 record.json 留存，见相应目录。）

## 结果证据

- guard（pi-r3-guards2，用 R2 `guards.py`）：`all_guards_valid=True`；`submitted` exit 0/0 失败；10 个反例全 reject——R1 八个（allow_unused_steps, float_variable_number, coerce_clauses, rebuild_exception, lazy_forbidden_import, diagnostic_suffix, ignore_deep_tie, always_sort_children）+ R2 新增两项（rebuild_exception_with_context, lazy_dependency_import），共 11 项，完整于 `pi-r3-guards2/guards.json`。
- README RUN：K1 代码块原样提取并实际运行，exit 0（非 dry-run）。
- focused（pi-r3-focused）：54/54 通过；含 R3 新断言（异常精确 D 组 20 项、身份矩阵 K1–K8 全手算键 + oracle + T0009 逐树键集、1201-header 不同关系长链全 header、各层真实类型检查、导入隔离硬封锁）。
- docs RUN：README/implementation_status/handoff 三处 T0012 状态一致（`awaiting_review`）、均指向 `pi-r3-guards2` 与本文 provenance；关键相对链接可解析；HEAD 冻结。

## R3 相对 R1–R2 的更正与保留（不重写旧原件）

- 长链从“同一自环规则重复、只查末 header”改为“不同关系链（a0 事实→a1→…→a1200）并逐 header 检查”；旧长链断言即本轮新断言（新测试文件名未改）。
- 异常检查从“`.__all__` 文本匹配 + 旧 verifier 调用”改为对 `canonical_proof_key` 直接断言精确异常类型/全文，并用 monkeypatch sentinel 做 `is` 身份检查（不再用 `__suppress_context__` 文本）。
- 移除已无用的 `_ground_key`、`canonical_clause_key` 导入；`test_type_soundness` 扩为各层真实类型检查。
- R1 的 dev 失败、R2 的“847 full 无原始 RUN”仍按留证规则保留自述/unknown；R3 以新 RUN 留证，不删除/移动/重录旧 RUN。旧 Pi/Codex RUN（R1/R2）、provenance、规划材料冻结不改。
- 未来 Codex 复验结论：未预填（`not_run`/`Codex` 待填）。
