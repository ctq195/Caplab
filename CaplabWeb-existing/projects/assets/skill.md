# CapLab-KB-Autopilot
## 新专业知识库 0→1 构建、扩充、质检与自动更新 Skill
### 通用可复现版本 v1.1｜可执行质检与增量更新版

---

## 0. Skill定位

### 0.1 目标

本 Skill 用于把“某一个新专业/新学科”的零散公开资料，系统化建设为一个：

- 可检索
- 可追溯
- 可扩展
- 可复核
- 可版本化
- 可持续更新
- 可迁移到其他专业

的专业成长与路径知识库。

它不是一次性“搜资料做 Excel”，而是一套长期数据工程流程：

> 专业定义 → 场景建模 → 数据模型 → 来源采集 → 原子事实 → 实体关联 → 案例/岗位/目标要求 → 标签体系 → 覆盖率 → 证据质检 → 发布 → 周期监测 → 增量更新 → 回归检查

### 0.2 适用对象

可用于：

- 计算机科学与技术
- 软件工程
- 经济学
- 金融学
- 工商管理
- 国际经济与贸易
- 法学
- 新闻传播
- 机械工程
- 电气工程
- 生物/医学相关专业
- 任何存在“本科背景 → 继续深造/就业/考公/出国”等路径选择的专业

### 0.3 核心原则

1. **先定义数据结构，再开始搜索。**
2. **事实、案例、规则、推论必须分层。**
3. **所有关键事实必须能回溯到来源。**
4. **具体岗位要求不能直接泛化成整个岗位族要求。**
5. **当前有效信息与历史案例必须分开。**
6. **UNKNOWN ≠ 空白。无法确认必须显式记录 UNKNOWN。**
7. **不允许为了凑数量制造案例或补齐不存在的信息。**
8. **每次更新都必须留下版本和审计痕迹。**
9. **自动化负责发现、整理、比对；关键事实由规则和人工复核把关。**
10. **知识库是导航与决策基础设施，不是更新日志。**

---

# 一、总架构：先搭“骨架”，再填“内容”

## 1.1 推荐的五层架构

### Layer 1：导航层

负责回答：

> 这个知识库有什么？从哪里进入？

核心表：

- `00_总览`
- `01_字段字典`
- `17_标签词表`

要求：

- 只做导航、定义和口径说明。
- 不记录大量单次更新细节。
- 新专业接入时优先复制这一层。

---

### Layer 2：实体层

负责描述“谁、什么、去哪里”。

推荐实体：

- 人物
- 本科背景
- 毕业后去向
- 岗位
- 岗位要求
- 目标对象
- 目标要求
- 路径节点
- 路径模板
- 机会窗口
- 风险情境
- 申请事件

典型表：

```text
02_人物案例
03_本科后去向
04_路径节点
06_招聘岗位
07_岗位要求
08_目标对象
09_目标要求
10_路径模板
13_机会窗口
14_风险情境
24_目标实例
25_窗口实例
26_申请事件
27_路径冲突
```

---

### Layer 3：证据层

负责回答：

> 这个结论从哪里来的？

核心表：

```text
15_来源索引
16_事实来源
23_理论依据
```

推荐结构：

```text
Source_ID
Claim_ID
Entity_ID
Target_Instance_ID
事实
事实状态
来源类型
来源发布者
发布日期
URL/路径
原文定位
核验日期
证据等级
适用范围
局限
生效开始
生效结束
```

最重要的关系：

```text
来源 Source
    ↓
原子事实 Claim
    ↓
实体 Entity
    ↓
目标/案例/岗位
    ↓
产品输出
```

不要让“一个网页”直接等于“一个结论”。

---

### Layer 4：治理层

负责回答：

> 数据是否可信？哪里有问题？

核心表：

```text
20_覆盖与质量
21_证据质检
22_审计记录
32_数据质检
28_领域覆盖
29_要求证据映射
30_差距判定规则
```

治理层必须独立存在。

不要把“我觉得这条没问题”当作质量控制。

---

### Layer 5：运行层

负责回答：

> 什么时候更新？更新什么？怎么知道旧数据过期？

核心表：

```text
36_周期监测总览
```

可以继续增加：

```text
41_更新队列
42_变更检测
43_版本发布
44_异常待审
```

---

# 二、0→1第一步：定义“新专业”的边界

## 2.1 输入

用户只需要提供：

```text
专业名称
目标国家/地区
主要服务人群
知识库用途
希望覆盖的路径
```

例如：

```text
专业：经济学
人群：本科生
地区：中国大陆
路径：
- 求职就业
- 考研
- 考公
- 出国/港硕
```

---

## 2.2 先建立“专业领域树”

格式：

```text
专业
├── 本科培养
├── 继续深造
│   ├── 国内考研
│   └── 出国/港硕
├── 就业
│   ├── 对口岗位
│   ├── 跨专业岗位
│   └── 实习
├── 公务员/事业单位
├── 行业方向
├── 能力要求
├── 证书/技能
└── 风险与机会窗口
```

注意：

不要一开始就决定“每个模块必须有50条”。

先确定：

> 这个专业需要哪些实体。

数量属于第二阶段。

---

# 三、第二步：建立“最小可用数据模型”

新专业第一次建库，不建议直接复制几十张表。

先建立 MVP：

```text
00_总览
01_字段字典
02_人物案例
03_本科后去向
06_招聘岗位
07_岗位要求
08_目标对象
09_目标要求
10_路径模板
15_来源索引
16_事实来源
17_标签词表
20_覆盖与质量
21_证据质检
22_审计记录
```

达到稳定运行后，再按专业增加：

```text
考研项目详情
考公考试批次
考公职位详情
留学项目详情
留学申请轮次
机会窗口
历史分数
留学录取案例
路径冲突
```

原则：

> 先有稳定骨架，再增加垂直模块。

---

# 四、第三步：设计字段字典

## 4.1 每个字段至少定义六件事

| 字段 | 必须说明 |
|---|---|
| 字段名 | 稳定、唯一 |
| 类型 | text / number / date / enum / boolean |
| 必填性 | required / optional |
| 定义 | 这个字段到底代表什么 |
| 来源要求 | 什么情况下才能填 |
| 维护规则 | 后续如何更新 |

---

## 4.2 必须区分三类字段

### A. 事实字段

例如：

```text
本科院校
本科专业
毕业年份
岗位名称
发布日期
最低学历
申请截止日期
```

