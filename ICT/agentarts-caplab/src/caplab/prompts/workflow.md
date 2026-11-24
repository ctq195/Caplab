# 五阶段路由与准入

每轮先读取 [methods/dialogic-self-understanding.md](methods/dialogic-self-understanding.md)，让贯穿式深度对话协议作用于当前阶段；只有出现叙述矛盾、信息选择性缺失、目标与行为不一致或隐含前提时，再读取 [methods/li-kaipi-dialogue-patterns.md](methods/li-kaipi-dialogue-patterns.md)。这两份文件是内部方法引用，不是单独阶段或 Skill。

然后根据 `caplab_state.py route` 的结果只读取当前阶段文件：

- `profile_intake`：读取 [stages/profile-intake.md](stages/profile-intake.md)。
- `profile_confirmation`：读取 [stages/profile-confirmation.md](stages/profile-confirmation.md)。
- `path_convergence`：读取 [stages/path-convergence.md](stages/path-convergence.md)。
- `path_evidence_cycle`：读取 [stages/path-evidence-cycle.md](stages/path-evidence-cycle.md)。
- `evidence_review`：读取 [stages/evidence-review.md](stages/evidence-review.md)。

只加载当前阶段，避免把五套输出规则同时放入上下文。若阶段文件要求的入口状态与实际状态冲突，以运行时校验和更早阶段为准。

阶段完成后不手写 `next_skill`。先应用经确认补丁，再由 `route` 根据已落盘状态选择下一阶段。
