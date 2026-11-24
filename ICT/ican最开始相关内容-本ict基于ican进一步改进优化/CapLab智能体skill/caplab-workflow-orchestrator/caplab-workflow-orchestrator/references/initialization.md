# 初始化与运行说明（v2.1.1）

> v2.0.2 用户权限以 [VIP 标识协议](vip-access.md) 为准。以下 tier / 文件名识别只用于数据分类，不授予付费权限。普通用户检索应省略 --index-dir，携带当前用户与会话标识；付费文件只可在标识开启后读取。

## 1. 两条初始化路径

### 1.1 快速路径（评审端 / 开箱即用，推荐）

评审或演示环境**不需要下载任何模型**，也不需要 torch：

```bash
python scripts/bootstrap.py check --workspace <workspace>
python scripts/caplab_rag.py init --prebuilt <skill>/assets/prebuilt_index/free --index-dir <workspace>/.caplab/knowledge_index
python scripts/caplab_state.py init --root <workspace>/.caplab/state --allow-temporary   # 首次临时工作区；正式目录省略 --allow-temporary
python scripts/caplab_state.py validate --root <workspace>/.caplab/state
python scripts/caplab_state.py route --root <workspace>/.caplab/state
```

索引必须先生成（状态命令会校验知识就绪）。`init --prebuilt` 只是把随 Skill 发布的 JSON + npy 索引文件复制到工作区，**秒级完成**。查询编码由随包 int8 ONNX 模型（`assets/models/bge-small-zh-v1.5-int8`，约 30 MB）在本机完成，全程离线。

依赖安装（首次，轻量，约 20 MB）：

```bash
python scripts/bootstrap.py setup --workspace <workspace> --confirm
```

依赖清单：`numpy`、`onnxruntime`、`tokenizers`。**不含 torch / openpyxl / sentence-transformers / HuggingFace 下载。**（openpyxl 仅维护者从 xlsx 重建时需要，见 1.2。）

### 1.2 维护者路径（从 JSON 卡片重建，推荐）

知识库源随包发布为 JSON 卡片（`assets/knowledge-cards/<free|paid>/`，评审端可直接打开阅读）。重建索引只需轻量依赖：

```bash
python scripts/build_prebuilt_index.py --cards assets/knowledge-cards/paid \
  --model-dir assets/models/bge-small-zh-v1.5-int8 \
  --tier paid --out assets/prebuilt_index
```

### 1.3 维护者路径（从 Excel 重建，需 openpyxl）

团队本机维护 xlsx 权威台账后：

```bash
# xlsx -> JSON 卡片（一次性转换）
pip install openpyxl
python scripts/export_kb_cards.py --excel "CapLab公共知识库_v2.3.0_付费版.xlsx" \
  --tier paid --out assets/knowledge-cards

# 卡片 -> 索引（无需 openpyxl）
python scripts/build_prebuilt_index.py --cards assets/knowledge-cards/paid \
  --model-dir assets/models/bge-small-zh-v1.5-int8 --tier paid --out assets/prebuilt_index
```

旧式直接索引（`caplab_rag.py init --excel ... --embedding-api ...`）仍可用，仅适合需要 API 编码向量的场景。

重建后请将索引打包为预建 bundle（见 `scripts/build_skill_zip.py` 或手工收集
`index_meta.json / documents.json / sparse_index.json / sources.json / claims.json / tags.json / embeddings.npy`），随新版本 Skill 一起发布。

## 2. 运行状态与首次使用

- 首次对话：AI 先运行 `bootstrap.py check`，核对依赖、索引、模型、JSON 卡片与状态；需要安装依赖或复制索引时，先展示范围与路径，用户明确确认后执行。
- 知识库版本识别：优先读取已有索引元数据 `tier`/`kb_version` 或知识卡片 `assets/knowledge-cards/<free|paid>/index.json`，其次看工作区文件名（`CapLab公共知识库_v2.3.0_免费版.xlsx` / `_付费版.xlsx`）；识别不出时保持免费，不通过口头选择授予权限。
- 索引一致性：索引 `tier`/`kb_version` 与当前确定版本不符时，先重建或重新 `init --prebuilt` 再继续业务。
- 检索模式：每轮检索输出 `retrieval_mode` 与 `embedding_channel`；向量不可用时明示降级（`sparse_fallback`），不伪称混合检索。

## 3. 边界

- 动态信息（招生、考试、岗位、费用、截止日期）仍须回到官方页面核验并标注核验日期；不可访问时标记"待核验"。
- 预建索引对应知识库版本的快照；知识库更新后需由维护端重建并重新发布，索引本身不自动更新。
- 分享链接的接收端需具备本地运行环境（安装 Skill + 复制索引）方可完整复现；分享链接只代表已完成的对话成果。

## LaTeX 简历模块（v2.1.0）

简历入口见 [简历生成流程](capabilities/resume/resume.md)。该模块无需先初始化 RAG 或开通 VIP。系统需提供 latexmk、XeLaTeX 和 ctex/Fandol 等模板宏包；完整验收另需 pdfinfo、pdfplumber 及 PDF 渲染工具。`bootstrap.py setup` 仅安装 RAG 依赖，不安装 TeX。缺少工具时保留 JSON、TeX、评分卡及未验证构建报告，不声称 PDF 已生成或验收。

## V2.1.1 索引完整性与恢复

随包每层增加 index_manifest.json，记录全体索引文件 SHA-256。检索、导出和正式状态就绪检查均验证清单、文件、JSON、计数、倒排引用及向量形状。缺失或损坏索引不得用“稀疏降级”掩盖；只有查询编码依赖不可用时正常降级。
init --prebuilt 经独占锁、同文件系统暂存、验证后切换；原目录移到同级 `.<目录名>.backups/<唯一编号>` 并在结果中返回 backup。已安装同一清单直接复用。目标中的未知文件不覆盖；旧版没有清单但结构完整的索引先备份再升级。真正空目录可安装，空元数据不是合法索引。

```bash
python scripts/caplab_index.py verify --index <索引目录>
python scripts/caplab_index.py install --index <已验证备份目录> --target <工作区>/.caplab/knowledge_index
```

普通异常在切换失败时自动恢复原目录。进程被强制终止或断电可能留下锁、暂存或备份，不能声称自动恢复：确认无安装进程后检查备份、解除遗留锁，再执行以上恢复命令。未知或损坏的当前目录需先由维护者另行归档，安装器不会擅自覆盖。
seal 命令只用于维护者明确构建的新索引，不是修复坏包的方式；SHA-256 清单是完整性检查，不是数字签名。
