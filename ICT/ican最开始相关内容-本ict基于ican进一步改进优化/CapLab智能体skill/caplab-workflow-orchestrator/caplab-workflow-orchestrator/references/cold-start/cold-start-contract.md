# 冷启动输出契约

```json
{
  "cold_start_handoff": {
    "grade_stage": "year_1",
    "decision_question": "未来两周先验证哪些计算机方向？",
    "evidence_records": [
      {"record_id": "INT-000001", "event": "用户描述的具体事件", "interpretation": "仅限用户确认的含义"}
    ],
    "direction_hypotheses": [
      {
        "hypothesis_id": "HYP-000001",
        "direction": "软件工程",
        "evidence_for": ["INT-000001"],
        "counter_evidence": [],
        "unknowns": ["尚未验证是否愿意持续调试"],
        "knowledge_card_ids": []
      }
    ],
    "knowledge_status": "no_usable_match",
    "knowledge_snapshot_ids": ["KSNP-000001"],
    "validation_experiments": [
      {"duration_days": 7, "task": "...", "observable_evidence": "..."},
      {"duration_days": 14, "task": "...", "observable_evidence": "..."}
    ],
    "ready_for_intake_confirmation": true
  }
}
```

`knowledge_status` 只使用 `sufficient`、`partial`、`no_usable_match`、`knowledge_unavailable`。知识库 ID 是临时检索引用，不得冒充 `caplab_state` 的全局来源 ID。

Skill 1 接收用户确认后，为候选方向分配 `PTH-*`，把必要外部来源转换为状态内 `SRC-*`，并提出 intake 补丁。冷启动 Skill 不提出状态补丁。
