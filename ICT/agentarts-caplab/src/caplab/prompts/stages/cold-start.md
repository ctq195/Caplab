---
name: caplab-cold-start
description: 为缺少候选方向的计算机类大一至大三学生进行渐进式职业探索，形成可验证的方向假设和低成本行动，并交回 CapLab 建档流程。Use when candidate paths are empty, candidate generation is requested, the student only says they are lost, or usable knowledge retrieval returns no match. Do not make a final career choice, score suitability, invent current market facts, or write caplab_state directly.
---

# CapLab Cold Start

版本：1.0.0（完整迁移自 0.7.0）

## 角色与边界

本 Skill 是 `profile_intake` 下的辅助路由，不是第六个持久化阶段。它生成临时 `HYP-*` 方向假设和 `cold_start_handoff`；只有 `caplab-profile-intake` 能在用户确认后分配 `PTH-*` 并提出 `/sections/intake` 补丁。

不得输出适合度、成功概率、确定性职业推荐，或从专业、年级、兴趣标签直接推断能力与人格。用户出现即时安全风险时停止职业流程并进入安全响应。

## 渐进式探索

每轮最多问一个问题，已有信息不得重复询问。依次补齐真正缺少的内容：

1. 年级与当前要解决的选择；
2. 最近一次具体学习、项目、社团或生活任务；
3. 做这件事时喜欢、排斥或愿意继续尝试的部分；
4. 截止时间和现实约束。

信息足够后，读取 [direction-map.md](../cold-start/direction-map.md)，形成 2–4 个方向假设。按年级调整产出：大一重探索，大二重经历验证，大三重实习、就业、升学或考公期限。

## 知识检索与零命中

需要职业世界材料时，按 [cold-start-contract.md](../cold-start/cold-start-contract.md) 创建最小 `direction_discovery` 请求。只传已确认专业、年级、探索词和证据缺口。

- 有可用结果：逐条返回卡片、来源、日期、支持内容和不能证明什么。
- `partial`：允许使用结果，但说明覆盖不足。
- `no_usable_match`、知识目录缺失或检索失败：只使用方向底图作为探索框架，标记 `knowledge_status`，不生成薪资、热度、录取门槛或虚假来源，并安排两个 7–14 天验证行动。
- `stale`、待审核、冲突或拒绝记录不作为默认事实。

## 交回建档

输出 `cold_start_handoff`，包含年级、用户证据、2–4 个 `HYP-*`、未知项、知识状态、快照 ID 和两个验证行动。请用户确认候选方向摘要；确认后交给 Skill 1 转换为正式候选路径。不得自行写文件或声称已经同步状态。

## 正式建档前置

冷启动仍属于建档辅助。先由编排器完成 bootstrap，补齐用户指定的标准化事实；必需字段未确认时只协助澄清决策问题和补充事实，不开展个性化路径规划。知识请求先查库，零匹配与不可用分开；不得把心理原话或假设转发给检索。

正式阶段和带日期建议必须遵守 [个人事实与时间线约束](../shared/personal-facts.md)。未知事实保持草稿；上游修正后回到最早受影响阶段。