必须来自证据。

### B. 推导字段

例如：

```text
路径阶段
适用人群
风险标签
可能的转向节点
```

可以由多个事实推导，但必须标记为推导结果。

### C. 产品字段

例如：

```text
学生最小任务
行动阶段
建议优先级
MVP是否使用
```

这是产品设计，不应该伪装成外部事实。

---

# 五、第四步：建立“来源分级体系”

推荐：

```text
A = 原始官方/原文，可直接核验
B = 母内容可访问，但部分细节依赖截图/检索结果/二级定位
C = 机构摘要、转载、数据库摘要等，信息不完整
D = 用户生成内容/论坛/社交媒体，仅作为案例线索
```

特殊情况：

```text
B-商业语境访谈
```

用于标记：

> 内容已核验，但存在课程、培训、商业推广等利益关系。

### 来源优先级

```text
官方机构
  ↓
高校官方
  ↓
政府/公共平台
  ↓
企业官方招聘
  ↓
权威研究机构
  ↓
学术论文
  ↓
媒体报道
  ↓
论坛/社交平台
```

注意：

来源级别高，不代表它能支持所有结论。

---

# 六、第五步：先建“来源库”，再建“案例库”

## 6.1 正确顺序

错误：

```text
搜到一个人
→ 写进人物表
→ 再想来源
```

正确：

```text
发现来源
→ 登记 Source_ID
→ 提取原子事实
→ 判断事实可信度
→ 关联实体
→ 生成案例
```

---

## 6.2 原子事实原则

例如网页说：

> 某学生本科毕业后进入A公司，工作两年后考研。

不要直接记录成：

> “该学生成功实现了职业跃迁。”

应该拆成：

```text
Claim_001
本科院校 = X

Claim_002
本科专业 = Y

Claim_003
毕业年份 = 2023

Claim_004
第一去向 = A公司

Claim_005
工作时长 = 2年

Claim_006
后续路径 = 国内考研
```

“成功”“逆袭”“优秀”“最佳选择”等评价性词汇除非有明确研究定义，否则不能自动写入事实层。

---

# 七、第六步：人物案例标准化

## 7.1 人物案例不是“鸡汤故事”

每个人物至少拆成：

```text
Person_ID
姓名/匿名标识
案例类型
国家/地区
主路径
本科院校
本科专业
本科院校层次
毕业年份
毕业后第一去向
后续路径
当前角色
关键转折
可迁移经验
不可复制条件
适用人群
使用警告
Source_ID
```

---

## 7.2 “不可复制条件”必须单独记录

这是 CapLab 的重要治理设计。

例如：

```text
[时代] 该案例发生于某行业高增长时期
[地域] 机会依赖特定城市/地区
[院校] 依赖特殊学校资源
[家庭] 依赖家庭资源
[政策] 依赖特定政策窗口
[行业] 依赖特殊行业周期
[个人] 存在极强个人特质
```

这样可以防止：

> “别人这样走成功了 → 所有学生都应该这样走。”

---

# 八、第七步：岗位库必须拆成“岗位”和“要求”

这是整个知识库中非常重要的结构。

## 8.1 岗位表

记录：

```text
Role_ID
公司
岗位名称
岗位族
用工类型
地点
目标人群
发布日期
职责摘要
最低学历
专业
来源
```

## 8.2 岗位要求表

从具体JD拆出：

```text
Job_Req_ID
Role_ID
类别
原子要求
归一层级
原始层级依据
候选证据
学生最小任务
行动阶段
优先级
Source_ID
```

---

## 8.3 禁止泛化

例如：

某一家公司的：

> “熟悉Python、SQL”

只能写成：

> 该岗位要求Python、SQL。

不能自动升级成：

> “数据分析岗位都要求Python、SQL。”

除非有多个独立来源支持。

---

# 九、第八步：目标要求体系

“岗位要求”和“目标要求”必须分开。

### 岗位要求

回答：

> 某家公司这个岗位现在要求什么？

### 目标要求

回答：

> 学生要达到某个目标，通常需要满足哪些条件？

例如：

```text
Target_ID = UK_CS_Master
```

下面可以有：

```text
学历
本科专业
GPA
语言
GRE
先修课
科研
项目
申请轮次
费用
截止日期
```

每一项都应尽可能绑定：

```text
Target_Instance_ID
Source_ID
核验日期
有效期
```

---

# 十、第九步：标签体系

标签不是装饰，而是检索和更新的基础设施。

## 10.1 推荐至少建立八组标签

```text
专业标签
院校层次
地域标签
时间标签
路径标签
行业标签
能力标签
治理标签
```

---

## 10.2 时间标签

至少保留：

```text
毕业年份
事件年份
数据发布日期
核验日期
生效开始
生效结束
下一复核日期
```

---

## 10.3 重大事件标签

用于解释：

```text
疫情
金融危机
行业风口
政策变化
招聘周期
留学政策变化
技术范式变化
```

目的不是增加故事，而是避免把特殊时代案例当成当前规律。

---

# 十一、第十步：不同专业如何“换皮”复用

Skill 不应该写死“计算机”。

采用参数化：

```yaml
domain:
  name: {{专业名称}}
  aliases: []
  major_families: []

population:
  target_users: 本科生
  geography: 中国大陆

paths:
  - 就业
  - 国内考研
  - 考公
  - 出国/港硕

case_target:
  employment: 50
  postgraduate: 50
  civil_service: 50
  overseas: 50

quality:
  min_source_level: B
  require_source_for_core_fact: true
  unknown_policy: explicit
```

例如换成经济学：

```yaml
domain.name = 经济学
```

然后自动生成：

```text
经济学就业案例
经济学考研案例
经济学考公案例
经济学出国/港硕案例
经济学岗位要求
经济学研究生项目
经济学相关公务员职位
```

核心结构不变，只替换领域实体和检索词。

---

# 十二、第十一步：案例扩充算法

## 12.1 不允许随机搜索

采用“覆盖矩阵”。

例如：

| 维度 | 候选 |
|---|---|
| 院校 | 985 / 211 / 双非 / 专科 |
| 去向 | 就业 / 考研 / 考公 / 出国 |
| 地域 | 一线 / 新一线 / 二三线 / 海外 |
| 行业 | 互联网 / 金融 / 制造 / 公共部门 / 教育等 |
| 路径 | 对口 / 跨专业 / 二次转向 |
| 时间 | 近年 / 历史 |

