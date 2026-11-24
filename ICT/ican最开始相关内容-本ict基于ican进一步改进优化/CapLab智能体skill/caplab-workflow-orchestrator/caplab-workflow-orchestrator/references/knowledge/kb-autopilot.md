# CapLab KB Autopilot 2.2.0

这是编排器的公共知识维护能力，按需读取；保持五阶段 schema 1.1.0，不写个人 `caplab_state.json`。维护者指定 KB_ROOT、工作簿、专业、地域、时间范围；目录不明时先确认，不能猜测桌面文件。已有授权范围足够时直接执行，不重复索要确认。

## 六种模式

| 模式 | 输入与结果 |
| --- | --- |
| init | 明确专业、地域、用户和路径；建立领域树、实体/来源/治理/监测模型，字段字典与标签词表；初始采集验证结构，不为数量凑案例。脚本仅初始化配置和空快照。 |
| expand | 从覆盖矩阵找缺口，按院校/地域/路径/时间组合检索；打开来源正文，抽取原子 Claim，去重评级，语义复核后形成候选快照。 |
| audit | 全库 G01–G12、覆盖指标、权限检查，写入 32/19 与异常；不自动修正含糊事实。 |
| update | 到期对象及触发事件入 41；核验新资料，OLD/NEW 哈希差异入 42，审核后更新候选，保留旧版。 |
| migrate | 复用字段、证据、治理与更新方法；重新建立专业词表、课程/岗位/项目、案例与来源，不复制原专业事实。 |
| release | 重新质检当前候选；通过后本地归档 43。完成 Excel、卡片/索引和实际检索回归才可发布为运行库。 |

## 标准生产循环

1. 读取真实工作簿表名、字段字典、权限方案与现有发布版本。原表是权威，33–40 垂直模块按需启用。配置表头映射后，由实际表格技能导出 `{"tables": {"表名": [记录]}}` JSON 快照；不得将 Excel 未回写说成已更新。
2. 来源发现使用宿主搜索；官方优先。摘要只是线索，核心事实必须打开原始页面并记录 Source_ID、发布/核验日期、适用地域/周期和快照定位。无法访问或核验的值写 UNKNOWN，不编造来源。
3. `Source → Claim → Entity → 卡片`，事实、推导与产品建议分开。人物案例记录不可迁移条件；单个 JD 不泛化为整个行业。政策/招生/考试/截止日期本次使用须核验。
4. 以字段字典规范值。脚本检测 NEW / UPDATED / EXPIRED / REMOVED / CONFLICT / UNVERIFIED；相同哈希不入队。页面打不开是 UNVERIFIED，不等于 REMOVED；自动差异中缺失行只给疑似移除，需人工确认。
5. G01 来源唯一、G02 URL/路径、G03 日期、G04 必填/UNKNOWN、G09 主键与业务去重、G11 外键闭合由脚本计算。G05 泛化、G06 历史当前、G07 地域、G08 粒度由 LLM 逐条给 PASS/FAIL/REVIEW、理由和证据边界。
6. G10：核心事实至少 B；当前政策/招生/招聘要求原则上 A，B 待审，C/D 不足；冲突待审。高风险变化由实际维护者决定，模型不能代签。G12 计算本次结构、主键、外键、来源覆盖、UNKNOWN、重复、过期、权限、41–44 结构与越权查询回归。
7. 任一 FAIL → BLOCKED；有 REVIEW → REVIEW；12 项均 PASS 才能 12/12。空库、无 Claim、未完成语义审核和过期记录不能发布。语义审核与人工决定需绑定当前哈希；修改数据后重跑，不复用旧放行。
8. 经审核的候选由表格技能按原格式回写并复读，保存备份；再导出 JSON 卡片、构建同模型索引并使用已有原子安装/备份机制。权限在检索前过滤，不把付费内容放进免费上下文。旧库运行直到替换成功；失败保留旧版并报告。

## 本地脚本接口

以下命令从 Skill 根目录运行。脚本仅用 Python 标准库，`--as-of` 明确业务日期以便复现；正常运行用宿主当前日期，时区 Asia/Shanghai。

```bash
python3 scripts/caplab_kb_autopilot.py init --root <KB_ROOT>
python3 scripts/caplab_kb_autopilot.py audit --root <KB_ROOT> --snapshot <current.json> --as-of YYYY-MM-DD --semantic <semantic.json> --approvals <approvals.json>
python3 scripts/caplab_kb_autopilot.py update --root <KB_ROOT> --old <previous.json> --new <current.json> --as-of YYYY-MM-DD
python3 scripts/caplab_kb_autopilot.py release --root <KB_ROOT> --snapshot <current.json> --version <vX.Y.Z> --as-of YYYY-MM-DD --semantic <semantic.json> --approvals <approvals.json>
```

