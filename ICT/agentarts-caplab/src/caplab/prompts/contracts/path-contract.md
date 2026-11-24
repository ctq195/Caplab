# Skill 3 统一状态契约

Skill 3 只输出 `/sections/path_decision` 补丁。外部知识由后台 `caplab-knowledge-maintainer` 返回，Skill 3 只能引用其来源和卡片快照，不能修改公共知识库。

```json
{
  "profile_reference": null,
  "decision_question": null,
  "decision_criteria": [],
  "knowledge_request": null,
  "knowledge_snapshot_ids": [],
  "paths": [],
  "evidence_gaps": [],
  "readiness": "insufficient_evidence",
  "stability": "low",
  "accepted": false,
  "update_triggers": []
}
```

补丁使用 `actor_skill: caplab-path-convergence`，仅写 `/sections/path_decision`。路径使用 `PTH-*`，证据缺口使用 `GAP-*`；`referenced_ids` 必须列出依赖的 `PRO-*`、`PTH-*`、`SRC-*` 等状态内引用。

每个路径包括 `path_id`、`name`、`status`、`requirements`、`resource_costs`、`supporting_record_ids`、`counter_record_ids`、`transferable_record_ids`、`external_evidence`、`assumptions`、`conditions`、`update_triggers`。

约束：

- 路径状态只使用 `primary`、`complementary`、`deferred`、`excluded`、`undetermined`。
- `readiness` 只使用 `insufficient_evidence`、`ready_for_low_cost_test`、`ready_to_pursue`；`stability` 只使用 `low`、`medium`、`high`。
- 当前市场主张没有来源、地域和日期时必须标为 `unverified`。
- `accepted: true` 需要用户明确接受，实际确认事件由编排器记录。
- 人物案例只能说明可能性，不能生成成功概率或因果化“成功公式”。

带日期的规划统一写入本区的 `decision_timeline` 数组（复盘写在每条 review 内），事件契约见 [personal-facts.md](../shared/personal-facts.md)。个人事实只引用 intake；发现毕业年份等矛盾时回交建档，不在本区另造档案。正式阶段需通过个人事实门槛；上游被标记 stale 时先返回最早受影响阶段。
