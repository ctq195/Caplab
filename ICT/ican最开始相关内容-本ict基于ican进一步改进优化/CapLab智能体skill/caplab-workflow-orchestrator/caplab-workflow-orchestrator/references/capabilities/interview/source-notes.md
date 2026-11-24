# 参考项目与取材边界

访问日期：2026-08-28。

## Snailclimb/interview-guide

- 官方仓库：https://github.com/Snailclimb/interview-guide
- 功能文档：https://snailclimb-interview-guide.mintlify.app/features/mock-interview
- 架构文档：https://snailclimb-interview-guide.mintlify.app/architecture/overview
- 借鉴：模块化的面试域；`CREATED → IN_PROGRESS → COMPLETED → EVALUATED` 会话生命周期；基于简历的个性化问题；按回答继续追问；完成后异步/统一评估；报告与恢复的概念边界。

本 Skill 将服务器、Redis、数据库与异步队列抽象为对话级会话合同，不声称拥有原项目的持久化、缓存、语音、RAG、PDF 服务或接口兼容性。没有可用持久化能力时，只在当前对话保持状态并交付可保存的摘要。

该项目采用 AGPL-3.0。V1.0.0 只记录公开架构思想并自行撰写 Skill 指令，没有复制其源代码。若后续代码级复用，必须重新核对许可证义务、目标提交和部署方式。
