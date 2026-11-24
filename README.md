# CapLab

CapLab 面向大学生的生涯路径探索。ICT 赛题 2 延续 iCAN 原型的阶段式访谈、路径比较和行动复盘，并在此基础上开发网页与 AgentArts 后端。

## 目录结构

```text
Caplab/
├── README.md
└── ICT/
    ├── README.md
    ├── CaplabWeb-existing/
    │   └── projects/                    # Next.js 网页工程
    │       ├── src/
    │       ├── public/
    │       ├── assets/
    │       ├── scripts/
    │       └── docs/
    ├── agentarts-caplab/                # Python / LangGraph 后端
    │   ├── app.py
    │   ├── Dockerfile
    │   ├── src/caplab/
    │   ├── assets/                      # 当前后端使用的知识卡与模板
    │   ├── tests/
    │   ├── scripts/
    │   ├── sql/
    │   └── docs/
    ├── ican最开始相关内容-本ict基于ican进一步改进优化/
    │   ├── CapLab应用方案.pdf
    │   ├── CapLab智能体skill/            # iCAN 工作流 Skill v2.2.0
    │   └── 原始excel知识库及知识库skill/
    ├── CapLab_产品与工程建设基线_20261124.md
    ├── CapLab_华为ICT到正大杯与大创实施规划_20261028.md
    ├── CapLab_开源扩展调研_20261109.md
    ├── CapLab_扩展功能图.{png,svg}
    ├── LangChian-Graph两者协作mermaid-diagram.png
    ├── project_20261122_113008_CaplabWeb.tar
    └── 赛题 2 作品信息收集表（模板和已填版）
```

## 开发入口

- [网页端](ICT/CaplabWeb-existing/projects/README.md) 位于 `ICT/CaplabWeb-existing/projects`。进入目录后运行 `pnpm install --frozen-lockfile` 和 `pnpm dev`。如需调用模型，依据该目录的 `.env.example` 配置本机 `.env.local`。
- [AgentArts 后端](ICT/agentarts-caplab/README.md) 位于 `ICT/agentarts-caplab`。安装依赖、离线验证和部署步骤见后端说明。
- [ICT 产品与工程建设基线](ICT/CapLab_产品与工程建设基线_20261124.md) 记录开发决策。[iCAN 资料](ICT/ican最开始相关内容-本ict基于ican进一步改进优化/) 保留原型、方案和原始知识库。

## 团队协作

接受仓库邀请后，运行 `git clone https://github.com/ctq195/Caplab.git`。开发前从最新的 `main` 创建分支，推送后发起 Pull Request，供队友审阅。

API 密钥和数据库连接信息保存在本机环境配置中。共享配置示例使用占位值。
