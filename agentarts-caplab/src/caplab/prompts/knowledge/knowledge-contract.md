# 后台知识接口与命令

## 最小请求

```json
{
  "request_id": "KREQ-000001",
  "major": {"name": "计算机科学与技术", "code": "080901", "status": "confirmed"},
  "candidate_path_ids": ["PTH-000001"],
  "region": "中国大陆",
  "time_window": "2026-2027",
  "retrieval_modes": ["background_similar", "goal_oriented"],
  "evidence_gaps": [{"gap_id": "GAP-000001", "claim_to_test": "..."}]
}
```

禁止出现 `raw_conversation`、`full_profile`、`health`、`family`、`finance`、`contact`、`phone`、`email`、`address`、`identity_card`、`bank_card` 等个人字段。

## 命令

```bash
python3 scripts/caplab_knowledge.py init --root <workspace>
python3 scripts/caplab_knowledge.py validate-request --request <request.json>
python3 scripts/caplab_knowledge.py validate --root <workspace>
python3 scripts/caplab_knowledge.py add --root <workspace> --file <record.json>
python3 scripts/caplab_knowledge.py freshness --root <workspace> [--mark]
python3 scripts/caplab_knowledge.py retrieve --root <workspace> --request <request.json> --mode background_similar
python3 scripts/caplab_knowledge.py retrieve --root <workspace> --request <request.json> --mode goal_oriented
python3 scripts/caplab_knowledge.py queue --root <workspace>
python3 scripts/caplab_knowledge.py review --root <workspace> --id <ID> --decision approve --text "审核说明"
```

`add` 从 `card_type` 自动选择 people、occupations 或 pathways；来源记录以 `source_id` 识别。重复项不会覆盖原文件，而会生成审核队列条目。

## 检索快照

检索结果写入 `knowledge/snapshots/KSNP-*.json`，包含请求摘要、生成时间、模式、结果 ID、来源 ID 和时效状态。Skill 3 将需要使用的来源最小元数据复制为状态内 `SRC-*`，不得把知识库内部 ID 当成 `caplab_state` 的全局引用。
