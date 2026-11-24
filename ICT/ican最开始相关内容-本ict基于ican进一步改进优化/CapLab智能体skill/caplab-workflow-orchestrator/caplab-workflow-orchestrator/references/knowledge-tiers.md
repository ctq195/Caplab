# 知识库分层、检索通道与可复现运行（v2.0.1）

> 适用范围：所有调用 `scripts/caplab_rag.py` 的初始化、检索、统计与导出动作。
> 配套：SKILL.md「版本与能力边界」「后台知识请求」、`scripts/caplab_rag.py`（v2.0.1）、`scripts/caplab_encoder.py`。

> v2.0.2 用户权限以 [VIP 标识协议](vip-access.md) 为准。以下 tier / 文件名识别只用于数据分类，不授予付费权限。普通用户检索应省略 --index-dir，携带当前用户与会话标识；付费文件只可在标识开启后读取。

## 1. 为什么分层

比赛与商业方案（v1.5.0）将知识库区分为**免费版与付费版**两层：免费版提供通用认知与职业标准库（规则引擎、官方结构化详情、基础路径模板、行动模板、证据规则），付费版在免费版之上提供行业资料与岗位库（人物案例、招聘岗位、岗位要求、访谈洞察、各去向项目详情、录取案例等）。分层原则：

- 免费版是**完整产品**（能走通资料建档→画像确认→路径收敛→证据回合→复盘全流程），不以功能残缺制造付费差异；
- 付费差异体现在**内容丰富度**，不体现在安全、纠错或基础闭环上；
- 机构定制内容与私有知识库属于后续演进方向（方案 v1.5.0），本版本不实现多用户隔离。

## 2. 两层结构与识别

| 层级 | 内容 | 检索行为 |
| --- | --- | --- |
| `free` | 通用认知与职业标准库（演示人物案例、路径模板、行动模板、证据规则、KB 卡片） | 免费基础版默认命中 |
| `paid` | 免费版之上增加行业资料与岗位库（人物案例、招聘岗位、岗位要求、访谈洞察、项目/职位/留学详情、录取案例等） | 个人成长版/班级版订阅解锁 |

- 层级识别：优先读取索引元数据 `index_meta.json` 的 `tier` 或知识卡片 `assets/knowledge-cards/<free|paid>/index.json`；其次看工作区 Excel 文件名（含"付费/paid/premium"→paid；含"免费/free/basic"→free）；识别不到按 `unknown` 处理并在输出中如实标注。
- 索引元数据 `index_meta.json` 记录 `tier` 与 `kb_version`；索引层级与当前确定的知识库版本不一致时，必须重建或重新复制预建索引后再继续。
- 免费版检索不得伪装成付费版覆盖：检索不到或仅有演示数据时如实说明，并提示"该能力属于付费版知识库"。

## 3. 检索通道与可复现运行（v2.0.1 核心变更）

v2.0.1 移除 torch / sentence-transformers / HuggingFace 下载链，改为**预建索引 + 三通道查询编码**：

| 通道 | 触发条件 | 维度要求 | 评审端体验 |
| --- | --- | --- | --- |
| `local_onnx`（默认） | 随包 int8 BGE 模型存在（`assets/models/bge-small-zh-v1.5-int8` 或 `<workspace>/.caplab/models`） | 512（与预建索引一致） | 离线、零下载、查询约几十 ms |
| `api`（可选） | `qianfan-config.json` 或环境变量配置了 key | 必须等于索引 `embedding_dimension`，否则跳过并说明 | 有网即用；千帆 `bge-large-zh` 为 1024 维，需用同一 API 重建索引后使用 |
| （无） | 上述均不可用 | — | 降级 TF-IDF，输出 `sparse_fallback` |

- 输出固定包含 `retrieval_mode`（`hybrid_dense_sparse` / `api_embedding` / `sparse_fallback`）与 `embedding_channel`（`local_onnx` / `api` / `none`），不得省略。
- 预建索引随 Skill 发布：`init --prebuilt <bundle>` 直接复制，**零模型下载、零编码**；维护端重建优先从随包 JSON 卡片：`build_prebuilt_index.py --cards assets/knowledge-cards/<free|paid>`（仅轻量依赖，无需 openpyxl）；从 xlsx 重建需 openpyxl（`export_kb_cards.py` 转卡片后走 `--cards`）。

## 4. 千帆 API（可选增强）

配置示例（`<workspace>/.caplab/qianfan-config.json`）：

```json
{
  "base_url": "https://qianfan.baidubce.com/v2",
  "api_key": "bce-你的密钥",
  "embedding_model": "bge-large-zh",
  "embedding_dimension": 1024,
  "chat_model": "ernie-speed-128k",
  "timeout": 30
}
```

也支持环境变量：`CAPLAB_API_BASE_URL`、`CAPLAB_API_KEY`、`CAPLAB_EMBEDDING_MODEL`、`CAPLAB_CHAT_MODEL`、`CAPLAB_EMBEDDING_DIM`。未配置时跳过 API 通道，不影响本地运行。API 调用仅发送检索所需的查询/文档文本与模型名，不发送对话、画像、家庭或经济信息。

## 5. 统一结构化入库与验证

- 知识源统一为"Excel 权威台账 → JSON 知识卡片（随包发布）→ schema 校验 → 预建索引"结构；xlsx 与 JSON 卡片收敛到同一文档结构，避免双份维护。
- 验证：
  - `tests/test_caplab_rag.py`：分层归属、sparse/dense 过滤、降级标识；
  - `scripts/package_selfcheck.py`：文档与文件齐全、版本边界标记；
  - `python scripts/caplab_rag.py stats --index-dir <index>`：输出每层文档数与来源数，确认免费/付费边界与方案 v1.5.0 口径（付费 433 张 KB 卡片 / 免费 293 张；付费 324 条来源 / 免费 214 条）一致。
