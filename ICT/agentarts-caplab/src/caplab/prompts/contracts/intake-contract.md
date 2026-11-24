# Skill 1 统一状态契约

仅在需要生成、保存或校验建档补丁时读取。Skill 1 不直接写 `caplab_state.json`，只输出交给编排器校验的补丁。

## 目标区

唯一可写路径是 `/sections/intake`。数据结构：

```json
{
  "decision_question": null,
  "candidate_paths": [],
  "candidate_generation_needed": true,
  "deadline": null,
  "major": {
    "name": null,
    "code": null,
    "status": "unconfirmed",
    "source_ids": []
  },
  "personal_facts": {
    "gender": {
      "value": null,
      "status": "unconfirmed",
      "source_ids": []
    },
    "age": {
      "value": null,
      "status": "unconfirmed",
      "source_ids": [],
      "as_of": null
    },
    "education_level": {
      "value": null,
      "status": "unconfirmed",
      "source_ids": []
    },
    "institution_name": {
      "value": null,
      "status": "unconfirmed",
      "source_ids": []
    },
    "institution_tier": {
      "value": null,
      "status": "unconfirmed",
      "source_ids": [],
      "classification_basis": null
    },
    "enrollment_year": {
      "value": null,
      "status": "unconfirmed",
      "source_ids": []
    },
    "graduation_year": {
      "value": null,
      "status": "unconfirmed",
      "source_ids": [],
      "kind": "expected"
    },
    "key_timepoints": {
      "status": "unconfirmed",
      "source_ids": [],
      "events": []
    }
  },
  "sources": [],
  "records": [],
  "constraints": [],
  "conflicts": [],
  "unknowns": [],
  "intake_ready": false,
  "confirmation_status": "unconfirmed",
  "problem_designability": null,
  "desired_output": null
}
```

## 补丁信封

```json
{
  "patch_id": "PAT-000001",
  "actor_skill": "caplab-profile-intake",
  "skill_version": "2.1.1",
  "base_revision": 0,
  "operation": "propose_patch",
  "changes": [{"op": "set", "path": "/sections/intake", "value": {}}],
  "referenced_ids": [],
  "requires_confirmation": true,
  "summary": "本补丁建立或更新资料建档。"
}
```

## 约束

- `confirmation_status` 只使用 `unconfirmed`、`confirmed`、`revision_requested`、`partial`。
- 来源、记录分别使用全局 `SRC-000001`、`INT-000001`，不得继续使用局部 `S001`、`I001`。
- `conflicts[]` 至少引用两个已存在的记录 ID；无法关联时放入 `unknowns`。
- `intake_ready: true` 只在用户明确确认摘要后提出；实际确认事件由编排器记录。
- `major` 是用户事实或官方目录规范化结果，不从兴趣、人物案例或模型印象推断。
- 不输出能力强弱、人格、职业适合度、路径分数或职业推荐。

个人事实与日期必须符合 [personal-facts.md](../shared/personal-facts.md)。所有必需字段、专业、关键节点和建档摘要确认且无未解决冲突，才能设置 `intake_ready=true`；拒答或未知保持草稿。
