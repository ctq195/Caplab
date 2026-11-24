# 模拟面试输出合同

## 输入最小集

- `target_job`：岗位名及 JD 或通用岗位说明；
- `candidate_material`：简历或已确认经历；
- `session_preferences`：可选的模式、题数、时长、语言和难度。

## 会话对象

- `session_scope`：岗位版本、材料版本、题目范围和限制；
- `status`：CREATED / IN_PROGRESS / COMPLETED / EVALUATED；
- `current_index`：当前主问题位置；
- `questions`：问题、依据、用户回答、追问和状态；
- `evaluation`：完成后生成的逐题观察、优势、缺口和练习建议；
- `limitations`：材料不足、未覆盖维度和持久化能力。

## 强制区分

- 模拟题 ≠ 目标公司真实题库；
- 练习评分 ≠ 录用概率或招聘方评分；
- 当前回答未体现 ≠ 用户没有该能力；
- 文件已生成 ≠ 报告已完成视觉检查。

本合同不扩展 V1.0.0 `caplab_state`。除非后续增加 schema、写权限和迁移方案，不要把会话对象写入现有五阶段状态文件。
