# CapLab 状态运行协议

## 文件与命令

状态文件固定为用户授权工作区下的 `.caplab/state/caplab_state.json`。命令中 `<state-root>` 表示 `<workspace>/.caplab/state`。运行时脚本：

```bash
python3 scripts/caplab_state.py init --root <state-root>
python3 scripts/caplab_state.py validate --root <state-root>
python3 scripts/caplab_state.py route --root <state-root>
python3 scripts/caplab_state.py propose --root <state-root> --patch <patch.json>
python3 scripts/caplab_state.py confirm --root <state-root> --patch-id PAT-000001 --decision confirm --text "用户的明确确认原话"
python3 scripts/caplab_state.py apply --root <state-root> --patch-id PAT-000001
python3 scripts/caplab_state.py rollback --root <state-root> --revision 2 --text "用户明确同意回到 revision 2"
```

`migrate` 接受 `--intake`、`--profile`、`--path-decision`、`--cycle-plan`、`--review`，把 v0.4.0 文件包装进统一状态。迁移保留原始资料，但个人事实降为待确认、下游标记失效，不能继承旧 ready 绕过新门槛。

## 补丁权限

| actor_skill | 唯一可写区 |
|---|---|
| caplab-profile-intake | `/sections/intake` |
| caplab-profile-confirmation | `/sections/profile` |
| caplab-path-convergence | `/sections/path_decision` |
| caplab-path-evidence-cycle | `/sections/cycle_plan` |
| caplab-evidence-review | `/sections/reviews` |
| caplab-workflow-orchestrator | `/active_stage`、`/workflow_status`、`/invalidations` |

运行时拒绝越权路径、旧 `base_revision`、重复身份 ID、未知引用、禁止字段和未经确认的应用。

## 确认语义

- `confirm`：原补丁可应用。
- `partial`：不应用原补丁；生成只含已确认范围的新补丁。
- `revise`：不应用原补丁；根据用户修正生成新补丁。
- `reject`：不改变 revision；保留确认审计文件。

确认文本保存最小必要原话。不要把沉默、继续聊天或系统推断写成确认。

贯穿式心理与自我理解使用 `/sections/profile` 中既有事实、感受、偏好、用户解释、AI 假设和冲突记录，不建立独立量表区，不保存题目、分数或人格标签。只有用户确认的最小摘要可参与路径判断；拒绝、跳过或中止不影响正常路由。心理、健康、危机和家庭原话不得进入后台知识请求。

## 回退与恢复

每次成功写入保存 `history/revision-NNNNNN.json`。早期区变化后，运行时将依赖区标为 `stale`，但不删除其内容。`rollback` 恢复目标快照的数据，同时保留当前 ID 注册表和确认历史，生成新的 revision 和 `rollback_of`。

遇到状态损坏：

1. 不覆盖损坏文件；
2. 报告校验错误；
3. 找到最高的可通过校验历史快照；
4. 展示恢复影响并取得确认；
5. 用 `rollback` 恢复，随后再次校验。

## V2.2.0 版本兼容策略

发布与新补丁版本为 2.2.0；状态 schema 仍为 1.1.0。已有合法状态和历史不改号、不覆盖。旧版待处理补丁一律拒绝，提示基于当前 revision 重建为新补丁 ID、重新校验、重新展示并确认；原有确认不自动授权新补丁。已经应用的旧补丁留在历史中，不重放。schema 1.0.0 状态仍使用 upgrade-state 升级，并保留原快照。

propose 会校验投影后的完整状态，apply 再次校验。详细结构见 schemas/caplab-state.schema.json；个人事实、时间线跨字段约束由 caplab_profile.py 校验。两者互补，JSON Schema 单独通过不等于满足业务准入。

## 程序化输出门

遵循 [每轮与交付运行合同](runtime-guards.md)。任务/承诺在独立账本校验，用户暂停时 deferred；证据和交付由脚本重新检查，不由模型的布尔标记授权。
