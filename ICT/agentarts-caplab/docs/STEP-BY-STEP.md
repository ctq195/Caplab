# CapLab 上 AgentArts：一步一步操作手册

> 适用：华为 ICT 大赛赛道二，区域固定 **cn-southwest-2（西南-贵阳一）**。
> 本地工程位于仓库内的 `ICT/agentarts-caplab`。各段本地命令从仓库根目录执行。
> 本文所有命令在 **Git Bash** 中执行（Windows 本地）或 **Ubuntu ARM ECS** 上执行，已分别标注。

---

## 阶段 0：本地已完成，不用重做

| 项 | 状态 |
|---|---|
| 五阶段提示词 / 契约 / Schema / 知识卡固化 | 已完成 |
| 补丁协议、权限表、回退、LangGraph 图 | 已完成 |
| 离线测试 16 项 | 已通过 |
| ARM64 Dockerfile、探针脚本、部署文档 | 已完成 |
| 知识检索 Tool span 埋点 | 已补齐，16 项测试复验通过 |

本地如需复验：

```bash
cd ICT/agentarts-caplab
python -m pytest tests/ -q        # 期望 16 passed
```

> 注意：本地 `CAPLAB_OFFLINE=1` 的测试结果**不能**作为比赛证据，只是代码自检。

---

## 阶段 1：开通云资源（按此顺序，约 30–60 分钟）

### 1.1 AgentArts 服务授权

1. 登录华为云控制台，进入 **AgentArts**。
2. 左上角确认区域为 **西南-贵阳一（cn-southwest-2）**。若不是，切换。
3. 左侧 **管理中心 > 授权管理**，把依赖云服务的授权全部完成（SWR、RDS、LTS、AOM、OBS、MaaS）。
   - 不完成这步，后面创建运行时会报权限错误。

### 1.2 创建 MaaS 模型密钥

1. 进入 **模型即服务 MaaS**（同区域贵阳一）。
2. 在"模型列表"选一个带 **思考 + 工具** 标签的模型（比赛需要工具调用能力）。
3. 创建 **API Key**，**只显示一次，立刻复制保存**到本机安全位置。
4. 记下三样东西，后面填环境变量要用：
   - `MAAS_BASE_URL`：模型详情页的 OpenAI 兼容端点（复制原文，通常形如 `https://.../v1`）
   - `MAAS_MODEL`：模型名称 / model id
   - `MAAS_API_KEY`：刚复制的密钥
5. 回到 AgentArts：**资产广场 > 模型 > 模型鉴权管理**，把该 MaaS 密钥配置进去。

> 前置检查：官方说明调用 API **不支持平台赠送的免费 token**，必须配置 MaaS 付费模型 API Key 或第三方 OpenAI 协议模型，否则报 `Model call failed`。

### 1.3 创建 RDS PostgreSQL

1. 进入 **RDS for PostgreSQL**，区域贵阳一，VPC 选 `vpc-default`（后面与运行时同 VPC）。
2. 创建实例：最小规格即可，数据库版本选 15 或 16。
3. **关键**：确认该实例支持 `vector` 扩展（pgvector）。若控制台无此选项，用支持 pgvector 的版本/规格。
4. 创建数据库 `caplab` 和账号，记下：内网地址、端口（默认 5432）、库名、用户名、密码。
5. 拼出连接串（后面填 `DATABASE_URL`）：

```
postgresql://<用户>:<密码>@<内网地址>:5432/caplab
```

6. 用数据库客户端（或 ECS 上的 psql）执行工程里的建表脚本：

```bash
psql "postgresql://<用户>:<密码>@<内网地址>:5432/caplab" -f sql/001_init.sql
```

   执行后应能看到 `caplab_state`、`caplab_revision`、`caplab_confirmation`、`caplab_checkpoint` 等表。

### 1.4 创建 SWR 组织

1. 进入 **容器镜像服务 SWR**，切换到贵阳一。
2. 右上角 **创建组织**，例如 `caplab-team`（记下这个名字）。
3. 右上角 **登录指令** → 复制"通用型登录指令"，后面在 ECS 上直接粘贴执行。

### 1.5 检查 ECS 构建机

你已购买的 ARM ECS，购买页请确认/修正：

| 项 | 应为 |
|---|---|
| 区域 | 西南-贵阳一 |
| 架构 | 鲲鹏 ARM64 |
| 镜像 | **Ubuntu 22.04 ARM64**（若是 24.04，建议重建） |
| 系统盘 | 80GB |
| 登录方式 | 密钥对 |
| 安全组 | 22 端口限制来源 IP，不要 `0.0.0.0/0` |

