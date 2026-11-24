'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  ClipboardCheck,
  ListChecks,
  CheckCircle2,
  FileText,
  MessageSquareQuote,
  HeartHandshake,
  TrendingUp,
  ShieldHalf,
  Lightbulb,
  PauseCircle,
  Dot,
  Square,
  CheckSquare,
  GitBranch,
  CircleDashed,
  ChevronRight,
  Columns3,
  Navigation,
  MousePointerClick,
  ArrowRight,
  ShieldCheck,
  FileBadge,
  RefreshCw,
  History,
  Download,
  FileJson,
  Trash2,
} from 'lucide-react';

export default function ReviewReportPage() {
  const [selectedRoute, setSelectedRoute] = useState('continue');

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* 页头 */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <span className="inline-flex items-center gap-1.5 bg-primary-container text-primary rounded-full px-3 py-1 text-xs font-medium">
            <ClipboardCheck className="w-3.5 h-3.5" />
            阶段 5/5 · 证据复盘
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight mb-2">
          证据复盘：什么新证据改变了哪层判断
        </h1>
        <p className="text-sm text-on-surface-variant">
          复盘服务于下一次选择。没有执行不等于懒惰，我们先还原发生了什么。
        </p>
      </div>

      {/* 桌面左右分栏：左侧复盘主体 flex-1，右侧 sticky 结论栏；移动堆叠 */}
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* ============ 左侧：复盘主体 ============ */}
        <div className="flex-1 min-w-0 space-y-6 w-full">
          {/* ===== 回合核对卡 ===== */}
          <section className="space-y-4" aria-labelledby="rounds-heading">
            <h2
              id="rounds-heading"
              className="text-base font-semibold flex items-center gap-2"
            >
              <ListChecks className="w-4 h-4 text-primary" />
              回合核对：先还原事实，再更新判断
            </h2>

            {/* 列表-回合卡1：回合1 completed */}
            <article
              id="round-card-1"
              className="bg-surface shadow-card rounded-xl p-5"
            >
              <div className="flex items-center justify-between gap-3 mb-4">
                <h3 className="text-sm font-semibold">
                  回合 1 · 需求拆解 + 低保真原型
                </h3>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-xs font-medium bg-success/15 text-success">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  completed
                </span>
              </div>

              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-xs text-on-surface-variant mb-1">
                    原判断
                  </dt>
                  <dd>我能否独立完成需求拆解并产出原型</dd>
                </div>
                <div>
                  <dt className="text-xs text-on-surface-variant mb-1">
                    实际发生
                  </dt>
                  <dd>
                    完成宿舍报修需求拆解文档 + 4 屏纸绘原型；1 位同班同学看过并提出 2 个问题；周日连续投入约 3 小时。
                  </dd>
                </div>
              </dl>

              {/* 证据条目 */}
              <div className="mt-4 space-y-2">
                {/* 证据1-产物 */}
                <div className="flex items-start gap-2 bg-surface-container rounded-md px-3 py-2 text-sm">
                  <FileText className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <span>
                      宿舍报修流程需求拆解文档 + 4 屏纸绘原型（含拍照存档）
                    </span>
                    <span className="ml-2 inline-block text-[10px] bg-primary/10 text-primary rounded px-1.5 py-0.5 align-middle">
                      用户带回产物
                    </span>
                  </div>
                </div>
                {/* 证据2-他人反馈 */}
                <div className="flex items-start gap-2 bg-surface-container rounded-md px-3 py-2 text-sm">
                  <MessageSquareQuote className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <span>同班 1 位同学阅读原型后提出 2 个问题</span>
                    <span className="ml-2 inline-block text-[10px] bg-primary/10 text-primary rounded px-1.5 py-0.5 align-middle">
                      用户带回产物
                    </span>
                  </div>
                </div>
                {/* 证据3-主观体验 */}
                <div className="flex items-start gap-2 bg-surface-container rounded-md px-3 py-2 text-sm">
                  <HeartHandshake className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <span>
                      主观体验：比预想更投入，周日下午一口气做了 3 小时，愿意再做一次
                    </span>
                  </div>
                </div>
              </div>

              {/* 证据判定 */}
              <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
                <span className="font-medium text-on-surface-variant">
                  证据判定：
                </span>
                <span className="inline-flex items-center gap-1 bg-success/15 text-success rounded px-2 py-0.5 font-medium">
                  <TrendingUp className="w-3 h-3" />
                  supports · 强化主路径
                </span>
                <span className="inline-flex items-center gap-1 bg-surface-container-high text-on-surface rounded px-2 py-0.5 font-medium">
                  <ShieldHalf className="w-3 h-3" />
                  可信度 medium
                </span>
                <span className="text-on-surface-variant">
                  理由：有真实产物 + 主动投入体验；但仅有同学反馈，缺少真实使用者验证。
                </span>
              </div>

              {/* 替代解释（必须出现） */}
              <div className="mt-3 flex items-start gap-2 rounded-md bg-warning/10 px-3 py-2.5 text-xs text-on-surface">
                <Lightbulb className="w-4 h-4 text-warning shrink-0 mt-0.5" />
                <p>
                  <span className="font-medium">替代解释：</span>
                  高投入也可能因为周末没有其他压力，而非任务本身的兴趣。
                  <span className="text-on-surface-variant">
                    → 建议下一轮接触真实报修使用者，以区分「任务兴趣」与「空闲带来的投入」。
                  </span>
                </p>
              </div>
            </article>

            {/* 列表-回合卡3：回合3 not_executed */}
            <article
              id="round-card-3"
              className="bg-surface shadow-card rounded-xl p-5"
            >
              <div className="flex items-center justify-between gap-3 mb-4">
                <h3 className="text-sm font-semibold">
                  回合 3 · 10 天每日复习 45 分钟节奏测试
                </h3>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-xs font-medium bg-warning/15 text-warning">
                  <PauseCircle className="w-3.5 h-3.5" />
                  not_executed（完成 3/10 天）
                </span>
              </div>

              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-xs text-on-surface-variant mb-1">
                    原判断
                  </dt>
                  <dd>能否连续 10 天每日复习 45 分钟</dd>
                </div>
                <div>
                  <dt className="text-xs text-on-surface-variant mb-1">
                    先还原事实（不接受「我太懒」的解释）
                  </dt>
                  <dd className="space-y-1.5">
                    <span className="flex items-start gap-2">
                      <Dot className="w-4 h-4 text-on-surface-variant shrink-0 mt-0.5" />
                      实际完成 3/10 天；
                    </span>
                    <span className="flex items-start gap-2">
                      <Dot className="w-4 h-4 text-on-surface-variant shrink-0 mt-0.5" />
                      第 2 天起期中论文与实验截止连续撞期（安排冲突）；
                    </span>
                    <span className="flex items-start gap-2">
                      <Dot className="w-4 h-4 text-on-surface-variant shrink-0 mt-0.5" />
                      原定早起时段与实际作息不符（任务设计 / 时间选择问题）；
                    </span>
                    <span className="flex items-start gap-2">
                      <Dot className="w-4 h-4 text-on-surface-variant shrink-0 mt-0.5" />
                      第 6 天空闲但不想开始——仅出现一次，不能据此判定失去兴趣。
                    </span>
                  </dd>
                </div>
              </dl>

              {/* 未执行原因（多选标签） */}
              <div className="mt-4">
                <div className="text-xs text-on-surface-variant mb-2">
                  未执行原因（可多选，按事实勾选）
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="inline-flex items-center gap-1 rounded-full border border-outline-variant/30 px-2.5 py-1 text-on-surface-variant">
                    <Square className="w-3 h-3" />
                    任务过大
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full border border-outline-variant/30 px-2.5 py-1 text-on-surface-variant">
                    <Square className="w-3 h-3" />
                    现实受阻
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary border border-primary/20 px-2.5 py-1 font-medium">
                    <CheckSquare className="w-3 h-3" />
                    安排冲突
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full border border-outline-variant/30 px-2.5 py-1 text-on-surface-variant">
                    <Square className="w-3 h-3" />
                    失去兴趣
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary border border-primary/20 px-2.5 py-1 font-medium">
                    <CheckSquare className="w-3 h-3" />
                    任务设计（时段不合理）
                  </span>
                </div>
                <p className="mt-2 text-xs text-on-surface-variant">
                  不归因于懒惰；「是否失去兴趣」证据不足（insufficient_evidence），单次不想开始不能据此否定考研方向。
                </p>
              </div>

              {/* 证据判定 */}
              <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
                <span className="font-medium text-on-surface-variant">
                  证据判定：
                </span>
                <span className="inline-flex items-center gap-1 bg-warning/15 text-warning rounded px-2 py-0.5 font-medium">
                  <GitBranch className="w-3 h-3" />
                  complicates · 让「暂缓考研」的信息更复杂，但不改变结论
                </span>
                <span className="inline-flex items-center gap-1 bg-surface-container-high text-on-surface rounded px-2 py-0.5 font-medium">
                  <ShieldHalf className="w-3 h-3" />
                  可信度 medium
                </span>
              </div>
            </article>

            {/* 列表-回合卡2：未开始（简卡，交代回合2状态） */}
            <article
              id="round-card-2"
              className="bg-surface shadow-card rounded-xl p-5 flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-xs font-medium bg-surface-container-high text-on-surface-variant">
                  <CircleDashed className="w-3.5 h-3.5" />
                  waiting
                </span>
                <div>
                  <h3 className="text-sm font-semibold">
                    回合 2 · 真实数据分析报告
                  </h3>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    未开始，本轮没有新证据；数据分析副路径仍为待验证缺口。
                  </p>
                </div>
              </div>
              <Link
                href="/evidence-cycle"
                id="link-round-2"
                className="shrink-0 text-xs font-medium text-primary hover:underline inline-flex items-center gap-1"
              >
                去安排<ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </article>
          </section>

          {/* ===== 判断更新对照表 ===== */}
          <section
            className="bg-surface shadow-card rounded-lg p-5"
            aria-labelledby="diff-heading"
          >
            <h2
              id="diff-heading"
              className="text-base font-semibold flex items-center gap-2 mb-4"
            >
              <Columns3 className="w-4 h-4 text-primary" />
              行动前 → 行动后，哪些字段变了
            </h2>
            <p className="text-xs text-on-surface-variant mb-4">
              规则：只更新被新证据触及的字段，准备度/稳定度调整必须有证据支撑；没有证据的字段明确标注「不变」。
            </p>

            <div className="overflow-x-auto">
              <div className="min-w-[640px] divide-y divide-outline-variant/50 text-sm">
                {/* 表头 */}
                <div className="grid grid-cols-4 gap-3 px-3 py-2.5 bg-surface-container text-xs font-semibold text-on-surface-variant rounded-t-md">
                  <span>判断层</span>
                  <span>行动前</span>
                  <span>新证据</span>
                  <span>现在</span>
                </div>
                {/* 对照行1：主路径 */}
                <div
                  id="diff-row-1"
                  className="grid grid-cols-4 gap-3 px-3 py-3 items-start"
                >
                  <span className="font-medium">主路径（AI 产品实习）</span>
                  <span className="text-on-surface-variant">可低成本测试</span>
                  <span className="text-on-surface-variant">
                    独立产出拆解 + 原型、主动投入
                  </span>
                  <span className="text-success font-medium">
                    维持主路径；准备度上调为 ready_to_pursue（限作品集维度）
                  </span>
                </div>
                {/* 对照行2：画像假设 */}
                <div
                  id="diff-row-2"
                  className="grid grid-cols-4 gap-3 px-3 py-3 items-start"
                >
                  <span className="font-medium">
                    画像假设「兴趣受体面感影响」
                  </span>
                  <span className="text-on-surface-variant">模型推断</span>
                  <span className="text-on-surface-variant">
                    在无观众压力下仍投入 3 小时
                  </span>
                  <span className="text-warning font-medium">
                    部分削弱（仍需真实使用者验证）
                  </span>
                </div>
                {/* 对照行3：考研 */}
                <div
                  id="diff-row-3"
                  className="grid grid-cols-4 gap-3 px-3 py-3 items-start"
                >
                  <span className="font-medium">考研（暂缓）</span>
                  <span className="text-on-surface-variant">
                    稳定投入未知
                  </span>
                  <span className="text-on-surface-variant">
                    3/10 天，以安排冲突为主
                  </span>
                  <span className="text-on-surface font-medium">
                    维持暂缓；改为固定晚间时段再做一次 7 天小测
                  </span>
                </div>
                {/* 对照行4：副路径 */}
                <div
                  id="diff-row-4"
                  className="grid grid-cols-4 gap-3 px-3 py-3 items-start"
                >
                  <span className="font-medium">副路径：数据分析</span>
                  <span className="text-on-surface-variant">—</span>
                  <span className="text-on-surface-variant">回合 2 未做</span>
                  <span className="text-on-surface-variant">
                    仍为缺口，保留，不做判断更新
                  </span>
                </div>
              </div>
            </div>
            <p className="mt-3 text-xs text-on-surface-variant">
              未被触及的字段（如异地意愿、家庭约束等）保持原值，不因一次结果定终身。
            </p>
          </section>

          {/* ===== 最小下一步 & 路由卡 ===== */}
          <section
            className="bg-primary-container/40 rounded-lg p-5"
            aria-labelledby="next-heading"
          >
            <h2
              id="next-heading"
              className="text-base font-semibold flex items-center gap-2 mb-1"
            >
              <Navigation className="w-4 h-4 text-primary" />
              下一步（四选一）
            </h2>
            <p className="text-xs text-on-surface-variant mb-4">
              每个选择都是低成本、可退出的；等待不是失败，也可以先暂停。
            </p>

            <div id="route-options" className="space-y-2.5">
              {/* 选项1（当前推荐，默认选中） */}
              <label
                id="route-option-1"
                htmlFor="route-radio-1"
                className={`route-option flex items-start gap-3 rounded-lg bg-surface shadow-card p-4 cursor-pointer border-2 ${
                  selectedRoute === 'continue'
                    ? 'border-primary'
                    : 'border-transparent'
                }`}
              >
                <input
                  type="radio"
                  name="route"
                  id="route-radio-1"
                  value="continue"
                  className="mt-0.5 accent-primary"
                  checked={selectedRoute === 'continue'}
                  onChange={() => setSelectedRoute('continue')}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">
                      继续主路径：验证真实使用者
                    </span>
                    <span className="inline-flex items-center text-[10px] bg-primary/10 text-primary rounded px-1.5 py-0.5 font-medium">
                      推荐
                    </span>
                  </div>
                  <p className="text-xs text-on-surface-variant mt-1">
                    下一轮拿 4 屏原型找 1 位真实宿管或有报修经历的学生验证，仍低成本、不异地。
                  </p>
                </div>
              </label>
              {/* 选项2 */}
              <label
                id="route-option-2"
                htmlFor="route-radio-2"
                className={`route-option flex items-start gap-3 rounded-lg bg-surface shadow-card p-4 cursor-pointer border-2 ${
                  selectedRoute === 'redesign'
                    ? 'border-primary'
                    : 'border-transparent'
                }`}
              >
                <input
                  type="radio"
                  name="route"
                  id="route-radio-2"
                  value="redesign"
                  className="mt-0.5 accent-primary"
                  checked={selectedRoute === 'redesign'}
                  onChange={() => setSelectedRoute('redesign')}
                />
                <div className="flex-1">
                  <span className="text-sm font-semibold">
                    重设计考研节奏测试
                  </span>
                  <p className="text-xs text-on-surface-variant mt-1">
                    固定晚间时段、周期缩短为 7 天、时长降到 30 分钟，排除时段不合理这一干扰。
                  </p>
                </div>
              </label>
              {/* 选项3 */}
              <label
                id="route-option-3"
                htmlFor="route-radio-3"
                className={`route-option flex items-start gap-3 rounded-lg bg-surface shadow-card p-4 cursor-pointer border-2 ${
                  selectedRoute === 'round2'
                    ? 'border-primary'
                    : 'border-transparent'
                }`}
              >
                <input
                  type="radio"
                  name="route"
                  id="route-radio-3"
                  value="round2"
                  className="mt-0.5 accent-primary"
                  checked={selectedRoute === 'round2'}
                  onChange={() => setSelectedRoute('round2')}
                />
                <div className="flex-1">
                  <span className="text-sm font-semibold">
                    开始回合 2：真实数据分析报告
                  </span>
                  <p className="text-xs text-on-surface-variant mt-1">
                    补上副路径缺口，用一份小报告检验数据清洗与分析的实际投入感。
                  </p>
                </div>
              </label>
              {/* 选项4 */}
              <label
                id="route-option-4"
                htmlFor="route-radio-4"
                className={`route-option flex items-start gap-3 rounded-lg bg-surface shadow-card p-4 cursor-pointer border-2 ${
                  selectedRoute === 'pause'
                    ? 'border-primary'
                    : 'border-transparent'
                }`}
              >
                <input
                  type="radio"
                  name="route"
                  id="route-radio-4"
                  value="pause"
                  className="mt-0.5 accent-primary"
                  checked={selectedRoute === 'pause'}
                  onChange={() => setSelectedRoute('pause')}
                />
                <div className="flex-1">
                  <span className="text-sm font-semibold">暂停 / 关闭本轮</span>
                  <p className="text-xs text-on-surface-variant mt-1">
                    保存现状，之后随时继续，不强制循环；已确认结论在有效期内保留。
                  </p>
                </div>
              </label>
            </div>

            {/* 立即的小动作 */}
            <div className="mt-4 flex items-start gap-2 rounded-md bg-surface px-3 py-2.5 text-xs text-on-surface-variant border border-outline-variant/20">
              <MousePointerClick className="w-4 h-4 text-primary shrink-0 mt-0.5" />
              <p>
                <span className="font-medium text-on-surface">
                  立即的小动作：
                </span>
                明天把原型照片发给 1 位符合真实使用者画像的人（宿管 / 近期报修过的学生）。是否发送由你决定，我不代发。
              </p>
            </div>

            {/* 路由按钮 */}
            <div className="mt-4 flex flex-wrap gap-3">
              <Link
                href="/evidence-cycle"
                id="btn-continue"
                className="bg-primary text-on-primary px-4 py-2 rounded-md text-sm font-medium hover:opacity-90 active:scale-[0.98] transition-all inline-flex items-center gap-2"
              >
                <ArrowRight className="w-3.5 h-3.5" />
                按此继续
              </Link>
              <Link
                href="/path-convergence"
                id="btn-back-convergence"
                className="px-4 py-2 rounded-md text-sm font-medium border border-outline-variant/30 text-on-surface hover:bg-surface transition-all inline-flex items-center gap-2"
              >
                返回路径收敛
              </Link>
              <Link
                href="/chat"
                id="btn-back-workbench"
                className="px-4 py-2 rounded-md text-sm font-medium border border-outline-variant/30 text-on-surface hover:bg-surface transition-all inline-flex items-center gap-2"
              >
                回到工作台
              </Link>
            </div>
          </section>

          {/* ===== 数据与隐私小卡 ===== */}
          <section
            id="privacy-card"
            className="bg-surface rounded-lg p-4 border border-outline-variant/20"
          >
            <div className="flex items-start gap-3">
              <ShieldCheck className="w-5 h-5 text-primary shrink-0 mt-0.5" />
              <p className="text-xs text-on-surface-variant leading-relaxed">
                CapLab 不主动索要身份证号等无关隐私，你可随时导出或删除数据。若你此刻有伤害自己或他人的念头或面临即时危险，请先停止生涯讨论，联系一位可信任的人、学校心理中心或紧急求助——你不必独自承受。
              </p>
            </div>
          </section>
        </div>

        {/* ============ 右侧：sticky 结论栏（移动端堆叠在底部） ============ */}
        <aside className="w-full lg:w-80 shrink-0 lg:sticky lg:top-20">
          <div className="bg-surface shadow-card rounded-lg p-4 space-y-3">
            <h2 className="text-sm font-semibold flex items-center gap-2">
              <FileBadge className="w-4 h-4 text-primary" />
              本轮报告结论
            </h2>

            <div className="space-y-2.5 text-xs divide-y divide-outline-variant/40">
              <div className="flex items-start justify-between gap-3 pt-1">
                <span className="text-on-surface-variant shrink-0">
                  结论有效期
                </span>
                <span className="text-on-surface font-medium text-right">
                  至 2026-03
                </span>
              </div>
              <div className="flex items-start gap-2 pt-2.5">
                <RefreshCw className="w-3.5 h-3.5 text-on-surface-variant shrink-0 mt-0.5" />
                <span className="text-on-surface-variant">
                  跨会话延续：已确认内容会保留，未确认项保持草稿。
                </span>
              </div>
              <div className="flex items-start gap-2 pt-2.5">
                <History className="w-3.5 h-3.5 text-on-surface-variant shrink-0 mt-0.5" />
                <span className="text-on-surface-variant">
                  若你纠正早期事实：将回到最早受影响阶段重新核验。
                </span>
              </div>
            </div>

            <div className="pt-1 space-y-2">
              {/* 生成报告 / 导出（静态行为，原型仅注释说明） */}
              <button
                type="button"
                id="btn-export-pdf"
                className="w-full bg-primary text-on-primary px-3 py-2 rounded-md text-sm font-medium hover:opacity-90 active:scale-[0.98] transition-all inline-flex items-center justify-center gap-2"
                onClick={() =>
                  console.log(
                    '导出复盘报告（PDF/打印）：原型静态行为，后续接入打印/PDF 生成'
                  )
                }
              >
                <Download className="w-4 h-4" />
                生成报告 / 导出（PDF/打印）
              </button>
              {/* 导出我的数据 */}
              <button
                type="button"
                id="btn-export-json"
                className="w-full px-3 py-2 rounded-md text-sm font-medium border border-outline-variant/30 text-on-surface hover:bg-surface-container transition-all inline-flex items-center justify-center gap-2"
                onClick={() =>
                  console.log('导出我的数据 JSON：原型静态行为，后续生成 Blob 下载')
                }
              >
                <FileJson className="w-4 h-4" />
                导出我的数据 (JSON)
              </button>
              {/* 删除我的数据 */}
              <button
                type="button"
                id="btn-delete-data"
                className="w-full px-3 py-2 rounded-md text-sm font-medium text-error hover:bg-error/10 transition-all inline-flex items-center justify-center gap-2"
                onClick={() =>
                  console.log('删除我的数据：需二次确认后调用删除接口')
                }
              >
                <Trash2 className="w-4 h-4" />
                删除我的数据
              </button>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
