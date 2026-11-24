# 简历输出合同

## 输入最小集

- `target_job`：岗位名称与 JD；
- `master_resume`：主简历或结构化经历；
- `confirmed_evidence`：可选的补充证据；
- `output_preferences`：可选的语言、页数、模板和格式。

只有岗位名称、没有 JD 时，输出必须标记为“通用岗位方向版”或先补齐要求来源，不能称为针对某一真实招聘启事的定制版。

## 输出对象

- `job_requirements`：岗位要求及来源；
- `evidence_matrix`：每项要求的证据状态；
- `change_set`：修改前后、理由、来源与确认状态；
- `resume_content`：可编辑的岗位版内容；
- `target_pages`：默认 1，只允许 1 或 2；两页必须记录 `two_page_reason`；
- `content_height_ratio`：构建后第一页正文垂直范围占页面高度的比例；小于 `0.75` 时触发舒展排版和事实受控的内容补充流程；
- `selected_evidence`：进入正文的证据来源 ID；
- `selection_log`：经历与要点的保留、隐藏、删除及理由；
- `scorecard`：六维评分、证据、扣分点、事实硬门槛和优化轮次；
- `artifacts`：`resume-content.json`、`resume.tex`、可选 `resume.pdf` 与 `resume-scorecard.md` 的实际路径；
- `open_questions`：必须由用户确认的事实；
- `export_status`：`not_exported`、`generated_unverified` 或 `generated_verified`；
- `limitations`：未验证的兼容性、缺失资料和真实能力缺口。

`export_status` 保持兼容：`not_exported`、`generated_unverified`、`generated_verified`。有 `.tex` 但无 PDF、分数未达门槛、页数超限或视觉未检查时都只能使用 `generated_unverified`。

本合同是对话与产物约定，不是 V2.1.1 `caplab_state` 的新增字段。不得把这些对象写入 `caplab_state.json`。
