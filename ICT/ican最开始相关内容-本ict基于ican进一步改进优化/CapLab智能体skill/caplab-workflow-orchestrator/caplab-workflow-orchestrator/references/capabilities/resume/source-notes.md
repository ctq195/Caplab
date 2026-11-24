# 参考项目与取材边界

访问日期：2026-08-28。

## Resume Matcher

- 官方仓库：https://github.com/srbhr/Resume-Matcher
- 借鉴：主简历作为稳定源、输入目标 JD、生成岗位版建议、用户编辑、模板选择和 PDF 输出的产品链路。
- 本 Skill 的额外约束：要求每项修改回指证据，不把匹配分数当录用概率，不编造关键词对应经历。

## Reactive Resume

- 官方仓库：https://github.com/amruthpillai/reactive-resume
- 架构文档：https://docs.rxresu.me/contributing/architecture
- 借鉴：schema、纯内容逻辑、PDF/DOCX 渲染和预览界面分层；内容编辑、模板和导出使用同一数据源；浏览器与服务端导出边界分开。
- 本 Skill 不依赖或复制 Reactive Resume 的实现，也不声称生成文件与其模板兼容。

两项目均处于持续开发状态。后续若要做代码级集成，必须重新核对目标版本、许可证和当前接口；V1.0.0 只封装工作流参考。
