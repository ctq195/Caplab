# CapLab

CapLab 是面向大学生的生涯路径探索项目，通过现实行动帮助学生验证职业选择。

本赛题延续 iCAN 原型。完整目录树见[仓库首页](../README.md#目录结构)。

## 开发入口

- [网页端](CaplabWeb-existing/projects/README.md) 使用 Next.js 和 pnpm。在 `CaplabWeb-existing/projects` 中运行 `pnpm install --frozen-lockfile` 和 `pnpm dev`。需要对话等外部服务时，按 `.env.example` 在本机配置 `.env.local`。
- [AgentArts 后端](agentarts-caplab/README.md) 使用 Python 和 LangGraph。安装依赖、离线测试和部署步骤见后端说明。环境变量模板位于 `agentarts-caplab/.env.example`。

## 团队协作

队友接受 GitHub 仓库邀请后，可以运行 `git clone https://github.com/ctq195/Caplab.git`。
开发前从最新的 `main` 创建自己的分支。推送分支后，在 GitHub 上发起 Pull Request，由队友审阅后合入 `main`。

API 密钥和数据库连接信息保存在本机环境配置中。共享配置示例时使用占位值。
