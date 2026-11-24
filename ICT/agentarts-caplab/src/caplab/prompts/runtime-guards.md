# 每轮接收、证据与交付门

这些脚本是本 Skill 的输出路径；先运行再发送通过的 response 文件，不能用模型自己给的 passed 替代。宿主若不调用脚本，Skill 无法拦截宿主直接发送的文字。程序检查来源一致性，不证明用户陈述真实；原始消息、上传文件和网页摘录由宿主/操作者采集，不能由模型编写为“原始证据”。

## 会话账本（全部能力，含 low / timid）

测试分流、停止保存规则优先。账本使用同一用户会话或同一 SAVE 的隔离目录 `<scope>/.caplab/turns`，不混用正式和测试存档，不写五阶段 caplab_state。停止保存时只在当前对话维护内存账本，不新增落盘；无法持久化时说明恢复仅限当前对话。不要为了补齐账本向用户增加问题。

1. 把当前原始用户消息写入 UTF-8 临时文件，运行：
   `python scripts/caplab_turn.py --root <ledger-root> begin --input <raw-message.txt>`
   程序在生成回复前持久化 received_intents，自动按子句覆盖多事项。语义识别出的额外任务可用 `--intents <array.json>` 追加，不能删去原始子句。收到事项不一定都要执行，普通叙述也可用回应片段标记 handled。
2. 根据 begin 返回的 revision 与稳定 ID 编写 resolution JSON：
   `base_revision`、`response`、`handled_intents: {ID: 回复中的原文片段}`、`deferred_intents: {ID: 原因}`、`commitment_updates: {ID: 更新对象}`；涉及行业解释设置 `mode: industry`，压力/模拟面试设置 `mode: interview`。不要把内部 JSON 发给用户。
3. 运行：
   `python scripts/caplab_turn.py --root <ledger-root> finish --resolution <resolution.json> --response-output <reply.txt>`
   只有成功才发送 reply.txt；失败修订 response/resolution 后重试。不得重新 begin 来绕过失败，开始新轮次也会保留中断事项为 deferred。
4. 助手提出行动时在 `proposed_actions` 登记回复中的行动原文。用户接受后，或主动要求行动计划时，自动开 commitment；未覆盖的自然语言接受/请求应由编排器在下一轮以额外意图补充，并按原话明确任务。不要把继续聊天当接受。
5. commitment 定义包含 task / deliverable / acceptance_criteria / time_budget / failure_adjustment，使用 `status: defined` 表示“计划已交付”，不表示用户已执行。五项都要在自然语言回复中出现；缺信息可给低成本建议并明确假设。不能补齐时设置 `status: deferred, reason: ...`；下次 status 可读取并继续。`commitment_open` 在 open/deferred 时为 true。
6. 用户说累了、今天到这，直接简短结束。程序保留 deferred，下次继续；不强迫完成面试或承诺定义。可说“今天先休息，两周任务留到下次继续”。保持 low/timid 的一次一个小问题和低压力体验。

received_intents 的每个 ID 必须落入 handled 或 deferred，不能同时出现。commitment 更新只能改内容和状态，不能删除/改 ID。用户回复中的延期提示一句即可；内部状态严格不代表对外长篇解释。

## 事实来源与措辞

`resume-content.json` 增量字段 `fact_bindings` 是 JSON pointer 到 `{source_id}` 的映射。复用已有 SRC ID。每个渲染字段（姓名、学历/学校、联系方式、公司、项目、日期、正文、数字/比例/倍数/排名/奖项/用户量，以及自定义含事实标题）均需来源；仅固定排版标签免校验。

独立来源目录 `--sources-dir` 下每条 JSON：

```json
{"source_id":"SRC-000001","kind":"user_input","locator":"current-session/message-12","text":"我是照教程搭的框，自己改了两个功能。"}
```

kind 可为 user_input / user_confirmation / uploaded_material / external / derived。locator 指向真实原消息、材料页码/单元格或 HTTPS 页面；确认后的最终措辞存为独立 user_confirmation 原始记录，不自造用户确认。不能从生成简历反向制造证据目录。外部来源应先核实适用对象、日期及合法访问范围。

validator 要求字段完整措辞可在对应原始记录中找到；因此数字相同但对象不同不能靠数字匹配过门。高强度词（独立设计/开发/架构、从零搭建/开发、主导、牵头、负责整体、上线、落地、实际使用、用户量、提升/降低/优化、获奖/排名、生产环境）必须同样有原文依据。教程上下文中的独立声明会被拒绝。`downgrade_tutorial` 可将越界措辞自动退回教程原话；其他改写无法证明时请求确认或阻止正式导出。含“反正没人查”等造假意图、否定、未解决来源不得采用；不能进入有效评分。

derived 仅支持 difference / ratio / percent_change 的两操作数复算；calculation.inputs 每项为 source_id/value，原始数值必须在非 derived 来源中存在。输出必须完全等于程序计算结果（可带 unit）。复杂推导应先在原始可复算材料中生成结果，再由用户确认对应表述；不执行任意 eval 或信任 derived=true。

## 简历构建、验收与交付

`build --input ... --output-dir ... --sources-dir ...` 运行事实门。带来源仍失败时拒绝构建，不写未经支持的正式正文。旧 JSON 没有 fact_bindings/来源时仍能生成草稿，但 evidence_status=blocked、score_total=null，评分卡不显示有效分数。

`verify --output-dir ... --sources-dir ... --visual-reviewed --content-reviewed` 在实际视觉与内容检查后执行。验证全部正文来源、重算派生项、检查构建时文件 SHA-256 与来源摘要、重新读取 PDF/日志。任一项失败撤销旧 ready；不能只改 hard_gate_passed、confirmed、report 或 export_status 来跳过。

四维状态：render_status=passed/failed；evidence_status=passed/blocked；content_status=draft/reviewed/passed；delivery_status=draft_only/needs_completion/ready。新 build 一律 draft；只有来源、完整内容、无待确认问题、既有评分门槛、渲染及视觉验收全部通过才 ready。旧 export_status 仅为兼容别名；generated_verified 只在 ready 时写出。

非 ready 回复说明已可查看的草稿、具体缺项与人工确认项，不说“直接投”。将 artifact_dir 与 sources_dir 放入 turn resolution 时，出口会重新验收已 ready 的产物；用户输入的 delivery_status 字符串无效。

## 心理归因与行业范围

输出 validator 拒绝“你的真实动机就是”“你其实只是”“你本质上”“你就是在逃避”等确定归因。用“从你的描述看，害怕失败可能是因素之一，目前还不能判断它是否主要原因”。规则是有限模式检查，不是完整心理语言理解。

行业解释用“不少自动化测试和测试开发岗位会要求写脚本或维护框架，不同公司和岗位差异较大”。压力面试把前提写进句子：“假设这个岗位要求自动化测试，需要写脚本和维护框架……”。不能靠末尾加一句“可能”掩盖前面的绝对断言。

## 兼容边界

五阶段 schema 1.1.0、旧历史与确认流程不变。会话账本独立版本 1.0.0；简历 fact_bindings 可选以支持旧草稿读取；构建报告增量 schema 1.1.0。旧产物若无来源映射、构建哈希和新验收，不能自动升级 ready，须补来源重建。来源、账本包含个人信息，沿用隔离与停止保存规则，不随公开 Skill 包收录用户证据。
