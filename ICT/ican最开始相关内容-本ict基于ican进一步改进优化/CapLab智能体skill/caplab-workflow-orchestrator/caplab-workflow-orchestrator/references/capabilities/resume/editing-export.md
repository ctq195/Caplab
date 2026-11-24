# LaTeX 编辑、篇幅与导出边界

## 内容与呈现分层

维护一个与具体版式无关的内容模型，再把它渲染到模板。至少保留：基本信息、摘要、经历、项目、教育、技能、证书或作品链接；每个条目保持稳定 ID，便于重排和局部修改。

每次岗位定制生成新版本，记录目标岗位、创建时间、来源版本和变更摘要。不要原地覆盖唯一主版本。

## 编辑原则

- 版式变化不应偷偷改变内容事实。
- 重排、隐藏和删减要可回退；隐藏内容仍留在主版本中。
- `.tex` 与 PDF 必须来自同一份已确认内容模型。
- 模板优先保证阅读顺序、标题层级、对比度、留白和机器可提取文本；装饰不能压过内容。
- 默认模板沿用用户提供的 260608 `.tex` 视觉体系：A4 单栏、黑白正文、居中三行页首、章节标题下横线、日期右对齐和紧凑项目符号；不复制其中的个人内容。
- 不使用图标、进度条、文本框或复杂表格。

## 一页控制顺序

1. 先移除重复技能、弱相关课程和低价值经历。
2. 再合并同义句、缩短背景叙述，保留行动、技术、对象和结果。
3. 运行 `resume_pipeline.py build`。normal 复现参考模板的 10pt、13.5mm 页边距和章节间距；内容过多时再尝试 compact、tight，最低 9pt、12.7mm。
4. 若 normal 已是一页但正文垂直范围低于页面高度的 75%，先尝试 relaxed：适度放大字号、行距、章节间距和页边距。
5. relaxed 后仍低于 75% 时，可补充动作、技术/方法、对象/任务、个人决策和结果描述，但每一句都必须来自已确认材料。材料不足时留下最多 3 个高价值问题，允许合理留白，不得编造内容填页。
6. 三档压缩后仍超过一页时返回内容删减，而不是继续缩字。只有高价值内容不能再删时，明确填写两页理由并以 `target_pages: 2` 重建。

## 构建

从 Skill 根目录运行：

```bash
python scripts/resume_pipeline.py build --input <resume-content.json> --output-dir <output-dir> --sources-dir <sources-dir>
```

脚本保留 `resume-content.json` 和 `resume.tex`，若 `latexmk -xelatex` 可用则生成 `resume.pdf`，并检查实际页数、正文占页高度、missing glyph 与 overfull box。构建成功仍是 `generated_unverified`，因为内容与视觉复核尚未全部完成；以四维 delivery_status 为准。

优先用 Poppler 将 PDF 渲染为 PNG；若运行环境的 Poppler 缺少中文 CMap，必须记录该限制并改用可正确显示嵌入字体的 PDF 渲染器（如 PyMuPDF）复核，不能把缺字预览判为简历缺字。视觉检查 PDF 后运行：

```bash
python scripts/resume_pipeline.py verify --output-dir <output-dir> --sources-dir <sources-dir> --visual-reviewed --content-reviewed
```

## 导出验收

只有实际生成文件后才报告“已导出”。若工具允许，至少检查：

1. `.tex` 与 PDF 可打开，实际页数不超过 `target_pages`；
2. 无截断、重叠、空白页、乱码或缺失字体；
3. 标题、日期、链接和项目符号一致；
4. 可提取文本顺序与视觉阅读顺序基本一致；
5. 文件名不泄露不必要的内部备注或敏感信息。

视觉检查、文件存在、文本可提取和 ATS 兼容性是不同结论，分别报告。没有 XeLaTeX 时保留结构化 JSON 与 `.tex`，并明确 PDF 尚未生成；不得改用 DOCX 冒充计划中的正式产物。

## 运行依赖与样例

LaTeX 编译需要系统提供 `latexmk`、XeLaTeX、ctex/Fandol 中文字体与模板中的 LaTeX 宏包；这些不随 Skill ZIP 内置。页数检查需 `pdfinfo`；正文占页高度及备用文本提取需 `pdfplumber`（见根目录 `requirements-resume.txt`）。视觉检查需 Poppler 或 PyMuPDF。不得将 RAG 的零模型下载宣传理解为 LaTeX 零依赖。

随包 `tests/fixtures/resume-synthetic.json` 是明确虚构的测试材料，不可当作用户资料。构建示例：

```bash
python scripts/resume_pipeline.py build --input tests/fixtures/resume-synthetic.json --output-dir <独立样例输出目录>
```

每个岗位版本使用独立输出目录。重建失败时会清除同目录旧 PDF/日志，避免把旧文件误报为本轮结果。缺少任何验收工具时保持 `generated_unverified` 并说明缺项。

## 程序化输出门

遵循 [每轮与交付运行合同](../../runtime-guards.md)。任务/承诺在独立账本校验，用户暂停时 deferred；证据和交付由脚本重新检查，不由模型的布尔标记授权。