目标不是每格完全相等，而是避免样本严重偏斜。

---

## 12.2 每次扩充流程

```text
检查当前覆盖
↓
找最缺的组合
↓
生成检索任务
↓
批量搜索来源
↓
来源登记
↓
提取事实
↓
去重
↓
证据评级
↓
加入案例
↓
重新计算覆盖率
```

---

# 十三、第十二步：检索策略

## 13.1 一个案例至少使用三层检索

### 第一层：定向搜索

```text
专业 + 本科 + 就业 + 公司
专业 + 本科 + 考研 + 学校
专业 + 本科 + 考公 + 上岸
专业 + 本科 + 留学 + 学校
```

### 第二层：来源追踪

找到案例后：

```text
姓名
→ 学校官网
→ 公司官网
→ 采访
→ 论文/报道
→ 原始帖子
```

### 第三层：交叉核验

至少核验关键节点：

```text
本科背景
第一去向
核心转折
当前去向
```

不是所有字段都必须三源交叉，但核心事实不能完全依赖单一低等级来源。

---

# 十四、第十三步：去重规则

每条新数据进入数据库前必须进行：

```text
URL去重
标题去重
Person_ID去重
公司+岗位+发布日期去重
Target_Instance_ID去重
Claim语义去重
```

### 人物案例去重

优先键：

```text
姓名 + 本科院校 + 毕业年份
```

若存在同名：

```text
姓名 + 院校 + 专业 + 时间
```

---

# 十五、第十四步：自动更新机制

自动更新不是“让AI每天重做整个知识库”。

应该采用：

> 增量检测 + 变化队列 + 规则审核 + 发布闸门

---

## 15.1 四种更新任务

### A. 高频更新

适合：

```text
招聘岗位
考公公告
考试批次
申请截止日期
机会窗口
政策
```

频率：

```text
每日/每周
```

### B. 中频更新

适合：

```text
研究生项目
留学项目
语言要求
院校申请规则
```

频率：

```text
每月
```

### C. 低频更新

适合：

```text
人物案例
路径模板
理论依据
专业能力框架
```

频率：

```text
季度/半年
```

### D. 触发式更新

当发现：

```text
政策变化
重大行业变化
岗位要求显著变化
申请制度变化
```

立即进入复核队列。

---

# 十六、第十五步：周期监测表

建议建立：

```text
领域
子域
历史核验案例
当前可直接决策案例
未来监测对象
当前状态
下一复核日期
发布闸门
主要边界
```

例如：

```text
就业 | 招聘岗位 | 50 | 32 | 100 | 监测中 | 2026-10-01
考公 | 招录批次 | 50 | 12 | 2027批次 | 监测中 | 2026-10-15
留学 | 项目要求 | 50 | 38 | 2027申请季 | 监测中 | 2026-11-01
```

---

# 十七、第十六步：变更检测

每次更新不要直接覆盖旧值。

比较：

```text
OLD
vs
NEW
```

生成：

```text
Change_ID
Entity_ID
字段
旧值
新值
变化类型
来源
发现日期
严重程度
是否需要人工审核
处理结果
```

变化类型：

```text
NEW
UPDATED
REMOVED
EXPIRED
CONFLICT
UNVERIFIED
```

---

# 十八、第十七步：可执行质检闸门

> 本章是 v1.1 的核心改造。12 个闸门不再是“手填检查清单”，而是明确分成：
> **脚本确定性检查（可自动判定）→ LLM 语义检查（逐条给结论和理由）→ 人工复核（高风险事件）**。
>
> `32_数据质检` 的 `12/12` 必须由程序根据本章规则计算，不允许人工直接填写“12/12”。

## 18.1 三层质检模型

| 层级 | 闸门 | 判定方式 | 自动化程度 | 输出 |
|---|---|---|---|---|
| 脚本确定性 | G01/G02/G03/G04/G09/G11 | Python 规则 | 100% 自动 | PASS/FAIL + 明细 |
| LLM 语义 | G05/G06/G07/G08 | 逐条语义判断 | 自动初判 | PASS/FAIL/REVIEW + 理由 |
| 混合/证据 | G10 | 规则计算证据等级与阈值 | 自动 + 必要人工 | PASS/FAIL/REVIEW |
| 人工高风险 | G12及高风险冲突/政策事件 | 人工复核 | 人工确认 | APPROVED/REJECTED |

### 总体状态计算

```text
AUTO_PASS = G01+G02+G03+G04+G09+G11 全部 PASS
SEMANTIC_PASS = G05+G06+G07+G08 全部 PASS
EVIDENCE_PASS = G10 PASS
HUMAN_PASS = 所有触发人工复核的对象均 APPROVED

12/12 = AUTO_PASS AND SEMANTIC_PASS AND EVIDENCE_PASS AND HUMAN_PASS
```

任何一个闸门为 `FAIL`，整体不得发布；`REVIEW` 不计入 PASS，进入 `44_异常待审`。

---

## 18.2 G01｜来源存在——脚本确定性

### 判定
对每一条需要证据的 Claim/Requirement/Case，必须存在有效 `Source_ID`，且 `Source_ID` 能在 `15_来源索引` 找到唯一记录。

### Python 规则

```python
def check_g01(rows, sources):
    source_ids = {str(x["Source_ID"]).strip() for x in sources if x.get("Source_ID")}
    errors = []
    for r in rows:
        if r.get("evidence_required", True):
            sid = str(r.get("Source_ID", "")).strip()
            if not sid or sid not in source_ids:
                errors.append({"row": r.get("ID"), "reason": "Source_ID不存在或未建立来源记录"})
    return {"gate": "G01", "status": "PASS" if not errors else "FAIL", "errors": errors}
```

### PASS 条件
- `Source_ID` 非空；
- 在 `15_来源索引` 中存在；
- 关联唯一。

---

## 18.3 G02｜URL/路径格式——脚本确定性

### 判定
Web 来源必须为 `http://` 或 `https://`；本地/数据库/官方文件等非 URL 来源必须填写合法 `URL/路径` 类型说明，不能出现纯文本标题冒充路径。

