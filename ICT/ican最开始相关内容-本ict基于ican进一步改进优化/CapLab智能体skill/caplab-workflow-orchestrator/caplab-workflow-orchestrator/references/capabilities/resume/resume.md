# CapLab 岗位简历制作辅助能力

版本：2.1.1（生成模块迁移自 v1.4.0）（一页优先的 XeLaTeX 生成、评分与验收闭环）

当用户明确要求制作、定制、编辑、排版或导出简历时使用。它保留“主简历 + 目标 JD + 证据矩阵”的既有链路，正式输出改为结构化内容、可编辑 LaTeX 源文件和 PDF。

## 执行顺序

1. 保留主简历，不覆盖唯一原件；读取教育、项目、实习、竞赛、技术栈、语言、日期、个人决策、指标、个人贡献与结果。
2. 拆解 JD 的职责、必备项、加分项、交付对象和用词，区分原文与推断；没有 JD 时只能生成“通用岗位方向版”。
3. 建立证据矩阵，按 `direct`、`supportable`、`transferable`、`gap`、`not_relevant` 标记。正文只使用用户本轮确认或有效 CapLab 资料支持的事实。
4. 信息缺口会显著改变岗位匹配、结果强度或时间线时，每轮最多询问 3 个高价值问题；低价值缺口不阻塞生成，也不得自行补造。
5. 按岗位覆盖、证据强度、技术关键性、量化成果、个人贡献、认可度、时效性和单位版面信息量筛选经历，并按 [岗位筛选规则](tailoring-workflow.md) 形成可回退的 `selection_log`。
6. 每条经历优先写成“动作 + 技术/方法 + 对象/任务 + 结果”。没有可核验数字时使用真实定性结果或列为待确认，不为满足句式编造结果。
7. 按 [结构化内容规范](resume-content-schema.md) 创建 `resume-content.json`，使用 `scripts/resume_pipeline.py build` 先按随包 `assets/resume/resume-template.tex` 样式排版；过密时尝试紧凑和最小可读档，正文占页高度不足 75% 时尝试舒展档。
8. 读取 `resume-scorecard.md` 与构建报告。低于 85 分、核心维度明显不足、超出目标页数或出现编译/排版问题时，优先删选和改写内容，最多自动优化 3 轮；需要新事实时停止并追问。
9. 将 PDF 渲染为图片，检查裁切、重叠、字体、日期、标题层级和留白；再检查文本提取顺序。只有这些检查完成后才能运行 `verify --visual-reviewed` 并报告 `generated_verified`。

## 一页与两页

- 默认 A4 单栏一页；先删弱相关和重复内容，再压缩措辞，最后才收紧排版。
- 一页正文垂直范围低于页面高度 75% 时，先适度放宽字号与间距；仍稀疏时只从已确认材料补充动作、技术对象、个人决策或结果描述，不为填页创造事实。
- 正文字号最低 9pt，页边距最低 12.7mm；禁止用极端缩字、负间距或裁切伪造一页。
- 必需且高价值内容经筛选后仍无法保持可读性，才将 `target_pages` 改为 2，并填写 `two_page_reason`。
- DOCX 不再是默认或必需交付物。缺少 XeLaTeX 或编译失败时仍保留 `.tex`，但状态只能是 `generated_unverified`。

## 按需读取

- 岗位拆解、追问与经历筛选：[tailoring-workflow.md](tailoring-workflow.md)
- LaTeX 构建、一页控制和导出验收：[editing-export.md](editing-export.md)
- 输入输出合同：[resume-contract.md](resume-contract.md)
- 结构化内容字段：[resume-content-schema.md](resume-content-schema.md)
- 评分与优化：[scoring-rubric.md](scoring-rubric.md)
- 参考项目与边界：[source-notes.md](source-notes.md)

本能力不写 `caplab_state.json`，不改变 `active_stage` 或 revision。评分仅用于内部优化，不是 ATS 官方评分、录用概率或招聘方判断。

## 知识库权限

简历制作无需 VIP。使用用户材料即可开始；需要知识库时遵循 [VIP 标识协议](../../vip-access.md)，保留 `ICANDumate_VIP:enabled` 精确匹配与当前用户会话隔离。知识库内容不能替代个人事实证据。评分由助手依据材料填写，脚本校验字段与阈值，不代表独立客观测评。

## 程序化输出门

遵循 [每轮与交付运行合同](../../runtime-guards.md)。任务/承诺在独立账本校验，用户暂停时 deferred；证据和交付由脚本重新检查，不由模型的布尔标记授权。
