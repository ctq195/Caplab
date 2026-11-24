# Skill 5 统一状态契约

Skill 5 只向 `/sections/reviews` 追加复盘。它可以提出 `route_request` 和 `invalidation_request`，但不能直接覆盖 intake、profile、path 或 cycle；由编排器另行生成路由补丁。

```json
{
  "review_id": "REV-000001",
  "cycle_reference": null,
  "cycle_status": null,
  "observations": [],
  "cause_factors": [],
  "evidence_updates": [],
  "before_after": [],
  "updated_readiness": null,
  "updated_stability": null,
  "remaining_gaps": [],
  "decision": null,
  "immediate_next_step": null,
  "route_request": null,
  "invalidation_request": []
}
```

补丁使用 `actor_skill: caplab-evidence-review` 和 `append` 到 `/sections/reviews`。观察记录使用 `OBS-*`，并在 `referenced_ids` 列出回合、路径和来源引用。

约束：

- `cycle_status` 只使用 `completed`、`partially_completed`、`not_executed`、`waiting`、`stopped`。
- 原因只使用 `access_or_precondition`、`cycle_design`、`current_capability_gap`、`task_preference`、`environment_mismatch`、`constraint_change`、`insufficient_evidence`。
- 证据影响只使用 `supports`、`weakens`、`complicates`、`no_change`；可信度只使用 `low`、`medium`、`high`。
- 决定只使用 `continue`、`adjust`、`wait`、`pause`、`close`。
- 路由请求只使用五个业务 Skill 名称或 `null`，且必须说明哪条新证据触及哪一层。

带日期的规划统一写入本区的 `decision_timeline` 数组（复盘写在每条 review 内），事件契约见 [personal-facts.md](../shared/personal-facts.md)。个人事实只引用 intake；发现毕业年份等矛盾时回交建档，不在本区另造档案。正式阶段需通过个人事实门槛；上游被标记 stale 时先返回最早受影响阶段。