```python
from urllib.parse import urlparse

def valid_url(value):
    try:
        u = urlparse(str(value).strip())
        return u.scheme in {"http", "https"} and bool(u.netloc)
    except Exception:
        return False

def check_g02(sources):
    errors=[]
    for r in sources:
        v=str(r.get("URL/路径", "")).strip()
        typ=str(r.get("来源类型", "")).strip()
        if typ in {"网页", "官网", "公告", "招聘", "大学官网", "政府公开平台"} and not valid_url(v):
            errors.append({"Source_ID":r.get("Source_ID"),"reason":"URL格式无效"})
    return {"gate":"G02","status":"PASS" if not errors else "FAIL","errors":errors}
```

---

## 18.4 G03｜日期有效——脚本确定性

### 必查日期
- 发布日期
- 毕业年份
- 核验日期
- 生效开始/结束
- 下一复核日期

### 判定
日期必须能解析；年份必须处于合理范围；`生效结束 < 生效开始` 直接 FAIL；`下一复核日期` 不能是自由文本。

```python
from datetime import date

def parse_date(v):
    if v in (None, "", "UNKNOWN"): return None
    return date.fromisoformat(str(v)[:10])

def check_g03(rows):
    errors=[]
    today=date.today()
    for r in rows:
        for field in ["发布日期","核验日期","生效开始","生效结束","下一复核日期"]:
            v=r.get(field)
            if v not in (None, "", "UNKNOWN"):
                try: parse_date(v)
                except Exception: errors.append({"ID":r.get("ID"),"field":field,"reason":"日期不可解析"})
        a,b=r.get("生效开始"),r.get("生效结束")
        if a and b and parse_date(b)<parse_date(a):
            errors.append({"ID":r.get("ID"),"reason":"生效结束早于生效开始"})
    return {"gate":"G03","status":"PASS" if not errors else "FAIL","errors":errors}
```

---

## 18.5 G04｜UNKNOWN 显式——脚本确定性

### 判定
对于“必须知道但当前无法确认”的字段，必须填写 `UNKNOWN`，禁止空白、`N/A`、`待定`、`不详`等自由变体替代。

### 规则
```python
UNKNOWN = "UNKNOWN"

def check_g04(rows, required_fields):
    errors=[]
    for r in rows:
        for f in required_fields:
            if f not in r or str(r.get(f, "")).strip()=="":
                errors.append({"ID":r.get("ID"),"field":f,"reason":"必填字段为空，应为具体值或UNKNOWN"})
    return {"gate":"G04","status":"PASS" if not errors else "FAIL","errors":errors}
```

`UNKNOWN` 只能表示“当前无法确认”，不能用于掩盖已知事实。

---

## 18.6 G05｜不越权泛化——LLM 语义判断

LLM 必须逐条回答：

1. 这条结论的证据对象是什么？
2. 证据只支持某个人/某个岗位/某个项目，还是支持一个群体？
3. 文本是否把“案例事实”写成“普遍规律”？
4. 是否出现“通常、都、必然、只要、一定、普遍”等未经群体证据支持的表达？
5. 是否把单个 JD 的要求升级成整个岗位族要求？

### 判定
- `PASS`：结论范围 ≤ 证据范围；
- `FAIL`：明显扩大适用范围；
- `REVIEW`：证据边界或语言含义存在歧义。

LLM 必须输出：
```json
{
  "gate":"G05",
  "status":"PASS|FAIL|REVIEW",
  "reason":"具体说明证据范围与结论范围",
  "evidence_scope":"具体对象",
  "claim_scope":"结论对象"
}
```

---

## 18.7 G06｜历史/当前分离——LLM 语义判断

检查事实是否明确区分：
- 历史案例；
- 当前有效规则；
- 当前招聘；
- 已过期窗口；
- 未来监测对象。

若一条历史信息被写成当前要求，`FAIL`。
若时间边界不充分，`REVIEW`。

LLM 必须检查 `事件时间 / 发布日期 / 核验日期 / 生效期 / 当前状态` 是否逻辑一致，并给出理由。

---

## 18.8 G07｜地域适用范围——LLM 语义判断

检查：
- 中国大陆/港澳台/海外是否混用；
- 国家、地区、城市、学校、机关、企业范围是否被扩大；
- 一个地区的政策/岗位/录取规则是否被写成全国规则。

### 判定
- 证据和结论地域完全一致：`PASS`；
- 证据范围小于结论范围：`FAIL`；
- 地域边界缺失但可补证：`REVIEW`。

---

## 18.9 G08｜项目粒度——LLM 语义判断

必须判断对象是否落在正确粒度：

```text
专业
 └─ 学校/机构
     └─ 项目/岗位/职位/考试批次
         └─ 具体要求
             └─ 原子事实
```

例如：
- “某大学计算机专业硕士要求”不能直接写成“所有计算机硕士要求”；
- “2026年某省公务员某职位要求”不能写成“公务员普遍要求”；
- “某公司某岗位 JD”不能升级成“该岗位族全部要求”。

LLM 输出 `PASS/FAIL/REVIEW + 粒度链条 + 理由`。

---

## 18.10 G09｜去重——脚本确定性

### 去重键
- 来源：标准化 URL；
- 人物：`Person_ID`；
- 岗位：`公司 + 岗位名称 + 发布日期/批次`；
- 项目：`学校/机构 + 项目名 + 入学/申请周期`；
- Claim：`实体ID + 字段/主题 + 规范化事实`；
- Change：`对象ID + 检测时间 + 新旧哈希`。

```python
import hashlib, json

def norm(v):
    return " ".join(str(v or "").strip().lower().split())

def row_hash(row, fields):
    payload={f:norm(row.get(f)) for f in fields}
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def check_g09(rows, key_fields):
    seen={}; errors=[]
    for r in rows:
        key=tuple(norm(r.get(f)) for f in key_fields)
        if key in seen:
            errors.append({"ID":r.get("ID"),"duplicate_of":seen[key]})
        else: seen[key]=r.get("ID")
    return {"gate":"G09","status":"PASS" if not errors else "FAIL","errors":errors}
```

---

## 18.11 G10｜证据等级满足阈值——规则 + 人工

证据等级沿用现有 `15_来源索引 / 21_证据质检` 体系，不改变原有 A/B/C/D 口径。

### 默认规则
- 核心事实：至少 B；
- 当前政策/招生/招聘要求：原则上 A，若只有 B 则进入人工复核；
- D 类来源：只能作为线索，不能单独关闭发布闸门；
- 冲突来源：不得自动选一个覆盖另一个，必须进入 `44_异常待审`。

