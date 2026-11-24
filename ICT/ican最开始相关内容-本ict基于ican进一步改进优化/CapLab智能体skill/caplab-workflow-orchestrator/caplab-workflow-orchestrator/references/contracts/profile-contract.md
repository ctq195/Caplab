# Skill 2 统一状态契约

Skill 2 只输出 `/sections/profile` 补丁，不直接写状态，也不得改写 intake 中的用户事实。

```json
{
  "intake_reference": null,
  "decision_question": null,
  "candidate_paths": [],
  "task_preferences": [],
  "capability_evidence": [],
  "interests_and_energy": [],
  "value_tradeoffs": [],
  "environment_needs": [],
  "work_life_compass": null,
  "energy_engagement": null,
  "anchor_assumptions": [],
  "dialogic_self_understanding": {
    "method": "event_grounded_reflective_dialogue",
    "clinical_use": false,
    "surface_question": "",
    "decision_conflict": "",
    "highest_value_gap": "",
    "user_confirmed_summary": "",
    "stop_reason": null
  },
  "constraints": [],
  "records": [],
  "hypotheses": [],
  "conflicts": [],
  "counterexamples": [],
  "unknowns": [],
  "confirmation_status": "unconfirmed",
  "profile_ready": false
}
```

补丁必须使用 `actor_skill: caplab-profile-confirmation`、`skill_version: 2.2.0`、当前 `base_revision` 和 `operation: propose_patch`。写入路径只允许 `/sections/profile`。画像记录使用 `PRO-*`，假设使用 `HYP-*`，并在 `referenced_ids` 列出所依赖的 `INT-*`、`PRO-*` 等既有引用。

约束：

- `confirmation_status` 只使用 `unconfirmed`、`partially_confirmed`、`confirmed`、`revision_requested`。
- 每条假设至少关联两条相互独立记录；信心只使用 `low`、`medium`。
- `profile_ready: true` 只表示足以进入路径比较，不表示职业已经确定。
- 用户确认由编排器形成 `CFM-*` 事件；沉默不是确认。
- 不输出路径分数、成功概率或固定人格标签。
- 心理与自我理解不保存题目、分数或人格标签，只通过既有 `records`、`hypotheses`、`conflicts` 和上述最小对话进度字段记录。只有用户确认的摘要可参与后续路径判断；原始心理、健康或家庭叙述不得发送给知识检索。

带日期的规划统一写入本区的 `decision_timeline` 数组（复盘写在每条 review 内），事件契约见 [personal-facts.md](../shared/personal-facts.md)。个人事实只引用 intake；发现毕业年份等矛盾时回交建档，不在本区另造档案。正式阶段需通过个人事实门槛；上游被标记 stale 时先返回最早受影响阶段。
