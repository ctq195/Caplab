---
name: caplab-knowledge-maintainer
description: 在 DuMate 本机工作区按已确认专业和候选路径按需创建、增量维护并检索可溯源的职业世界知识库，包括来源、人物、职业和路径卡、去重、时效检查及人工审核队列。Use only as the CapLab path stage's background support or when explicitly maintaining the local CapLab knowledge folder. Do not infer a user's major or tendency, store personal profile data, turn successful people into formulas, or present stale dynamic facts as current.
---

# CapLab Knowledge Maintainer

版本：2.2.0

## 角色

本 Skill 是 `caplab-path-convergence` 的后台支持。它维护当前 DuMate 工作区的本机公共知识，不向其他设备共享，也不写 `caplab_state.json`。

## 入口门槛

只接受符合 [knowledge-contract.md](knowledge/knowledge-contract.md) 的最小请求：已确认专业、候选路径 ID、地域、时间窗口、检索模式和证据缺口。运行：

```bash
python3 ../scripts/caplab_knowledge.py validate-request --request <request.json>
```

请求含原始对话、完整画像、健康、家庭、经济或联系方式时拒绝，并要求编排器重建最小请求。专业是用户事实或官方目录规范化结果；倾向只来自用户已确认画像或已接受路径，本 Skill 不重新测评。

## 自动更新与专业建库

维护者明确要求 `init / expand / audit / update / migrate / release` 时，按 [kb-autopilot.md](knowledge/kb-autopilot.md) 执行。该维护入口接受显式 KB_ROOT、专业、地域、时间及工作簿配置，不需要个人画像或候选 PTH。后台学生请求仍必须通过上面的最小请求门，不能借维护入口读取付费库或扩大个人数据采集。

已有 `caplab_knowledge.py` 的本机 JSON 卡片库与工作簿生产链分别记录；未完成显式转换、权限过滤和检索回归前，不把维护候选版本当成正在使用的 RAG 版本。

## 按需维护循环

1. `init` 当前工作区的 `knowledge/`；已有库时不得覆盖。
2. 运行 `freshness`、`validate` 和 `retrieve`，先复用仍有效的本机卡片。
3. 覆盖不足或动态信息过期时，按 [source-policy.md](knowledge/source-policy.md) 制定检索清单并联网查找原始页面。
4. 搜索摘要只用于发现来源。读取正文后建立原子来源和 claim；只保存必要摘录与元数据，不复制整篇受版权保护内容。
5. 生成来源、人物、职业或路径 JSON，使用 `add` 入库。重复、冲突或低质量记录自动进入 `review_queue/`。
6. 再次运行 `validate` 与 `freshness`；不通过时不得返回为可用知识。
7. 按 `background_similar` 和 `goal_oriented` 两种模式检索，并把快照交回 Skill 3。

命令和字段见 [knowledge-contract.md](knowledge/knowledge-contract.md)，卡片语义见 [knowledge-schema.md](knowledge/knowledge-schema.md)。

## 人物案例边界

分别维护 `famous`、`alumni`、`ordinary_public`、`setback_or_transition`、`cross_major_bridge`。人物卡记录可核验时间线、决策点、行动、结果、代价和不可照搬条件。

“成功经验”只能写为：

- `reported_practice`：本人或可靠来源明确报告的做法；
- `transferable_hypothesis`：模型提出、等待现实验证的可能经验。

不得从最终职位倒推人格、动机、家庭资源或成功因果，也不得把案例比例写成成功概率。

## 审核与使用

- `machine_validated` 人物卡可作为可能性案例，必须标明未人工审核。
- 动态门槛用于排除路径前，必须在本次使用时重新核验，或达到 `human_approved`。
- `pending_human_review`、`conflicting`、`stale`、`rejected` 不进入默认检索结果。
- 人工决定用 `review` 记录审核人说明；不静默改写来源或删除冲突。

## 返回 Skill 3

每条结果必须包含：检索依据、相似点、关键差异、不可迁移条件、来源与日期、支持什么、不能证明什么、审核状态。结果是证据候选，不是匹配排名。

用户权限以 [VIP 标识协议](vip-access.md) 为准；付费数据须先校验当前会话标识。