`G10 = PASS` 的必要条件是：证据等级达到该对象规定阈值，且没有未处理冲突。

---

## 18.12 G11｜关键表关联闭合——脚本确定性

### 核心关系

```text
Entity
  ↓
Claim / Requirement / Case
  ↓
Source
```

以及：

```text
Role_ID → 06_招聘岗位 → 07_岗位要求 → Source_ID
Target_Instance_ID → 09_目标要求 → Source_ID
Person_ID → 03_本科后去向 → 02_人物案例 → Source_ID
```

### 自动规则
- 外键必须存在；
- 外键必须唯一；
- 不允许孤儿记录；
- 要求/事实必须能回到来源；
- 任何已发布实体不得存在断链。

```python
def check_fk(rows, field, valid_ids):
    errors=[]
    valid=set(str(x) for x in valid_ids)
    for r in rows:
        v=str(r.get(field,"" )).strip()
        if v and v not in valid:
            errors.append({"ID":r.get("ID"),"field":field,"value":v})
    return errors

def check_g11(relations):
    errors=[]
    for rel in relations:
        if rel["source_id"] not in rel["source_ids"]:
            errors.append(rel)
    return {"gate":"G11","status":"PASS" if not errors else "FAIL","errors":errors}
```

---

## 18.13 G12｜回归测试通过——自动计算 + 人工兜底

每次结构、字段、标签、脚本、检索权限发生变化，都必须运行 `19_评测与试算`。

### 自动测试至少包括
- 表名/字段名存在；
- 主键唯一；
- 外键闭合；
- 来源覆盖率；
- UNKNOWN 规范；
- 重复率；
- 过期记录识别；
- 权限标签完整；
- 运行层 41–44 表结构完整；
- 关键查询结果未出现越权数据。

### G12 判定
- 全部自动测试 PASS 且无人工高风险事项：`PASS`；
- 有失败：`FAIL`；
- 有高风险变更未人工签字：`REVIEW`。

---

## 18.14 `32_数据质检` 的自动计算口径

`32_数据质检` 不允许人工输入“12/12”。建议字段：

| 字段 | 含义 |
|---|---|
| Run_ID | 本次质检运行编号 |
| Run_Time | 运行时间 |
| G01_Status | PASS/FAIL |
| G02_Status | PASS/FAIL |
| G03_Status | PASS/FAIL |
| G04_Status | PASS/FAIL |
| G05_Status | PASS/FAIL/REVIEW |
| G06_Status | PASS/FAIL/REVIEW |
| G07_Status | PASS/FAIL/REVIEW |
| G08_Status | PASS/FAIL/REVIEW |
| G09_Status | PASS/FAIL |
| G10_Status | PASS/FAIL/REVIEW |
| G11_Status | PASS/FAIL |
| G12_Status | PASS/FAIL/REVIEW |
| Auto_Pass_Count | 自动 PASS 数 |
| Review_Count | REVIEW 数 |
| Fail_Count | FAIL 数 |
| Gate_Result | 12/12 或 BLOCKED |
| Blocking_Reason | 阻断原因 |
| Audit_ID | 审计记录 |

### 计算公式

```python
def calc_gate_result(statuses):
    fail=sum(v=="FAIL" for v in statuses.values())
    review=sum(v=="REVIEW" for v in statuses.values())
    passed=sum(v=="PASS" for v in statuses.values())
    if fail:
        result="BLOCKED"
    elif review:
        result="REVIEW"
    else:
        result="12/12"
    return passed, review, fail, result
```

---

# 十八-A、运行层：增量更新必须有载体

原有 `36_周期监测总览` 只负责“监测什么、什么时候复核”，不能承担变化队列、差异快照、发布记录和异常处理。因此必须新增以下四张表。

## 18-A.1 `41_更新队列`

用途：所有待抓取、待核验、待更新对象的工作队列。

| 字段 | 说明 |
|---|---|
| Queue_ID | 队列项唯一 ID |
| Object_Type | Case/Role/Target/Source/Policy等 |
| Object_ID | 对象 ID |
| Trigger_Type | 到期/新增/变化/冲突/人工触发 |
| Priority | P0/P1/P2/P3 |
| Detected_Time | 发现时间 |
| Due_Date | 最迟处理日期 |
| Assignee | 执行者 |
| Status | NEW/PROCESSING/DONE/BLOCKED |
| Related_Change_ID | 对应变更记录 |
| Result | 处理结果 |
| Updated_At | 更新时间 |

## 18-A.2 `42_变更检测`

用途：保存 OLD/NEW 比对，不覆盖历史。

| 字段 | 说明 |
|---|---|
| Change_ID | 变更唯一 ID |
| Object_Type | 对象类型 |
| Object_ID | 对象 ID |
| Detected_Time | 检测时间 |
| Previous_Hash | OLD 快照哈希 |
| Current_Hash | NEW 快照哈希 |
| Changed_Fields | 发生变化的字段 |
| OLD_Value | 旧值/快照位置 |
| NEW_Value | 新值/快照位置 |
| Change_Type | NEW/UPDATED/REMOVED/EXPIRED/CONFLICT/UNVERIFIED |
| Source_ID | 新证据来源 |
| Severity | P0-P4 |
| Review_Status | PENDING/APPROVED/REJECTED |

### 变化检测原则

```text
当前数据 → 标准化 → Hash
                  ↓
            与上次 Hash 比较
             ↙          ↘
          相同            不同
           ↓               ↓
        NO_CHANGE      写入42_变更检测
                           ↓
                      生成41_更新队列
```

## 18-A.3 `43_版本发布`

用途：记录每次知识库发布，而不是覆盖旧版本。

| 字段 | 说明 |
|---|---|
| Release_ID | 发布 ID |
| Version | vX.Y.Z |
| Release_Time | 发布时间 |
| Trigger | 初始化/增量/结构变更/紧急修复 |
| Changed_Count | 变化对象数量 |
| Added_Count | 新增 |
| Updated_Count | 更新 |
| Removed_Count | 删除/失效 |
| Gate_Result | 12/12/REVIEW/BLOCKED |
| Regression_Result | PASS/FAIL |
| Human_Approver | 人工审核人 |
| Release_Scope | 发布范围 |
| Changelog | 变更摘要 |

## 18-A.4 `44_异常待审`

用途：所有自动化无法安全决定的事项统一落点。