---

## 阶段 2：在 ECS 上构建并推送 ARM64 镜像

### 2.1 初始化 ECS（SSH 登录后执行）

```bash
# Docker（官方要求 >= 18.06）
sudo apt update && sudo apt install -y docker.io
sudo systemctl enable --now docker

# 国内镜像加速（拉 python:3.10-slim 用）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io", "https://dockerproxy.net", "https://mirror.baidubce.com"]
}
EOF
sudo systemctl daemon-reload && sudo systemctl restart docker

# 若 docker version 显示 27+，关闭 OCI（SWR 基础版不支持 OCI 格式）
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io"],
  "features": {"containerd-snapshotter": false}
}
EOF
sudo systemctl restart docker

docker version --format '{{.Server.Version}}'
```

### 2.2 上传工程

在本地 Windows 的 Git Bash 执行（替换为实际 IP 和密钥路径）：

```bash
scp -r -i ~/.ssh/your-key.pem \
  "ICT/agentarts-caplab/." \
  ubuntu@<ECS公网IP>:/home/ubuntu/caplab-agentarts/
```

> 如果目标目录不存在，先在 ECS 上 `mkdir -p /home/ubuntu/caplab-agentarts`。

### 2.3 构建 + 本地验证

```bash
cd /home/ubuntu/caplab-agentarts

# ARM 机器上直接 build 即可（Dockerfile 已固定 --platform=linux/arm64）
docker build -t caplab-agentarts:1.0.0 .

# 模拟平台入口做本地验证
docker run --rm -d -p 8080:8080 --name caplab-test --env-file .env caplab-agentarts:1.0.0
curl http://localhost:8080/ping
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message":"我想梳理毕业后方向","session_id":"local-1","_server_user_id":"u1"}'
docker stop caplab-test
```

`/ping` 期望返回 `{"status":"Healthy",...}` 一类健康响应。若失败，**不要继续部署**——平台会判定启动失败并反复重启实例。

### 2.4 推送 SWR

```bash
# 粘贴在 1.4 复制的登录指令（形如下面）
sudo docker login -u cn-southwest-2@{xxx} -p {xxx} swr.cn-southwest-2.myhuaweicloud.com

sudo docker tag caplab-agentarts:1.0.0 \
  swr.cn-southwest-2.myhuaweicloud.com/<组织名>/caplab-agentarts:1.0.0

sudo docker push \
  swr.cn-southwest-2.myhuaweicloud.com/<组织名>/caplab-agentarts:1.0.0
```

推完到 SWR 控制台 **我的镜像** 确认能看到 `caplab-agentarts:1.0.0`。

---

## 阶段 3：AgentArts 控制台创建运行时（比赛核心）

### 3.1 创建

左侧导航栏 **智能体运行时** → 右上角 **托管智能体**，按表填写：

| 参数 | 填写值 |
|---|---|
| 名称 | `caplab-career-agent` |
| 描述 | `CapLab 生涯探索助手 - ICT赛道二` |
| 镜像 | 选择刚推送的 `caplab-agentarts:1.0.0` |
| 委托 | `DefaultAgentArtsRuntimeAgency`（默认即可） |
| 入网配置 | `defaultgw`（默认） |
| 入栈协议 | **HTTP** |
| 入站身份认证 | **API Key**（选这个，方便探针用 Bearer 调用） |
| 可观测配置 | **开启** |
| 生命周期配置 | 默认 |
| 出网网络配置 | 公网访问 |
| 存储配置 | 选填，通过下面环境变量注入 RDS 即可 |

### 3.2 配置环境变量（在运行时编辑页注入，不写进镜像）

```
AGENT_RUN_PORT=8080
AGENTARTS_REGION=cn-southwest-2
MAAS_BASE_URL=<1.2 复制的 OpenAI 兼容端点>
MAAS_MODEL=<1.2 的模型名>
MAAS_API_KEY=<1.2 的 API Key>
DATABASE_URL=<1.3 拼好的 PostgreSQL 连接串>
CAPLAB_OFFLINE=0
CAPLAB_DEMO_VIP_SWITCH=0
```

> 严禁把 `CAPLAB_OFFLINE=1` 带到云端——那会用 FakeLLM，不算真实运行。
> 若平台额外要求 `REGION` / `PROJECT_ID`，`REGION` 填 `cn-southwest-2`，`PROJECT_ID` 在右上角用户名 → **我的凭证 → 项目列表** 查看。

### 3.3 开启可观测

在运行时编辑页勾选 **日志记录 / 调用链 / 指标** 三项。
不勾选，观测页看不到 Trace，比赛证据拿不到。

