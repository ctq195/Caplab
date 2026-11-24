# 必须使用 ARM64 基础镜像：X86 镜像在 AgentArts 运行时会直接失败。
# 构建：docker buildx build --platform linux/arm64 -t caplab-agentarts:latest .
FROM --platform=linux/arm64 python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AGENT_RUN_PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# SDK 通过 AgentArtsRuntimeApp 处理 /invocations 与 /ping 协议
ENTRYPOINT ["python", "app.py"]