| 字段 | 说明 |
|---|---|
| Exception_ID | 异常 ID |
| Object_ID | 对象 ID |
| Exception_Type | 冲突/语义歧义/政策/权限/证据不足/结构异常 |
| Severity | P0-P4 |
| Description | 异常说明 |
| Evidence | 相关 Source/Change |
| Suggested_Action | 建议动作 |
| Human_Decision | APPROVE/REJECT/EDIT |
| Decision_By | 审核人 |
| Decision_Time | 时间 |
| Closed | YES/NO |

---

# 十八-B、定时调度：谁到点执行

`36_周期监测总览` 的 `下一复核日期` 只是调度输入，不是调度器本身。运行环境统一由 **doubao-cron-scheduler** 承担。

## Task 01｜每周质检

```yaml
name: caplab-weekly-qc
schedule: weekly
frequency: "每周一次"
steps:
  - load_kb
  - run_table_schema_check
  - run_G01_G04
  - run_G09_G11
  - run_G05_G08_semantic_review
  - run_G10_evidence_check
  - run_19_regression
  - write_32_quality_result
  - write_44_exceptions
  - if_all_pass: prepare_release
```

目标：`32_数据质检 + 19_评测与试算`。

## Task 02｜每月增量监测

```yaml
name: caplab-monthly-update
schedule: monthly
frequency: "每月一次"
steps:
  - read_36_monitoring
  - find_due_objects
  - create_41_update_queue
  - search_and_verify_sources
  - snapshot_old_new
  - write_42_change_detection
  - update_entities_and_claims
  - run_quality_gates
  - write_43_release
  - write_44_exceptions
```

### 触发式例外

以下事件不等待月度任务：
- 政策/招生规则变化；
- 公务员考试公告/职位表变化；
- 招聘 JD 重大变化；
- 申请截止日期变化；
- 官方页面明确撤回/修改；
- 高风险证据冲突。

一旦触发，直接创建 `41_更新队列`，优先级 P0/P1，并进入人工复核链路。

---

# 十八-C、执行环境与工具契约

> Skill 必须明确“文件在哪里、谁负责读写、谁负责搜索、结果怎么交付”。否则它只能作为方法论，不能实际运行。

## 18-C.1 知识库目录契约

默认目录：

```text
CapLab_KB/
├── workbook/
│   └── CapLab公共知识库.xlsx
├── sources/
│   ├── raw/          # 原始网页/公告/文件快照
│   └── normalized/   # 标准化来源记录
├── snapshots/
│   ├── previous/     # OLD
│   └── current/      # NEW
├── reports/
│   ├── qc/
│   ├── audit/
│   └── release/
├── scripts/
│   ├── qc_deterministic.py
│   ├── diff_detector.py
│   └── regression.py
└── config/
    ├── schema.yaml
    ├── quality_rules.yaml
    └── permission_rules.yaml
```

如果实际项目目录不同，必须在初始化参数中覆盖 `KB_ROOT`，禁止由模型猜目录。

## 18-C.2 Excel 读写契约

- Excel 结构/读写：使用项目配置的 **sheet 技能**；
- Python 只负责确定性计算、校验、Hash、差异检测和测试；
- 不允许模型通过自由文本“假装写入 Excel”；
- 写入前必须通过 schema 检查；
- 写入后必须重新跑 G01-G12 与回归。

## 18-C.3 来源搜索契约

- 来源发现：使用通用搜索；
- 官方来源优先；
- 搜索结果只作为候选来源，不等于事实；
- 关键事实必须打开来源并记录 `Source_ID`；
- 来源变更进入 `42_变更检测`，而不是直接覆盖旧记录。

## 18-C.4 产物交付契约

每次运行至少交付：

```text
1. 更新后的 Excel 知识库
2. 32_数据质检结果
3. 19_评测与试算结果
4. 41_更新队列（如有）
5. 42_变更检测（如有）
6. 43_版本发布记录
7. 44_异常待审（如有）
8. 本次运行摘要 Markdown
```

不得只回复“已更新”，必须返回：`Version + Gate_Result + Regression_Result + Added/Updated/Blocked + 异常数量`。

---

# 十八-D、付费权限血缘：从“标签”落到检索过滤

> 本节只固化权限机制，不擅自重建用户此前 9-20 讨论中的具体付费标签枚举。具体标签值、免费/付费边界必须以项目既有方案为唯一来源，并写入 `17_标签词表` 与 `config/permission_rules.yaml`。

## 18-D.1 权限血缘链

```text
Source / Claim / Entity
        ↓
Access_Label
        ↓
Access_Policy
        ↓
User_Tier
        ↓
Retrieval_Filter
        ↓
Visible / Masked / Locked
```

## 18-D.2 必须新增的权限字段

至少在相关实体/卡片层保留：

| 字段 | 作用 |
|---|---|
| Access_Label | 内容访问标签 |
| Access_Tier | 内容所需用户层级 |
| Permission_Source | 权限规则来源 |
| Permission_Version | 权限规则版本 |
| Mask_Mode | 隐藏/摘要/锁定等呈现方式 |
| Entitlement_Check | 是否通过用户权限检查 |

## 18-D.3 检索端硬规则

1. 权限过滤发生在检索/返回之前，不在前端显示后再隐藏；
2. 被过滤内容不得进入低权限用户的上下文；
3. 免费版与付费版只能通过权限规则控制，不复制两套事实数据；
4. 权限变更必须留下 `43_版本发布` 记录；
5. 权限规则变化必须触发 `19_评测与试算` 中的越权回归测试；
6. 权限标签缺失的高价值付费对象进入 `44_异常待审`，不得默认放开。

## 18-D.4 权限回归测试

至少测试：

```text
Free → 不得检索付费锁定 Claim
Free → 可以检索免费公开 Claim
Paid → 可以检索其 Entitlement 范围内 Claim
权限变化 → 新旧结果集差异可追踪
```

如果 9-20 原方案的具体标签表重新可检索，必须把该标签表原样接入 `17_标签词表`，并把本节的 `Access_Label / Access_Tier / Mask_Mode` 映射到原方案，而不是重新发明一套标签。

---

# 十九、第十八步：覆盖率体系

不要只统计：

> “一共多少条。”

必须至少统计：

```text
总案例数
有效案例数
A/B证据案例数
来源覆盖率
核心字段完整率
目标组合覆盖率
地域覆盖率
院校层次覆盖率
路径覆盖率
时效有效率
重复率
UNKNOWN率
待审核数
过期数
冲突数
```

