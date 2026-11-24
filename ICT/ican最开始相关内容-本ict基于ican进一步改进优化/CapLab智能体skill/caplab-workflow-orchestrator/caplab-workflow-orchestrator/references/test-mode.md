# 显式 Save / Read Save 测试协议

## 先解析命令

任何正式状态、历史、个人材料或测试存档读取之前，先运行：

```bash
python3 scripts/caplab_test_mode.py --text "<当前原始输入>"
```

### 新建存档

唯一的新建格式是：

```text
上海师范大学商学院中法计算机测试存档 Save 31415926：<本次非空测试正文>
```

解析结果为 `action=create` 后，使用同一条命令中的口令创建存档：

```bash
python3 scripts/caplab_test_archive.py create \
  --root <workspace>/.caplab-test-archives \
  --access-code 31415926
```

程序会生成下一个可用编号，例如 `SAVE-000001`。只有命令成功后才能宣告创建，第一条回复必须明确显示：`测试存档编号：SAVE-000001`。随后把新建命令中的测试正文及助手回复追加到该 SAVE。

### 读取并继续存档

唯一的读取格式是：

```text
Read Save SAVE-000001 31415926
Read Save SAVE-000001 31415926：<本轮继续优化的内容>
```

必须同时满足：`Read Save`、完整六位 SAVE 编号、正确口令。解析结果为 `action=read` 后，才运行：

```bash
python3 scripts/caplab_test_archive.py show \
  --root <workspace>/.caplab-test-archives \
  --save-id SAVE-000001 \
  --access-code 31415926
```

编号不存在、口令错误、缺少 `SAVE-`、编号不是六位或语法不完整时，拒绝命令，不读取任何存档，也不转入正式 CapLab 流程。

## 保存当前轮次

读取或创建成功后，只能向已授权的当前 SAVE 追加：

```bash
python3 scripts/caplab_test_archive.py append \
  --root <workspace>/.caplab-test-archives \
  --save-id SAVE-000001 \
  --access-code 31415926 \
  --role user \
  --text "<本轮文本>"
```

仅在存档处于 active 且用户允许保存时，助手回复才以 `role=assistant` 追加。每轮显示当前 SAVE 编号。用户明确结束且不再优化时可运行 `close`；关闭后不得继续追加。

## 隔离规则

1. 新建 Save 不读取正式记忆或任何旧 SAVE，只使用新建命令冒号后的正文和内置公共知识库。
2. Read Save 只读取命令点名的一个 SAVE，不扫描、搜索、比较或概括其他 SAVE。
3. 同一 SAVE 可跨新对话继续来回优化；每个新对话的第一条必须重新提供完整 Read Save 命令。
4. 测试内容只能写入 `.caplab-test-archives/<SAVE-ID>/`，不得写入正式 `.caplab/state`、个人画像、revision、正式历史或账户长期记忆。
5. 内置公共知识库可以读取；工作区可变 RAG、个人文件和正式用户知识不得读取。
6. `31415926` 是防误读口令，不是加密或身份认证。SAVE 编号可猜测且配置包内可见，不得用于真正敏感信息。
7. 即时自伤、他伤或紧迫危险仍执行安全响应，但不扩大存档读取范围。

## 平台边界

脚本能够在文件层拒绝错误口令、错误编号和跨存档读取。Skill 不能删除平台已经注入的聊天历史，也不能替 DuMate 关闭账户级记忆。因此，新建测试与 Read Save 都应从新的平台对话开始；平台侧隔离仍需导入后实测。

## 停止保存优先级（V2.1.1）

先判断本轮是否要求停止保存，再决定是否追加本轮内容。用户要求停止保存心理内容时，调用 pause，暂停当前 SAVE 的全部后续追加，不将停止要求中的心理原文再次 append。不得通过新建 SAVE 绕过同一对话的停止意愿。实际脚本是按 SAVE 隔离的，跨 SAVE 的用户意愿需要调用层继续遵守。

```bash
python scripts/caplab_test_archive.py pause --root <workspace>/.caplab-test-archives --save-id SAVE-000001 --access-code 31415926
python scripts/caplab_test_archive.py resume --root <workspace>/.caplab-test-archives --save-id SAVE-000001 --access-code 31415926 --confirm
```

pause 不删除原 transcript；暂停期间 append 对用户、助手、系统事件均拒绝。show 和 Read Save 不恢复追加。用户明确同意恢复后才调用 resume --confirm；closed 不能恢复。暂停只写最小状态元数据，不保存停止原因、原话或心理摘要。平台自身的聊天历史不由 Skill 删除。详见 [演示操作与故障边界](demo-operations.md)。
