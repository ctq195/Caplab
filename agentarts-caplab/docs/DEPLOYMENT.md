# 部署与验证指南

> 完整逐步操作（含云资源开通、控制台配置字段、命令）见 [STEP-BY-STEP.md](STEP-BY-STEP.md)。

## 1. 本地离线验证（现在即可）

```bash
cd agentarts-caplab
cp .env.example .env
# .env 设置：CAPLAB_OFFLINE=1
python -m pytest tests/ -q       # 16 项测试应全部通过
python app.py                    # 本地 FastAPI，端口 8080
curl http://localhost:8080/ping
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message":"我想梳理毕业后方向","session_id":"local-1","_server_user_id":"u1"}'
```

> 注意：`CAPLAB_OFFLINE=1` 使用 FakeLLM 与内存仓储，**不得**作为比赛演示或"云端运行成功"的证据。

## 2. 比赛托管专项：从 ECS 到 AgentArts

> 官方依据：https://support.huaweicloud.com/bestpractice-agentarts/agentarts_06_0066.html

### 2.0 先纠正 ECS 配置（重要）

官方明确推荐 **Ubuntu 22.04 ARM64** 制作镜像，避免使用其他版本带来的兼容问题。
购买页镜像若显示 `Ubuntu 24.04 server 64bit with ARM`，请改选 **Ubuntu 22.04 ARM64**。
规格 km2.large.8（2vCPU 16GB 鲲鹏）作为构建机够用；系统盘建议 80GB。

### 2.01 ECS 初始化（买完第一件事）

```bash
# 1. 装 Docker（官方要求 18.06+）
sudo apt update && sudo apt install -y docker.io
sudo systemctl enable --now docker

# 2. 配置国内镜像加速（拉 python:3.10-slim 用，避免超时）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io", "https://mirror.ccs.tencentyun.com"]
}
EOF
sudo systemctl restart docker

# 3. 确认 Python 3.10+
python3 --version

# 4. 装 AgentArts Starter toolkit（SDK CLI，可选，用一键部署时更省事）
python3 -m pip install agentarts-sdk
```

### 2.02 把工程传到 ECS

在本地 Windows 终端（项目根目录）：

```bash
# 用 scp 上传（替换为你的 ECS 公网 IP 和密钥路径）
scp -r -i ~/.ssh/<你的密钥.pem> ./* ubuntu@<ECS公网IP>:/home/ubuntu/caplab-agentarts/
```

### 2.03 两种托管方式（二选一）

**方式 A：SDK 一键部署（新项目验证推荐）**

```bash
cd ~/caplab-agentarts
# 需先配好 agentarts.yaml 里的凭证与区域
agentarts launch
```
SDK 自动完成镜像构建、推送 SWR、创建运行时，适合快速跑通。

**方式 B：手动构建镜像 + 控制台部署（比赛推荐，可控性更强）**

```bash
cd ~/caplab-agentarts
# 在 ARM64 机器上直接 build，无需 buildx 模拟
docker build -t caplab-agentarts:1.0.0 .

# 本地先验证（模拟平台入口）
docker run --rm -p 8080:8080 --env-file .env caplab-agentarts:1.0.0
curl http://localhost:8080/ping
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message":"我想梳理毕业后方向","session_id":"local-1","_server_user_id":"u1"}'
```

然后推送 SWR 并在控制台创建运行时（见 2.4 / 2.5）。

### 2.04 比赛必须留存的证据

| 证据 | 获取位置 |
|---|---|
| 运行时名称 / ID / 版本 / 访问方式 | 控制台"托管与运行 > 智能体运行时" |
| 调用链 Trace（含 LangGraph 节点与 Tool span） | "观测与优化 > 观测 > 调用链分析" |
| 两用户会话隔离 | 会话分析页 + 两个不同 session_id 的调用 |
| 版本信息 | 运行时版本列表截图 |
| 状态恢复 | 同 session 两轮 revision 递增（探针 P4） |
| 探针输出日志 | `python scripts/probe.py` 的 stdout |

