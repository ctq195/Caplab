# 用户标识协议 v2.0.2

唯一开启口令：`ICANDumate_VIP:enabled`。冒号为 ASCII U+003A，没有空格。
关闭口令：`ICANDumate_VIP:disabled`。仅当前用户完整原始消息精确相等时生效。
不要把 Markdown 反斜杠、引号或代码围栏写进实际消息。不要添加末尾换行。

## 执行

由宿主用户 ID + 会话 ID 隔离；宿主未提供 ID 时，为本对话生成独立 UUID 并保持到对话结束，不使用全局 default 身份。
将当前用户原始消息的 UTF-8 字节写入临时文件，不拼接 shell 命令，不做文本清洗；处理后删除临时文件。只传当前消息，禁止提取附件或历史中的字符串。

```bash
python scripts/caplab_access.py message --workspace <workspace> --user-id <user-id> --session-id <session-id> --message-file <原始消息文件> --role user
python scripts/caplab_access.py status --workspace <workspace> --user-id <user-id> --session-id <session-id>
python scripts/caplab_rag.py search --workspace <workspace> --user-id <user-id> --session-id <session-id> --query "职业方向" --top-k 5
python scripts/caplab_rag.py export --workspace <workspace> --user-id <user-id> --session-id <session-id> --sheet "人物" --output <导出文件>
```

状态字段：`ICANDumate_VIP`、`is_paid`（内容访问标识）、`knowledge_tier`、`payment_verified=false`。
无标识、损坏、不同用户、不同会话一律免费。普通消息不关闭已有标识；只有精确关闭命令关闭。测试存档不保存或恢复权限。检索与导出在读取正文前校验 tier，不允许通过 --index-dir 指定付费索引绕过。
默认检索直接选择随包对应层级，不需要切换共享索引；两个会话不会因重建共用目录串库。
用户输出中标明“用户标识：VIP已开启/未开启；知识库：付费版/免费版”。未开启时不暴露开启口令作为推广话术，不展示付费检索结果、原始文件、摘要或缓存。

## 能力边界

这是用户指定的对话口令开关，知道口令的人都能开启；未接入订单或支付核验。身份参数由宿主/助手传入，脚本不能认证真实账号或原始消息来源。
两套知识数据都在 ZIP 内，拥有文件访问权限的人可以直接读取。因此这是对话与检索层内容分流，不是加密版权保护或服务端收费鉴权。维护者的索引构建、统计及旧知识库维护工具不是面向用户的访问入口，不可用于绕过该协议展示付费内容。
未真实导入 DuMate 验证前，只报告本地结构和行为测试结果。