`expand / migrate` 是代理工作模式，不是虚构的脚本子命令：完成采集/转换后复用 audit/update/release。init 拒绝覆盖已有目录。audit/update 的报告每次独立编号；release 重算审核且版本目录不可覆盖，只归档候选，不改生产索引或工作簿。命令失败返回非零状态。

配置：`config/schema.json` 明确每表 kind、主键、必填字段、日期字段、去重键和外键。模板 `15_来源索引 / 02_人物案例 / 16_事实来源 / 36_周期监测总览` 是交换示例；表格技能按真实字段字典映射到标准化字段，保留反向映射以回写原列。来源主键为 source_id，实体/Claim/监测主键为 id；Source_ID/Person_ID/Claim_ID 等原列名不需在 Excel 中改名。来源用 url/source_type/published_at/checked_at/grade/region；Claim 用 entity_id/field/statement/source_id/scope/status/region；权限用 access_label/access_tier/permission_source/permission_version/mask_mode。其他实体与要求表加入配置后才允许发布；未知表阻断，禁止静默漏审。配置和表结构迁移需先把 OLD/NEW 都转换到同一交换 schema；已有候选归档链不自动迁移，不兼容时使用明确的新 KB_ROOT 保留旧链。

语义输入 `{"snapshot_hash":"...","items":[{"id":"Claim_ID","object_hash":"...","gate":"G05","status":"PASS","reason":"具体理由","evidence_scope":"来源支持范围","claim_scope":"结论范围"}]}`，每个 Claim 对 G05–G08 都有一条。哈希使用脚本导出的 `Snapshot_Hash / Object_Hashes`；快照哈希绑定内容表、配置与 as-of 日期，排除报告/治理表，回写质检结果不构成审核循环。不完整、重复、旧哈希为 REVIEW，FAIL 保持阻断。

人工输入 `{"snapshot_hash":"...","items":[{"id":"Claim_ID","object_hash":"...","decision":"APPROVED","reviewer":"真实维护者","reason":"真实决定及依据"}]}`。此文件只承载实际决定，不能让 LLM 生成批准记录。脚本只验证字段和绑定，不认证审核人身份；共享生产环境应由宿主控制文件写权限。

## 运行表、覆盖与输出

- 41：Queue_ID、Object_ID、Priority、Trigger、Detected_Time、Due_Time、Status、Assigned_To、Search_Query、Expected_Change、Result_Change_ID。
- 42：Change_ID、Object_ID、OLD/NEW_Value、OLD/NEW_Source_ID、OLD/NEW_Hash、Change_Type、Detection_Method、Detected_Time、Risk_Level、Review_Status。
- 43：Release_ID、Version、Release_Time、Trigger、Changed/Added/Updated/Removed_Count、Gate_Result、Regression_Result、Human_Approver、Release_Scope、Changelog。
- 44：Exception_ID、Object_ID、Exception_Type、Severity、Description、Evidence、Suggested_Action、Human_Decision、Decision_By/Time、Closed。

脚本报告返回上述表的行与字段，宿主表格技能负责回写。release 自动与该 KB_ROOT 的上一份候选快照比较，初次与空快照比较；移除/权限变化的人工记录也需按报告绑定对象哈希。质检报告另含 `32_数据质检`、`19_评测与试算`、来源关联覆盖率、核心字段完整率、Claim 时效有效率、UNKNOWN率、重复率；分母为零时返回 null。领域/地域/院校/路径/目标组合覆盖需有实际目标矩阵，缺配置就列待补，不制造百分比。G12 的权限查询是本地候选投影检查（Regression_Scope=local_snapshot_projection_only），不证明已部署 RAG 的权限或检索效果；后者须用真实新索引测试。

每次实际运行交付更新后的工作簿或明确的 pending 状态、报告/队列/变化/异常/候选版本文件和 Markdown 摘要：`Version + Gate_Result + Regression_Result + Added/Updated/Blocked + 异常数量 + Excel/Index/Scheduler 状态`。可以按 [对话渲染协议](../dialogue-rendering.md) 丰富摘要，但图形不能遮蔽阻断项。

## 调度接入

默认 `scheduler_status=not_configured`。需要持续自动更新且当前任务已授权时，发现宿主真实调度能力（原文候选为 doubao-cron-scheduler），配置每周质检、每月增量，保存真实任务 ID、Asia/Shanghai 时区、下次执行时间与失败恢复方式。不具备能力时输出可执行工作流和未接入状态，不能声称到点会自行运行。

每周：schema → G01–G12 → 32/19/44 → 候选发布。每月：36 到期 → 41 → 搜索核验 → 42 → 更新候选 → G01–G12 → 43/44。政策/招生/考公公告/截止日期/官方撤回/证据冲突立即 P0/P1 入队并人工复核。无变化保持安静，仅有重要变化、失败或需人工决定时通知。对话结束或停止保存不能变成暗中保存个人信息的理由。