> 说明：我们是平台托管运行时，SDK 会自动接入平台观测；**不需要**配置 `agentarts_agentops_*` 那套第三方探针环境变量（那是给外部自托管智能体用的）。

### 3.4 发布版本与访问方式

1. 创建版本 `1.0.0`（用上面推的镜像 tag，不可变版本便于历史回溯）。
2. 创建访问方式 `Latest`，绑定版本 `1.0.0`；有余力再加 `Stable`。
3. 在运行时详情页记下两样东西：
   - **访问地址**（"访问方式"页签中，形如 `https://agentarts.cn-southwest-2.myhuaweicloud.com/v1/runtimes/caplab-career-agent/invocations`）
   - **API Key**：详情页 → "权限与访问控制" → 访问URN → 进入 AgentIdentity → 基本信息 → 复制 API Key

---

## 阶段 4：部署探针，坐实比赛证据

在本地 Windows Git Bash 执行：

```bash
cd ICT/agentarts-caplab

python scripts/probe.py \
  --base-url "<3.4 复制的访问地址>" \
  --api-key "<3.4 复制的 API Key>" \
  --session-id probe-session-001
```

> 探针会自动处理地址是否已带 `/invocations`，两种写法都可以。

### 四项证据与判据

| 探针 | 验证内容 | 通过判据 | 证据留存 |
|---|---|---|---|
| P1 | 一次真实请求 | `[PASS] P1`，`status=success` 且有 revision | 保存 stdout |
| P2 | 一次工具调用 | 调用成功，Trace 中有 span `caplab.tool.knowledge_retrieve` | Trace 截图 |
| P3 | 一条追踪 | 观测页按 `probe-session-001` 能查到 Trace | Trace 详情截图 |
| P4 | 一次状态恢复 | `revision X -> Y`（Y>X） | stdout + RDS 表截图 |

### 平台侧截图清单（缺一项就可能被判未完成赛题）

1. 运行时名称 / ID / 版本 / 访问方式列表
2. **观测与优化 > 观测 > 调用链分析**： Trace 详情，能看到 `caplab.invocation`、`caplab.graph`、`caplab.tool.knowledge_retrieve`
3. 会话分析页：两个不同 session_id 的调用互不串数据
4. 版本列表（证明版本管理真实存在）
5. 探针 stdout

> 只调用一个华为模型端点、或只把平台画在架构图里，**不算**完成赛题要求。上面这些必须是真实运行产物。

---

## 阶段 5：前端接入（部署成功后做）

现有 `ican/CapLabAgent/projects` 的 `/api/chat` 直调模型，需改为转发 AgentArts：

- 请求：`POST /runtimes/{runtime_name}/invocations`（用阶段 3.4 的访问地址）
- 必填 Header：
  - `Authorization: Bearer <API Key>`（密钥只在服务端，不落浏览器）
  - `X-Hw-Agentarts-Session-Id: <前端生成的会话 ID>`
- Body：`{"message": "...", "_server_user_id": "<服务端鉴权得到的用户ID>"}`
- 角色限制：只接受 user / assistant，system 由服务端控制
- `/api/upload` 目前返回固定模拟值：**先禁用入口并明示**，避免虚构解析结果

---

## 常见失败速查

| 现象 | 原因 / 处理 |
|---|---|
| 调用返回 `Model call failed` | MaaS API Key 未配置，或用了免费 token。回 1.2 |
| 实例反复重启 | `/ping` 失败。本地先跑 2.3 验证，检查端口 8080、绑定 0.0.0.0 |
| X86 镜像调用失败 | 必须在 ARM64 机器上构建。回阶段 2 |
| 观测页无 Trace | 3.3 三个开关没开；或没走平台访问地址而是直连容器 |
| 401 / 鉴权失败 | API Key 前后多了空格、或运行时入站认证选了 IAM 却用 Bearer。回 3.1 / 3.4 |
| 多轮状态丢失 | `DATABASE_URL` 没注入，退化为内存。回 3.2；检查 RDS 安全组放行运行时 |
| 跨区看不到镜像 | SWR 与 AgentArts 必须同为贵阳一。回 1.4 |
| 付费知识越权 | `CAPLAB_DEMO_VIP_SWITCH=1` 会让口令生效，生产必须为 0 |

---

## 部署后待核实（官方 OpenAPI 与首次真实调用为准）

- ExecuteRuntime 完整请求/响应字段与文件上传下载 API
- `/ws` 流式与网页 SSE 的兼容性
- `user_id` 能否从平台鉴权上下文可靠取得（当前实现接受 SDK context 或服务端注入，拒绝客户端自报）
