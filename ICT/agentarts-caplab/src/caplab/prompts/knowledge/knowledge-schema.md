# 本机知识字段合同

## 通用卡片

必填：`id`、`card_type`、`title`、`created_at`、`updated_at`、`major_tags`、`region_tags`、`time_tags`、`major_event_tags`、`claims`、`source_ids`、`review_status`、`supports`、`cannot_prove`。

审核状态只使用 `machine_validated`、`pending_human_review`、`human_approved`、`conflicting`、`stale`、`rejected`。

每条 claim 包含 `statement`、`source_ids`、`status` 和 `claim_type`。`claim_type` 使用 `fact`、`reported_practice`、`transferable_hypothesis`、`model_interpretation`。后两类不得伪装为来源事实。

## 人物卡

`pool` 使用 `famous`、`alumni`、`ordinary_public`、`setback_or_transition`、`cross_major_bridge`。另含教育/职业时间线、决策点、行动、结果、代价、可迁移假设和不可迁移条件。

## 职业卡

包含职业代码、核心活动、进入门槛、工作环境、适用地域、相邻角色和 `valid_until`。薪资、需求、资格、考试等动态 claim 必须有地域、口径和有效期。

## 路径卡

包含方向、制度路径、前置条件、阶段、桥接方式、现实验证、切换条件和风险。路径卡是综合解释，必须同时引用职业事实与人物或制度来源。

## 来源

来源包含 `source_id`、URL、标题、发布者、类型、发布时间、核验时间、地域、适用期、动态类型、`valid_until`、审核状态、快照位置和说明。搜索结果摘要不是可用来源。
