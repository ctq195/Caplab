# CapLab × 华为云 AgentArts

面向华为 ICT 大赛赛道二的高代码智能体适配工程。基于 `ican` 中已有的
`caplab-workflow-orchestrator v2.1.1` Skill 完整协议，迁移为 LangGraph 五阶段
业务图，通过 AgentArts Runtime SDK 托管运行，落地真实 Trace、版本与状态恢复。

## 快速开始

```bash
# 1. 离线验证（无需云资源）
python -m pip install -r requirements.txt
cp .env.example .env      # 设置 CAPLAB_OFFLINE=1
python -m pytest tests/ -q    # 16 passed

# 2. 本地入口
python app.py
curl http://localhost:8080/ping
```

## 目录结构

```
app.py                       AgentArts Runtime SDK 入口 / 本地 FastAPI 入口
agentarts.yaml               运行时配置模板（区域、镜像、存储、观测）
Dockerfile                   ARM64 镜像
sql/001_init.sql             状态/审计/知识库表结构
src/caplab/
  graph/                     LangGraph 五阶段图与确认门
  protocol/                  补丁协议、ID 体系、Schema 校验（代码化确定性）
  persistence/               内存仓储（测试）/ PostgreSQL 仓储（云端）
  prompts/                   从 Skill 逐字迁移的提示词/契约/方法
  knowledge/                 分层知识卡检索
  session/                   会话隔离与权限判定
  observability/             OTel Baggage / Span
  llm.py                     MaaS 模型调用 / 离线 FakeLLM
scripts/probe.py             部署探针（请求/工具/Trace/状态恢复）
docs/                        基线、云资源、部署、验收文档
```

## 设计原则

1. **五阶段 = 图中的节点/子图**，不是五个自由对话 Agent（阶段数 ≠ Agent 数）。
2. **确定性代码化**：补丁校验、权限、确认语义、回退由代码执行，不交给 LLM 声明。
3. **云端无本地状态**：所有业务状态落 RDS PostgreSQL，禁止 SQLite/本地文件。
4. **会话强隔离**：session_id 来自平台 Header/Context，user_id 由服务端鉴权解析。
5. **唯一提示词基线**：只使用 v2.1.1 Skill 完整协议，网页简化版不参与实现。

## 文档

- `docs/PROMPT-BASELINE.md` — 提示词/协议基线与迁移映射
- `docs/CLOUD-RESOURCES.md` — 云资源清单与踩坑
- `docs/DEPLOYMENT.md` — 部署步骤、探针与验收清单

## 状态

- 已完成：阶段 0–4（基线固化、协议持久化、五阶段图、检索权限与 Runtime 入口）
- 待云资源开通：阶段 5–6（云部署探针、前端接入与平台验收）
