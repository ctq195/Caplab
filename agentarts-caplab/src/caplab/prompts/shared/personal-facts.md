# 个人事实与时间线硬约束（V1.0.0 迁移版）

建档前、修改个人信息或输出带日期的计划前读取。规范结构见包内 `assets/templates/intake-draft.json` 和 `references/schemas/caplab-state.schema.json`。

## 唯一事实源与准入

`sections.intake.personal_facts` 是性别、年龄、学历、院校、入学与毕业信息的唯一结构化事实源；专业仅用 `sections.intake.major`。禁止另造 `gender_info`、`graduate_year`、`school_level` 等别名迁就现有参数。字段值未知用 null；结构不能改名。

| 字段 | 附加要求 |
|---|---|
| gender | 用户自述，不从姓名、照片或声音猜测，不用于推荐刻板印象。 |
| age | 整数年龄及 `as_of` 完整日期；仅有年龄时不反推精确出生日期。 |
| education_level | 用户当前学历层次，不混用计划攻读学历。 |
| institution_name | 院校原名。 |
| institution_tier | 同时保存 `classification_basis`，区分办学层次、招生批次及特定名单口径。 |
| enrollment_year | 当前学历项目入学年份。 |
| graduation_year | 当前学历项目毕业年份，`kind` 为 expected 或 actual。 |
| birth_date | 可选；提供后与 age/as_of 交叉核验。 |
| key_timepoints | 本轮决策适用的关键节点；无节点可用空 events，但用户仍须确认确实无适用节点。 |

每个事实包含 `value`、`status`、`source_ids`；status 为 unconfirmed / confirmed / conflicted / declined。专业包含 name、code、status、source_ids。sources 中被确认事实引用的来源必须使用 SRC-*，标明 source_type、title、read_status；只有实际读取成功才能写 success。用户陈述是自述证据，不等于官方核验。

所有必需事实、专业和关键节点确认后才能设置 intake_ready=true；conflicts 中不能留未解决冲突。冲突解决过程作为 records 留存。必需字段拒答时标 declined、保持草稿并解释暂不能进入正式规划，不反复索取。心理探索可跳过，不影响这个事实门槛。空值或“用户应该知道”不能当成确认。

## 日期与政策

每轮读取系统日期；不得沿用旧会话的“今年”。年龄按记录日解释，不把旧年龄当今天年龄。只有年份时保留年精度，不补 1 月 1 日冒充真实日期。入学不得晚于毕业，但不限制学制固定四年；延期、休学、转学由用户确认实际项目的年份，原值保留历史。

key_timepoints 包含 status、source_ids、events。每个 event 使用：

```json
{"name":"准备研究生考试","kind":"preparation","date":"2026","precision":"year","status":"confirmed","source_ids":["SRC-000001"],"related_graduation_year":2028,"eligibility_status":"not_applicable","rule_source_ids":[]}
```

kind 仅为 preparation / application / exam / program_entry / internship / employment / other。precision 为 year / month / day，date 分别为 YYYY / YYYY-MM / YYYY-MM-DD。日期未知时保持 unconfirmed。

正式报名、考试和项目入学节点须关联当前 graduation_year，eligibility_status=verified，并给出已读取、标明 applicable_period 的政策来源 rule_source_ids；不能把备考年份当考试或入学年份。核验政策的学历条件、应届资格、项目学制、届别及例外与用户档案是否吻合，不能仅凭 URL 宣称适用。政策不明时可给备考准备建议，正式节点保留待核，不确认资格。

例如，2028 年毕业的用户可以从 2026 年准备，但不能无依据写成 2026 年正式参加某届考研。运行时拦截无政策来源、毕业锚点错误的结构化节点；它不能判断任意自由文本或外部政策真伪，必须用材料阅读及对话验收补足。

profile / path_decision / cycle_plan / 每条 review 的带日期建议统一使用 `decision_timeline`（同 events 数组契约），禁止另建未校验的日期表作为正式结果。已过期政策重新核验，不复制上一轮资格结论。

## 修改与迁移

只有 Skill 1 可修改 intake；修改后原有依赖区由运行时标 stale，其他阶段提出回交，不跨区修正。schema 1.0.0 须经 upgrade-state 显式迁移到 1.1.0；迁移保留原始备份及历史，补齐待确认字段、降为草稿。不能通过旧 ready 标记绕过门槛。
