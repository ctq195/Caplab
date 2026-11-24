# RAG 知识检索协议

版本：2.0.1

## 概述

CapLab 以随包 **JSON 知识卡片**（`assets/knowledge-cards/<free|paid>/`，由维护者从 `公共知识库.xlsx` 权威台账经 `export_kb_cards.py` 导出）为主知识源。v2.0.1 使用随包 int8 ONNX 的 `BAAI/bge-small-zh-v1.5` 密集向量和中文 TF-IDF/bigram 稀疏检索双路召回，通过 Reciprocal Rank Fusion 融合排序。结果必须保留 Source_ID、Claim_ID、sheet/row、证据等级和时效状态。

## 工作区路径

```text
<workspace>/.caplab/
├── deps/
├── models/
├── knowledge_index/
│   ├── embeddings.npy
│   ├── documents.json
│   ├── sparse_index.json
│   ├── sources.json
│   ├── claims.json
│   ├── tags.json
│   └── index_meta.json
└── state/
```

工作区外不安装依赖、模型或索引。安装依赖和下载模型前必须获得用户确认。

## 首次初始化（评审端，零模型下载）

```bash
python scripts/bootstrap.py check --workspace <workspace>
python scripts/bootstrap.py setup --workspace <workspace> --confirm
python scripts/caplab_rag.py init --prebuilt <skill>/assets/prebuilt_index/<free|paid> --index-dir <workspace>/.caplab/knowledge_index --workspace <workspace>
```

维护者重建（从 JSON 卡片，无需 openpyxl）：`build_prebuilt_index.py --cards <skill>/assets/knowledge-cards/<free|paid>`。

`index_meta.json` 记录脚本版本、模型名、向量维度、文档数、源台账 SHA-256、创建时间和工作表范围。源内容改变后必须重建索引。

## 检索

```bash
python scripts/caplab_rag.py search --workspace <workspace> --user-id <user-id> --session-id <session-id> --query "计算机考研初试科目" --top-k 5
```

可选用 `--sheet`、`--tag` 进行元数据过滤。路径收敛阶段优先根据已确认的专业、地域、候选路径、周期和证据缺口构造具体查询，不使用"职业路径"等泛化词作为唯一查询。

顶层输出必须包含 `retrieval_mode`、`degraded`、`degradation_reason` 和索引元信息。每条结果必须包含 `dense_score`、`sparse_score`、`final_score` 与溯源字段。

## 时效和外部核验

1. `HISTORICAL_VERIFIED` 只是已核验历史事实，不等于当前仍有效。
2. `HISTORICAL_SECONDARY_CORROBORATED` 是二手交叉证据，不能支撑最终报名或就业决策。
3. 当前招生、考试、政策、岗位、费用和截止日期必须回到政府、学校、考试机构或企业官方页面核验，并记录核验日期。
4. 官方页面不可访问时标记"待核验"，不用历史值补齐。
5. 引用人物案例时必须展示"不可复制条件"。

## 降级

- `embeddings.npy` 或 int8 ONNX 模型不可用时，自动进入 `sparse_fallback`，明示说明原因。
- 卡片源缺失或索引未初始化时停止知识库推理，提供精确的初始化命令。
- 检索无结果时只允许用更宽查询重试一次；仍无结果则返回缺口。
- 降级结果仍必须溯源，不得伪造 dense score 或外部核验记录。

## 回答引用格式

```text
[知识库 | sheet#row | Source_ID | Claim_ID | 证据等级 | 时效状态]
[官方核验 | 页面标题 | URL | 核验日期]
```

用户权限以 [VIP 标识协议](vip-access.md) 为准；付费数据须先校验当前会话标识。

## V2.1.1 默认质量过滤

检索前统一评估审核状态、时效状态、当前有效性、有效性状态、版本状态及关联来源/声明；稀疏与向量通道在截取 top-k 前使用同一候选集合。拒绝、过期、待人工审核、待当季核验和监测待发布记录不进入普通结果。明确 ISO 日期到期时排除；招聘岗位最后核验超过14天也排除。
历史材料只提供参考，不证明当前申请资格。缺字段、缺关联来源或无法解析的日期按未知处理，不当成已验证；未明确禁止的未知材料可以作为待核验线索，但不能直接据此形成最终行动结论。quality.needs_live_verification 始终提示动态行动需官方复核。默认导出应用相同规则；原始资料保留，不因过滤而删除。
