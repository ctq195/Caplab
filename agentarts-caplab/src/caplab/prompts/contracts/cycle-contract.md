# Skill 4 统一状态契约

Skill 4 只输出 `/sections/cycle_plan` 补丁，不得把计划写成已执行证据。

```json
{
  "path_decision_reference": null,
  "priority_gap_id": null,
  "cycles": [],
  "selected_cycle_ids": [],
  "plan_status": "draft",
  "execution_records": [],
  "review_ready": false
}
```

补丁使用 `actor_skill: caplab-path-evidence-cycle`，回合和观察记录分别使用 `CYC-*`、`OBS-*`。每个回合包含 `affected_path_ids`、`claim_to_test`、`required_event`、`immediate_next_step`、`actions`、`artifact`、`objective_feedback`、`subjective_signals`、`preconditions`、`cost_ceiling`、`completion_criteria`、`wait_or_absorb_condition`、`downgrade`、`stop_condition`、`review_trigger` 和 `selected`。

约束：

- `plan_status` 只使用 `draft`、`selected`、`in_progress`、`waiting`、`stopped`。
- `execution_records` 只记录用户提供的真实事件、产物、反馈或未执行原因。
- 只有出现真实复盘输入时才设置 `review_ready: true`。
- 默认设计 2–3 个互补回合；资源只允许一个时可标记部分方案。
- 实际联系、报名、购买、发送或发布仍需在执行时另行授权。

带日期的规划统一写入本区的 `decision_timeline` 数组（复盘写在每条 review 内），事件契约见 [personal-facts.md](../shared/personal-facts.md)。个人事实只引用 intake；发现毕业年份等矛盾时回交建档，不在本区另造档案。正式阶段需通过个人事实门槛；上游被标记 stale 时先返回最早受影响阶段。
