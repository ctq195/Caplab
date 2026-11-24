# `resume-content.json` 结构

构建器读取 UTF-8 JSON。完整机器约束见 `references/schemas/resume-content.schema.json`；以下字段决定实际行为。

- `meta`：`title`、`language`、`target_job`、`tailoring_mode`、`target_pages`、可选 `jd_source` 与 `two_page_reason`。`jd_tailored` 必须保留 JD 来源；`general_direction` 的目标名必须明确包含“通用岗位方向版”或等价英文标签。
- `candidate`：`name`、`headline`、`contact`。`headline` 用于学校、专业、年级等页首概况，可用 ` | ` 分隔；联系信息按字符串数组输入，模板不依赖图标。
- `sections`：按最终阅读顺序排列，类型为 `entries` 或 `lines`。
  - `entries` 项包含 `id`、`title`、可选 `date`、`subtitle`、`location`、条目自身的证据字段和 `bullets`。未知日期留空并进入 `open_questions`，不要把“时间待补”写进正式正文。
  - 每个 bullet 包含 `text`、`evidence_status`、`confirmed` 与 `source_ids`。
  - `lines` 项包含 `label`、`text`、`evidence_status`、`confirmed` 与 `source_ids`。
- `selected_evidence`：所有进入正文的来源 ID；正文的 `source_ids` 必须属于它。
- `selection_log`：每个候选经历或要点的 `item_id`、`decision` 和 `reason`。`decision` 为 `keep`、`hide` 或 `drop`。
- `open_questions`：未进入正文、但可能提升下一版质量的问题，最多保留当前轮最重要的 3 个。
- `scorecard`：六个固定评分维度、`hard_gate_passed` 和 1–3 的 `optimization_round`。

正文只允许 `direct` 或 `transferable`，且必须 `confirmed: true`。`supportable`、`gap` 和 `not_relevant` 只能出现在证据矩阵、选择日志或待确认项，不能进入正式正文。