推荐：

```text
来源覆盖率 =
有有效Source_ID的记录 / 总记录

核心字段完整率 =
核心字段非UNKNOWN记录 / 总记录

时效有效率 =
当前有效记录 / 当前决策记录

证据闭环率 =
同时存在Entity + Claim + Source的记录 / 核心记录
```

---

# 二十、第十九步：知识库卡片层

如果知识库最终要被AI调用，建议增加：

```text
18_KB卡片
```

它不是事实原表，而是：

> 给Agent快速读取的结构化摘要。

推荐格式：

```text
KB_ID
标题
对象类型
对象ID
适用专业
适用路径
核心结论
关键事实
证据等级
不可复制条件
使用边界
关联来源
最后核验
下一复核
```

---

# 二十一、第二十步：AI调用原则

Agent不能直接：

```text
搜索结果 → 给学生建议
```

应该：

```text
用户目标
↓
匹配目标对象
↓
读取目标要求
↓
读取人物/岗位/项目案例
↓
读取时间与地域约束
↓
检查证据等级
↓
识别UNKNOWN
↓
生成比较
↓
输出下一步
```

---

# 二十二、自动更新 Skill 的核心执行流程

## 模式A：新专业建库

```text
输入专业
→ 生成领域树
→ 生成实体表
→ 生成字段字典
→ 生成标签词表
→ 生成来源规则
→ 建立最小数据库
→ 初始化覆盖矩阵
→ 输出首轮检索任务
```

## 模式B：扩充案例

```text
读取覆盖表
→ 找缺口
→ 生成检索式
→ 搜索
→ 提取来源
→ 提取Claim
→ 去重
→ 生成Entity
→ 证据评级
→ 质量检查
→ 写入
→ 更新覆盖率
```

## 模式C：周期更新

```text
读取周期监测
→ 找到期对象
→ 搜索新资料
→ 比较OLD/NEW
→ 标记变化
→ 人工审核高风险变化
→ 更新事实
→ 保留旧版本
→ 重跑质检
→ 发布新版本
```

## 模式D：专业迁移

```text
读取公共模板
→ 替换专业词表
→ 替换检索模板
→ 替换目标路径
→ 初始化覆盖矩阵
→ 保留治理规则
→ 重新采集领域数据
```

---

# 二十三、推荐的 Skill 输入协议

用户只需要告诉AI：

```text
【新建知识库】

专业：
地区：
目标用户：
用途：
路径：
案例数量目标：
是否需要岗位库：
是否需要考研：
是否需要考公：
是否需要留学：
是否需要周期更新：
```

如果用户只给：

> “帮我做经济学知识库。”

Skill 应自动追问或合理默认：

```text
专业 = 经济学
目标用户 = 本科生
地区 = 中国大陆
核心路径 = 就业/考研/考公/出国
```

但如果涉及高风险或强时效规则，应要求确认地区和时间范围。

---

# 二十四、推荐的 Skill 输出协议

首次运行必须输出：

### 1. 知识库架构

```text
实体表：
证据表：
治理表：
监测表：
```

### 2. 字段字典

输出所有表字段及定义。

### 3. 首轮数据

明确：

```text
已建立多少
待补多少
UNKNOWN多少
```

### 4. 证据报告

```text
A：
B：
C：
D：
```

### 5. 覆盖报告

明确缺口：

```text
985不足
双非不足
考公不足
海外不足
岗位不足
近期数据不足
```

### 6. 更新计划

```text
高频：
中频：
低频：
触发式：
```

---

# 二十五、推荐的自动化任务模板

## Task 01｜发现

```text
请扫描{{专业}}的公开信息，重点寻找{{路径}}相关案例、岗位、项目和政策。
不要直接写入知识库。
先输出：
1. 来源
2. 来源类型
3. 发布时间
4. 可能支持的事实
5. 证据等级
6. 可能存在的局限
```

## Task 02｜抽取

```text
根据来源{{Source_ID}}，只抽取原文能够支持的事实。
每条事实独立成Claim。
禁止推测。
无法确认字段写UNKNOWN。
```

## Task 03｜建模

```text
将Claims映射到：
Person / Role / Target / Project / Window
不得因为一个Claim缺少字段而补写不存在的信息。
```

## Task 04｜质检

```text
检查：
1. 来源
2. 日期
3. URL
4. 重复
5. 冲突
6. 时效
7. 地域
8. 项目粒度
9. 泛化
10. UNKNOWN
```

## Task 05｜更新

```text
比较旧版本和新资料。
只报告实际发生的变化。
将变化分为：
NEW / UPDATED / EXPIRED / REMOVED / CONFLICT / UNVERIFIED
```

---

# 二十六、专业迁移时“不能复制”的东西

公共 Skill 可以复制：

```text
表结构
字段规范
证据等级
标签逻辑
质检规则
审计机制
版本机制
更新机制
覆盖率算法
```

但以下内容必须重新建立：

```text
专业岗位
专业课程
专业能力
院校项目
专业相关考公岗位
专业相关留学项目
行业公司
行业关键词
专业案例
专业术语
检索词
时效规则
```

原则：

> 复制“方法”，不要复制“事实”。

---

# 二十七、版本管理

版本建议：

```text
v0.1 = 骨架
v0.2 = 首轮数据
v0.5 = 核心模块可用
v1.0 = MVP稳定
v1.x = 数据增量
v2.0 = 数据模型重大变化
```

每次发布记录：

```text
版本
发布日期
新增
修改
删除
过期
新增来源
质检结果
覆盖率变化
已知问题
下一步
```

不要把版本更新日志塞进 `00_总览`。

总览只负责导航。

---

# 二十八、审计机制

每次发现问题建立：

```text
Audit_ID
严重程度
影响范围
发现的问题
修正内容
影响/结果
审计版本
```

严重等级：

```text
P0 = 会导致错误决策
P1 = 核心事实错误
P2 = 重要字段缺失
P3 = 格式/标签问题
P4 = 优化建议
```

---

# 二十九、最容易失败的十种做法

## 1. 先搜一堆资料再想结构

后果：

数据无法统一。

## 2. 为了达到“50个案例”而凑案例

后果：

重复、低质量、不可用。

## 3. 用一个网页支撑整段结论

后果：

无法知道网页到底证明了什么。

## 4. 把成功故事当作规律

后果：

产生幸存者偏差。

