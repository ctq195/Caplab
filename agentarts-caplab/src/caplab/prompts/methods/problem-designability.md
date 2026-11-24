# 问题可设计性

仅当用户的原始困扰混合了现实边界和可行动部分时读取。目标是把问题改写成可处理的决策，不是说服用户“任何约束都能突破”。

## 三级分类

- `hard_constraint`：本轮无法改变，只能接受、绕行或改变目标范围。
- `partially_designable`：边界真实存在，但路径、地域、组织、组合方式、节奏或资源配置仍可调整。
- `designable`：可通过选择、行动或低成本接触直接改变或验证。

不要只用“重力问题/真问题”二分。行业平均收入、学历门槛、家庭责任等常同时包含硬边界与可设计部分。

## 输出字段

```yaml
problem_designability:
  type: hard_constraint | partially_designable | designable
  original_problem:
  classification_basis:
    - 已知事实、来源记录 ID 或明确约束
  fixed_part:
  designable_part:
  reframed_decision_question:
  requires_reflective_confirmation: true
  unknowns: []
```

只记录有来源的依据。若分类依赖用户动机、价值取舍或对经历的解释，保留未知并交给 `caplab-profile-confirmation`。
