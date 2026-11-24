# 提示词与协议基线说明

## 唯一基线

本工程的五阶段提示词、契约与 Schema 来自 iCAN 的 `caplab-workflow-orchestrator-v2.1.1-runtime-guards -toCoze` 版本。后端运行时从本工程加载这些文件。仓库收录的 [iCAN 历史资料](../../ican最开始相关内容-本ict基于ican进一步改进优化/) 包含 v2.2.0 版工作流 Skill，供对照。

| 源路径 | 目标路径 | 说明 |
|---|---|---|
| `SKILL.md` | `src/caplab/prompts/SKILL-source.md` | 总控 12 步流程 / 路由表 / 输出块 |
| `references/workflow.md` | `src/caplab/prompts/workflow.md` | 五阶段准入 |
| `references/state-protocol.md` | `src/caplab/prompts/state-protocol.md` | 补丁权限 / 确认语义 / 回退 |
| `references/runtime-guards.md` | `src/caplab/prompts/runtime-guards.md` | 输出门 / 事实来源 / 措辞守卫 |
| `references/stages/*.md` | `src/caplab/prompts/stages/` | 五阶段 + 冷启动提示词（6 份） |
| `references/contracts/*.md` | `src/caplab/prompts/contracts/` | 五阶段契约（5 份） |
| `references/methods/*.md` | `src/caplab/prompts/methods/` | 9 份对话方法 |
| `references/shared/*.md` | `src/caplab/prompts/shared/` | 个人事实 / 心理机制 |
| `references/knowledge/*.md` | `src/caplab/prompts/knowledge/` | 知识请求契约 |
| `references/schemas/*.json` | `src/caplab/protocol/schemas/` | 状态 / 补丁 / 交付 Schema（4 份） |
| `assets/knowledge-cards/{free,paid}` | `assets/knowledge-cards/{free,paid}` | 免费 / 付费知识卡（物理隔离） |
| `assets/templates/*.json` | `assets/templates/` | 状态初始化模板 |

## 版本

- Skill 版本：**2.1.1**（补丁 `skill_version` 必须为 2.1.1）
- 状态 Schema：**1.1.0**

## 明确排除的口径

以下三套提示词**不作为本工程基线**，仅作背景说明：

1. `ican/CapLabAgent/projects/src/lib/system-prompt.ts`：网页端简化版，缺少补丁/确认/回退协议。
2. `ican/05_工程与交付/AgentArts验证智能体创建指南.md` 第四章"可粘贴版"：低代码路线专用。
3. `ICANdumate赛道终稿提交/旧版对话与新版Skill对照报告_20260928.md`：描述旧版失败用例，不是规范。

## 协议代码化清单

以下机制从 Skill 的"提示词 + 本地 CLI"迁移为平台侧代码，不交给模型自行声明：

| Skill 机制 | 实现位置 |
|---|---|
| `caplab_state.py propose/confirm/apply/rollback` | `src/caplab/protocol/patch.py` |
| 权限表 / 禁止字段 / ID 体系 | `src/caplab/protocol/ids.py` |
| Schema + 业务准入校验 | `src/caplab/protocol/schema_validation.py` |
| `route` 五阶段准入 | `src/caplab/protocol/patch.py::route_for` |
| 本地状态文件 | `src/caplab/persistence/repository.py` + `sql/001_init.sql` |
| `caplab_guards.py` 措辞门 | `src/caplab/graph/nodes/orchestrator.py::_guard_reply` |
| VIP 口令 | `src/caplab/session/access.py`（服务端判定，口令仅演示开关） |
| `caplab_rag.py` | `src/caplab/knowledge/retriever.py`（保留 tier/quality/Source_ID 契约） |

## 校验基线一致性

```bash
# 提示词与 Schema 应与源文件逐字一致（仅路径不同）
diff <(cat "<Skill源>/references/stages/profile-intake.md") \
     src/caplab/prompts/stages/profile-intake.md
```
