# 奥德赛路径变体

仅当候选路径过窄、用户被单一方案锚定或明确需要发散时读取。借鉴 Life Design 的多版本思路，但不强制三个五年计划。

可从下列生成框架中选择真正有区分度的角度：

- `continuation`：延续当前积累可能形成什么路径；
- `disappearance`：当前方案不可行时还有什么可行路径；
- `constraint_relaxed`：暂时降低金钱或社会评价权重，哪些生活要素值得探索。

```yaml
path_variant:
  path_id:
  generation_frame:
  path_statement:
  desired_life_elements: []
  key_assumptions: []
  hard_constraints: []
  evidence_supporting: []
  evidence_missing: []
  prototype_questions: []
```

每个变体必须是用户真愿意考虑的可能性，不是凑数备胎。生成后仍按现实约束、正反证据和资源成本归入 `primary`、`complementary`、`deferred`、`excluded` 或 `undetermined`。
