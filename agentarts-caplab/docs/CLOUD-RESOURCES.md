# 云资源与前置条件清单

> 用户当前状态：云资源尚未构建。本清单区分"本地可立即做"与"开通后必须做"。

## A. 本地立即可做（无需云资源）

- [x] 从 Skill 复制提示词 / 契约 / Schema / 知识卡（已完成）
- [x] 实现补丁协议、权限表、路由、回退（已完成，16 项离线测试通过）
- [x] 实现 LangGraph 五阶段图与确认门（已完成）
- [x] 实现本地内存仓储与本地 FastAPI 入口（已完成，仅用于离线验证）
- [x] 准备 ARM64 Dockerfile / .dockerignore（已完成）
- [ ] 用本地 PostgreSQL 容器验证 SQL 与仓储层（可选，需 Docker）

## B. 云侧必须准备

### B1. 账号与区域

| 项 | 要求 |
|---|---|
| 华为云账号 | 比赛账号，完成实名认证，确认余额或赠送额度 |
| 区域 | **cn-southwest-2（西南-贵阳一）** —— AgentArts 高代码运行时当前唯一支持区域 |
| 服务开通 | AgentArts、SWR、MaaS、RDS for PostgreSQL、VPC + 子网 + 安全组、IAM、LTS / APM / AOM、OBS（如需上传） |

### B2. 模型

- 在 MaaS 控制台（区域贵阳一）创建 API Key，仅显示一次，立即保存到环境变量 `MAAS_API_KEY`。
- 在 AgentArts "资产广场 > 模型 > 模型鉴权管理"配置鉴权。
- 选择带"思考 + 工具"标签的模型；确认免费 Token 额度（文档提及 200 万 Tokens，需在实际账号核实）。
- 注意：只调用一个华为模型端点**不能**证明赛题完成，必须有平台真实运行与 Trace。

### B3. 数据库与存储

- RDS PostgreSQL，支持 `vector` 扩展（pgvector），与运行时同 VPC。
- 执行 `sql/001_init.sql` 建表。
- 环境变量 `DATABASE_URL` 由平台注入，**不得写入镜像或配置文件**。
- 可选：会话存储（多轮上下文，1 个）、OBS（用户上传/产物，最多 5 个桶）。
- 硬约束：禁止 SQLite / 本地文件状态，沙箱销毁后本地磁盘数据全部丢失。

### B4. 网络与权限

- VPC 私网打通：运行时 ↔ RDS ↔ SWR；安全组最小放行。
- IAM 用户或委托权限：SWR 推送/拉取镜像、RDS 连接、OBS 读写（如启用）、LTS 日志上报。
- 访问方式：运行时最多 10 个；建议至少 Latest + Stable 两个版本。

### B5. 配额

| 项 | 最低 | 说明 |
|---|---|---|
| 智能体运行时 | 1 | 单账号最多 1000 个 |
| 运行时版本 | 2 | 单运行时最多 1000 个版本，支持历史回溯 |
| 访问方式 | 1 | 用于对外调用 |
| Token 额度 | 按实测 | 比赛赠送额度需在账号确认 |
| RDS 规格 | 最小可用 | 按并发与数据量调整 |

### B6. 本地工具

- Python ≥ 3.10（推荐 3.10，与 Dockerfile 一致）
- Docker ≥ 18.06；X86 主机需 `docker buildx build --platform linux/arm64`
- Docker 27+ 需关闭 OCI 支持（SWR 基础版不支持 OCI 镜像格式）
- `agentarts` CLI（用于 `agentarts dev` 本地运行、`agentarts launch` 一键部署、`agentarts invoke` 调用）

## C. 常见踩坑

1. **X86 镜像直接失败**：必须用 ARM64 基础镜像构建。
2. **本地状态丢失**：任何写本地磁盘的状态（SQLite、JSON 文件）在沙箱释放后消失，必须落 RDS。
3. **区域错配**：MaaS API Key 与 AgentArts 必须同为贵阳一区域，否则鉴权失败。
4. **口令不是鉴权**：`ICANDumate_VIP:enabled` 仅演示开关，生产环境保持 `CAPLAB_DEMO_VIP_SWITCH=0`。
5. **Trace 需开启开关**：运行时编辑页开启"日志记录/调用链/指标"，否则观测页无数据。

## D. 官方参考

- 运行时概述：https://support.huaweicloud.com/highcode-agentarts/agentarts_10_029.html
- Runtime SDK：https://support.huaweicloud.com/highcode-agentarts/agentarts_10_041.html
- 部署第一个 Agent：https://support.huaweicloud.com/highcode-agentarts/agentarts_10_183.html
- ExecuteRuntime API：https://support.huaweicloud.com/api-agentarts/InvokeRuntime1.html
- 存储配置：https://support.huaweicloud.com/highcode-agentarts/agentarts_10_124.html
- LangChain/LangGraph 观测：https://support.huaweicloud.com/ops-agentarts/agentarts_14_0159.html
- 上报观测数据：https://support.huaweicloud.com/ops-agentarts/agentarts_14_0005.html
