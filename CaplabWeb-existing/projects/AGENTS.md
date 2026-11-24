# 项目上下文

### 版本技术栈

- **Framework**: Next.js 16 (App Router)
- **Core**: React 19
- **Language**: TypeScript 5
- **UI 组件**: shadcn/ui (基于 Radix UI)
- **Styling**: Tailwind CSS 4

## 目录结构

```
├── public/                 # 静态资源
├── scripts/                # 构建与启动脚本
│   ├── build.sh            # 构建脚本
│   ├── dev.sh              # 开发环境启动脚本
│   ├── prepare.sh          # 预处理脚本
│   └── start.sh            # 生产环境启动脚本
├── src/
│   ├── app/                # 页面路由与布局
│   ├── components/ui/      # Shadcn UI 组件库
│   ├── hooks/              # 自定义 Hooks
│   ├── lib/                # 工具库
│   │   └── utils.ts        # 通用工具函数 (cn)
│   └── server.ts           # 自定义服务端入口
├── next.config.ts          # Next.js 配置
├── package.json            # 项目依赖管理
└── tsconfig.json           # TypeScript 配置
```

- 项目文件（如 app 目录、pages 目录、components 等）默认初始化到 `src/` 目录下。

## 包管理规范

**仅允许使用 pnpm** 作为包管理器，**严禁使用 npm 或 yarn**。
**常用命令**：
- 安装依赖：`pnpm add <package>`
- 安装开发依赖：`pnpm add -D <package>`
- 安装所有依赖：`pnpm install`
- 移除依赖：`pnpm remove <package>`

## 开发规范

### 编码规范

- 默认按 TypeScript `strict` 心智写代码；优先复用当前作用域已声明的变量、函数、类型和导入，禁止引用未声明标识符或拼错变量名。
- 禁止隐式 `any` 和 `as any`；函数参数、返回值、解构项、事件对象、`catch` 错误在使用前应有明确类型或先完成类型收窄，并清理未使用的变量和导入。

### next.config 配置规范

- 配置的路径不要写死绝对路径，必须使用 path.resolve(__dirname, ...)、import.meta.dirname 或 process.cwd() 动态拼接。

### Hydration 问题防范

1. 严禁在 JSX 渲染逻辑中直接使用 typeof window、Date.now()、Math.random() 等动态数据。**必须使用 'use client' 并配合 useEffect + useState 确保动态内容仅在客户端挂载后渲染**；同时严禁非法 HTML 嵌套（如 <p> 嵌套 <div>）。
2. **禁止使用 head 标签**，优先使用 metadata，详见文档：https://nextjs.org/docs/app/api-reference/functions/generate-metadata
   1. 三方 CSS、字体等资源可在 `globals.css` 中顶部通过 `@import` 引入或使用 next/font
   2. preload, preconnect, dns-prefetch 通过 ReactDOM 的 preload、preconnect、dns-prefetch 方法引入
   3. json-ld 可阅读 https://nextjs.org/docs/app/guides/json-ld

## UI 设计与组件规范 (UI & Styling Standards)

- 模板默认预装核心组件库 `shadcn/ui`，位于`src/components/ui/`目录下
- Next.js 项目**必须默认**采用 shadcn/ui 组件、风格和规范，**除非用户指定用其他的组件和规范。**

## CapLab 项目结构

### 产品定位
CapLab（Career Action Prototyping Lab）是面向大学生的 AI 生涯路径收敛平台。理念：不替学生做终身决定，而是用低成本现实行动验证选择。

### 页面路由
| 路由 | 文件 | 功能 |
|------|------|------|
| `/` | `src/app/page.tsx` | 开场首页（Hero + 三入口 + 五阶段） |
| `/chat` | `src/app/chat/page.tsx` | 对话工作台（对话流 + 阶段面板） |
| `/path-convergence` | `src/app/path-convergence/page.tsx` | 路径收敛（比较表 + 三分证据） |
| `/evidence-cycle` | `src/app/evidence-cycle/page.tsx` | 证据回合（三回合卡五要素） |
| `/resume` | `src/app/resume/page.tsx` | 简历工坊（JD + 证据矩阵 + A4预览） |
| `/interview` | `src/app/interview/page.tsx` | 模拟面试（追问对话 + 四维反馈） |
| `/review-report` | `src/app/review-report/page.tsx` | 复盘报告（回合核对 + 判断更新） |

### API 路由
| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/chat` | POST | 对话 API（接入 DeepSeek 官方 deepseek-flash（V4 Flash），OpenAI 兼容接口 SSE 流式输出；配置见 `.env.example`） |
| `/api/upload` | POST | 文件上传（PDF/Word/图片，含 OCR 提示） |
| `/api/knowledge` | POST | 知识库问答（免费版 v2.3.0） |

### 设计规范
- **主色**：墨松绿 `#0E6A5F`（primary）
- **背景**：暖纸白 `#F6F5F2`（background）
- **卡片**：纯白 `#FFFFFF`（card/surface）
- **容器**：`#EFEEE9`（muted/surface-container）
- **文字**：`#1C2321`（foreground）/ `#59635E`（muted-foreground）
- **功能色**：success `#1E8E5A` / error `#C83E33` / warning `#B57A0A`
- **字体**：Noto Sans SC + system-ui
- **阴影**：shadow-card / shadow-float / shadow-dialog（克制柔和）

### 知识库

统一使用**免费版 v2.3.0**，无 VIP/付费分层。界面显示"知识库版本：免费版 v2.3.0"。

**知识库构建规范**：详见 `docs/knowledge-base-skill.md`（CapLab-KB-Autopilot Skill v1.1）。

核心原则：
- 五层架构：导航层 → 实体层 → 证据层 → 治理层 → 运行层
- 原子事实原则：每条事实独立成 Claim，禁止推测
- 来源分级：A（原始官方）/ B（母内容可访问）/ C（机构摘要）/ D（用户生成内容）
- 12 道质量闸门（G01-G12）：脚本确定性 + LLM 语义 + 人工复核
- 增量更新：变更检测 → 更新队列 → 版本发布 → 异常待审
- 权限血缘：检索前过滤，免费版与付费版不复制两套事实数据

当前 `/api/knowledge` 为简化实现（基于免费版 xlsx 的关键词匹配），后续可按 Skill 规范升级为完整的五层架构 + 质量闸门 + 增量更新机制。