> 只调用一个华为模型端点、或只把平台画在架构图里，**不算**完成赛题要求；必须有上面这些真实运行证据。

### 2.1 准备数据库

在 RDS PostgreSQL 执行 `sql/001_init.sql`，确认 `vector` 扩展可用。

### 2.2 配置环境变量

在 AgentArts 运行时控制台注入（不写入镜像）：

```
DATABASE_URL=postgresql://user:pass@host:5432/caplab
MAAS_BASE_URL=<MaaS OpenAI 兼容端点>
MAAS_MODEL=<模型名>
MAAS_API_KEY=<MaaS API Key>
AGENT_RUN_PORT=8080
CAPLAB_OFFLINE=0
CAPLAB_DEMO_VIP_SWITCH=0
```

### 2.3 构建 ARM64 镜像并推送 SWR

```bash
docker buildx build --platform linux/arm64 -t caplab-agentarts:1.0.0 .
docker tag caplab-agentarts:1.0.0 <swr-registry>/<org>/caplab-agentarts:1.0.0
docker push <swr-registry>/<org>/caplab-agentarts:1.0.0
```

### 2.4 创建运行时

- 控制台：托管与运行 > 智能体运行时 > 创建，选择 SWR 镜像，区域贵阳一。
- 配置存储：RDS 连接（通过 `DATABASE_URL`），按需挂载会话存储 / OBS。
- 开启可观测：编辑页打开"日志记录 / 调用链 / 指标"。
- 创建访问方式（如 Latest），发布版本 1.0.0。

### 2.5 部署探针（赛题合规关键）

```bash
python scripts/probe.py \
  --base-url https://<runtime-endpoint> \
  --api-key <api-key> \
  --session-id probe-session-001
```

四项探针：

| 探针 | 验证内容 | 判据 |
|---|---|---|
| P1 | 一次真实请求 | `status=success`，返回 revision |
| P2 | 一次工具调用 | Trace 中出现 Tool span `caplab.tool.knowledge_retrieve`（人工确认） |
| P3 | 一条追踪 | 平台"调用链分析"可见 session_id 对应 Trace |
| P4 | 一次状态恢复 | 同 session 第二轮 revision 递增 |

### 2.6 平台侧证据留存

- 运行时名称 / ID / 版本 / 访问方式截图
- 调用链分析页 Trace 详情截图（含 LangGraph 节点与 Tool span）
- 会话分析页两用户隔离截图
- 部署探针输出日志

## 3. 前端接入（下一步）

现有 `ican/CapLabAgent/projects` 的 `/api/chat` 直调模型，需改为转发 AgentArts ExecuteRuntime：

- 请求：`POST /runtimes/{runtime_name}/invocations`
- 必填 Header：`X-Hw-Agentarts-Session-Id`
- 鉴权：服务端携带 API Key，密钥不落到浏览器
- 角色限制：只接受 user/assistant，system 由服务端控制
- `/api/upload` 当前返回固定模拟值：先禁用入口并明示，避免虚构解析结果

## 4. 验收清单

- [ ] 浏览器对话真实经过 AgentArts，有运行记录
- [ ] 两用户会话隔离
- [ ] 未授权不能调用付费模型 / 读付费知识
- [ ] 一轮只问一个关键问题
- [ ] 未确认信息不变成事实；沉默不算确认
- [ ] 上传不返回虚构解析（先禁用入口）
- [ ] 行动任务五要素齐全（目的/产物/验收/时间/失败调整）
- [ ] 结果能更新判断并保留未知项
- [ ] 多轮 / 停止生成 / 错误提示 / 刷新行为符合实际支持范围
- [ ] Trace / 版本 / 状态恢复探针全部通过

## 5. 待核实项

- ExecuteRuntime 请求/响应完整字段与文件上传下载 API：以平台 OpenAPI + 一次真实调用为准。
- `/ws` 流式与网页 SSE 的兼容性：需实测后决定前端流式方案。
- user_id 能否从平台鉴权上下文可靠取得：当前实现接受 SDK context.user_id 或服务端注入字段，拒绝客户端自报。