## 5. 把历史规则当当前规则

后果：

高风险。

## 6. 把岗位要求泛化

后果：

把单公司要求变成行业规律。

## 7. 把UNKNOWN留成空白

后果：

无法区分“没有填写”和“无法确认”。

## 8. 没有地域和时间标签

后果：

不同地区、年份的数据混在一起。

## 9. 只做内容更新，不做结构回归

后果：

越更新越乱。

## 10. 让AI自动修改所有高风险事实

后果：

错误会被批量放大。

---

# 三十、推荐的完整目录模板

新专业默认生成：

```text
{{专业}}_CapLab/
│
├── 00_总览
├── 01_字段字典
├── 02_人物案例
├── 03_本科后去向
├── 04_路径节点
├── 05_访谈洞察
├── 06_招聘岗位
├── 07_岗位要求
├── 08_目标对象
├── 09_目标要求
├── 10_路径模板
├── 11_证据规则
├── 12_行动模板
├── 13_机会窗口
├── 14_风险情境
├── 15_来源索引
├── 16_事实来源
├── 17_标签词表
├── 18_KB卡片
├── 19_评测与试算
├── 20_覆盖与质量
├── 21_证据质检
├── 22_审计记录
├── 23_理论依据
├── 24_目标实例
├── 25_窗口实例
├── 26_申请事件
├── 27_路径冲突
├── 28_领域覆盖
├── 29_要求证据映射
├── 30_差距判定规则
├── 31_运行接口
├── 32_数据质检
│
├── 33_考研项目详情
├── 34_考公考试批次
├── 35_考公职位详情
├── 36_周期监测总览
├── 37_留学项目详情
├── 38_留学申请轮次
├── 39_考公历史分数
└── 40_留学录取案例
```

其中 33—40 属于“按需要启用”的垂直模块，不要求所有专业一开始全部填满。

---

# 三十一、从0到1的标准项目流程

## Phase 0｜定义

```text
专业
用户
地区
路径
用途
```

## Phase 1｜建模

```text
实体
字段
标签
来源
证据
质检
```

## Phase 2｜首轮采集

建议优先建立：

```text
10—20人物案例
10—20岗位
10—20目标对象
核心路径模板
核心来源库
```

目的：

> 验证结构，而不是追求数量。

## Phase 3｜扩充

根据覆盖缺口：

```text
20 → 50
50 → 100
```

扩充不是机械增加，而是填补组合缺口。

## Phase 4｜治理

运行：

```text
来源检查
字段检查
重复检查
冲突检查
时效检查
覆盖检查
```

## Phase 5｜发布

形成：

```text
v1.0
```

## Phase 6｜监测

建立：

```text
下一复核日期
更新频率
变化检测
异常队列
```

## Phase 7｜长期运行

每次更新：

```text
发现
→ 抽取
→ 比对
→ 审核
→ 更新
→ 质检
→ 发布
→ 审计
```

---

# 三十二、最终评价标准

一个“可复现的新专业知识库”至少应该满足：

### 结构

- [ ] 有字段字典
- [ ] 有实体关系
- [ ] 有来源层
- [ ] 有治理层
- [ ] 有监测层

### 数据

- [ ] 核心路径都有数据
- [ ] 不同院校层次都有样本
- [ ] 不同地域有覆盖
- [ ] 不同路径有覆盖
- [ ] 当前与历史分离

### 证据

- [ ] 核心事实可追溯
- [ ] Source_ID完整
- [ ] 关键事实有核验日期
- [ ] 证据等级明确
- [ ] 商业语境有标记

### 质量

- [ ] 无明显重复
- [ ] 无无来源核心事实
- [ ] 无单案例行业泛化
- [ ] 无历史规则冒充当前规则
- [ ] UNKNOWN显式化

### 更新

- [ ] 有下一复核日期
- [ ] 有更新队列
- [ ] 有变更类型
- [ ] 有版本号
- [ ] 有审计记录
- [ ] 更新后能重新跑质检

---

# 三十三、Skill的核心思想

不要把这个项目理解成：

> “帮我做一个专业知识库。”

应该理解成：

> **建立一套可以把任何专业的公开信息持续转换为“结构化事实—案例—要求—路径—证据—决策支持”的数据生产系统。**

真正可迁移的不是某个专业的50个人物案例，也不是某个岗位列表，而是：

```text
统一数据模型
+
证据链
+
覆盖矩阵
+
标签系统
+
质量闸门
+
周期监测
+
增量更新
+
版本审计
```

这八部分稳定后，新增一个专业，本质上只是：

```text
换专业词表
→ 换检索规则
→ 换实体数据
→ 重新建立领域覆盖
```

而不是重新发明一套知识库。

---

# 三十三-A、v1.1 执行化变更清单

本版本针对“能不能真正跑起来”补齐以下能力：

- G01/G02/G03/G04/G09/G11：给出 Python 确定性规则；
- G05/G06/G07/G08：规定 LLM 逐条判定、理由和 REVIEW 状态；
- G10：明确证据等级阈值与冲突处理；
- G12：绑定 `19_评测与试算`，并禁止手填 12/12；
- 新增 `41_更新队列`、`42_变更检测`、`43_版本发布`、`44_异常待审`；
- 新增每周/每月 doubao-cron-scheduler 调度契约；
- 新增知识库目录、Excel、搜索、产物交付工具契约；
- 新增付费权限血缘与检索前过滤机制；
- 保留 9-20 既有付费标签枚举的接入位，未凭空重建具体标签值。

# 三十五、推荐执行命令

以后可以将这个 Skill 固化为：

```text
$caplab-kb-autopilot
```

推荐支持以下模式：

```text
$caplab-kb-autopilot init
$caplab-kb-autopilot expand
$caplab-kb-autopilot audit
$caplab-kb-autopilot update
$caplab-kb-autopilot migrate
$caplab-kb-autopilot release
```

### init

从0创建新专业。

### expand

根据覆盖缺口扩充数据。

### audit

执行全库质量审计。

### update

检查周期到期和最新变化。

### migrate

把公共模型迁移到新专业。

### release

通过发布闸门并生成新版本。

---

## 结语

CapLab的真正可复现能力，不是“拥有多少条数据”，而是：

> **任何团队成员拿到同一套字段、证据、标签、质检和更新规则，都能够从0开始重新构建一个新专业，并在后续继续维护，而不是依赖最初建库的人。**

