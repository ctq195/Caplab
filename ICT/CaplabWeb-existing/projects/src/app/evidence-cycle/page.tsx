'use client';

import { useState } from 'react';
import {
  FlaskConical,
  Gauge,
  CalendarClock,
  Crosshair,
  Package,
  ClipboardCheck,
  Clock,
  LifeBuoy,
  Zap,
  Hourglass,
  OctagonX,
  Sparkles,
  PenTool,
  BarChart3,
  Repeat,
  Layers,
  Puzzle,
  ShieldCheck,
  Check,
  ArrowRight,
  ArrowLeft,
} from 'lucide-react';

export default function EvidenceCyclePage() {
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null);

  const handleSelectCycle = (cycleNum: number) => {
    setSelectedCycle(cycleNum);
  };

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
      {/* 页头 */}
      <section id="page-header" className="space-y-3">
        <span className="inline-flex items-center gap-1.5 bg-primary-container text-primary rounded-full px-3 py-1 text-xs font-medium">
          <FlaskConical className="w-3.5 h-3.5" />
          阶段 4/5 · 证据回合
        </span>
        <h1 className="text-2xl font-bold tracking-tight">把关键疑问，做成低成本现实回合</h1>
        <p className="text-sm text-on-surface-variant leading-relaxed max-w-2xl">
          每个回合只验证一个判断，失败也会留下信息。选择一个回合先开始，不必一次走完。
        </p>
      </section>

      {/* 要改变的路径判断 摘要条 */}
      <section id="gap-summary" className="bg-surface shadow-card rounded-lg p-4 mt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <span className="shrink-0 mt-0.5 inline-flex items-center justify-center bg-primary/10 text-primary text-[11px] font-bold rounded-sm px-1.5 py-0.5">G1</span>
          <p className="text-sm leading-relaxed">
            <span className="text-on-surface-variant">当前最关键缺口：</span>
            <span className="font-medium">我是否能独立完成需求拆解并产出原型</span>
            <span className="text-on-surface-variant">（对应主路径 AI 产品实习）</span>
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0 flex-wrap sm:justify-end">
          <span className="inline-flex items-center gap-1 bg-surface-container text-on-surface-variant rounded-sm px-2 py-0.5 text-xs font-medium">
            <Gauge className="w-3 h-3" />准备度：ready_for_low_cost_test
          </span>
          <span className="inline-flex items-center gap-1 bg-surface-container text-on-surface-variant rounded-sm px-2 py-0.5 text-xs font-medium">
            <CalendarClock className="w-3 h-3" />每周可用：约 12h
          </span>
        </div>
      </section>

      {/* 主体：左回合卡 + 右 sticky 概要栏 */}
      <div className="flex flex-col lg:flex-row gap-6 mt-8 items-start">
        {/* 左侧：回合卡列表 */}
        <div id="cycle-list" className="flex-1 min-w-0 space-y-5 w-full">
          {/* 回合 1：微型作品（推荐） */}
          <article
            id="cycle-card-1"
            className={`bg-surface shadow-card rounded-xl p-5 border ${
              selectedCycle === 1 ? 'border-primary ring-2 ring-primary/40' : 'border-primary ring-1 ring-primary/20'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="text-sm font-bold text-primary">回合 1</span>
                <span className="inline-flex items-center gap-1 bg-primary text-on-primary text-[11px] font-medium rounded-full px-2 py-0.5">
                  <Sparkles className="w-3 h-3" />建议先做
                </span>
              </div>
              <span className="inline-flex items-center gap-1 text-xs text-on-surface-variant shrink-0">
                <PenTool className="w-3.5 h-3.5" />微型作品
              </span>
            </div>
            <h2 className="text-base font-semibold mt-2">独立需求拆解 + 低保真原型</h2>
            <p className="text-xs text-on-surface-variant mt-1">对应缺口 G1 · 最可能改变主路径「AI 产品实习」的归类</p>

            {/* 五要素清单 */}
            <ul className="mt-4 space-y-3.5">
              {/* 要素-目的 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-primary/10 text-primary flex items-center justify-center">
                  <Crosshair className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">目的 · 要验证的可证伪判断</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">验证在没有学长代劳后端的情况下，我能否独立把一个真实小需求拆解清楚并产出可讲解的低保真原型（可证伪：不是只停留在“我有个产品想法“）</p>
                </div>
              </li>
              {/* 要素-产物 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <Package className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">需保留的产物</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">1 份需求拆解文档（用户、场景、问题、方案取舍各一页内）+ 1 个 3-5 屏低保真原型（纸笔拍照或免费原型工具均可）</p>
                </div>
              </li>
              {/* 要素-验收标准 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <ClipboardCheck className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">验收标准</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">覆盖至少 1 个真实使用者与 1 个具体场景；写出 1 个被放弃的方案及原因；能向他人讲清每个页面解决什么问题（不要求对方认可）</p>
                </div>
              </li>
              {/* 要素-时间投入 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <Clock className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">预计时间投入</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">总计 6-8 小时，拆成 3 次、每次 2 小时左右，本周内可开始</p>
                </div>
              </li>
              {/* 要素-失败调整 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <LifeBuoy className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">失败后如何调整</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">若卡住：降级为只拆解一个功能点；若两次后仍无法推进或持续抗拒记录感受——这本身是关于任务规模或偏好的证据，复盘时重新设计，不归因懒惰</p>
                </div>
              </li>
            </ul>

            {/* 立即下一步 / 等待 / 停止 */}
            <div className="mt-4 space-y-2">
              <div className="flex items-start gap-2 bg-primary/10 text-primary rounded-md px-3 py-2">
                <Zap className="w-4 h-4 mt-0.5 shrink-0" />
                <p className="text-xs leading-relaxed"><span className="font-bold">立即下一步：</span>今晚定一个你自己每天都会遇到的小问题作为题目（不替你联系任何人）</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-1.5 text-xs text-on-surface-variant bg-surface-container rounded-sm px-2.5 py-1">
                  <Hourglass className="w-3.5 h-3.5" />等待条件：—
                </span>
                <span className="inline-flex items-center gap-1.5 text-xs text-on-surface-variant bg-surface-container rounded-sm px-2.5 py-1">
                  <OctagonX className="w-3.5 h-3.5" />停止条件：单次超过 3h 仍无进展即停，先复盘
                </span>
              </div>
            </div>
          </article>

          {/* 回合 2：真实反馈 + 微型分析 */}
          <article
            id="cycle-card-2"
            className={`bg-surface shadow-card rounded-xl p-5 border ${
              selectedCycle === 2 ? 'border-primary ring-2 ring-primary/40' : 'border-outline-variant/30'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <span className="text-sm font-bold text-on-surface">回合 2</span>
              <span className="inline-flex items-center gap-1 text-xs text-on-surface-variant shrink-0">
                <BarChart3 className="w-3.5 h-3.5" />真实反馈 + 微型分析
              </span>
            </div>
            <h2 className="text-base font-semibold mt-2">用真实数据走完一次分析闭环</h2>
            <p className="text-xs text-on-surface-variant mt-1">对应缺口 G2 · 独立产出一份基于真实数据的分析报告</p>

            {/* 五要素清单 */}
            <ul className="mt-4 space-y-3.5">
              {/* 要素-目的 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-primary/10 text-primary flex items-center justify-center">
                  <Crosshair className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">目的 · 要验证的可证伪判断</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">验证我能否用真实数据独立走完一次“提问—清洗—分析—结论“，而不是复现教程</p>
                </div>
              </li>
              {/* 要素-产物 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <Package className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">需保留的产物</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">1 份基于公开真实数据集（或校内可获得数据）的分析报告，含 1 张图表和 1 条可执行建议；注明哪些步骤查过教程</p>
                </div>
              </li>
              {/* 要素-验收标准 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <ClipboardCheck className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">验收标准</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">问题由自己提出；数据来源与时间可写清；结论能被一位懂数据的人提问（可请课程老师/学长，是否约得到由你决定）</p>
                </div>
              </li>
              {/* 要素-时间投入 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <Clock className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">预计时间投入</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">8-10 小时，分 4 次</p>
                </div>
              </li>
              {/* 要素-失败调整 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <LifeBuoy className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">失败后如何调整</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">约不到反馈者 → 转为公开社区发帖或只完成自评，“无回复”不计为路径不成立；数据清洗过重 → 缩小数据集</p>
                </div>
              </li>
            </ul>

            {/* 立即下一步 / 停止 */}
            <div className="mt-4 space-y-2">
              <div className="flex items-start gap-2 bg-primary/10 text-primary rounded-md px-3 py-2">
                <Zap className="w-4 h-4 mt-0.5 shrink-0" />
                <p className="text-xs leading-relaxed"><span className="font-bold">立即下一步：</span>选定数据集并写下你的分析问题（一句话）</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-1.5 text-xs text-on-surface-variant bg-surface-container rounded-sm px-2.5 py-1">
                  <OctagonX className="w-3.5 h-3.5" />停止条件：连续两周无整块时间 → 回复盘重排规模
                </span>
              </div>
            </div>
          </article>

          {/* 回合 3：约束测试 */}
          <article
            id="cycle-card-3"
            className={`bg-surface shadow-card rounded-xl p-5 border ${
              selectedCycle === 3 ? 'border-primary ring-2 ring-primary/40' : 'border-outline-variant/30'
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <span className="text-sm font-bold text-on-surface">回合 3</span>
              <span className="inline-flex items-center gap-1 text-xs text-on-surface-variant shrink-0">
                <Repeat className="w-3.5 h-3.5" />约束测试
              </span>
            </div>
            <h2 className="text-base font-semibold mt-2">小规模复习节奏测试（连续 10 天）</h2>
            <p className="text-xs text-on-surface-variant mt-1">对应缺口 G3 · 考研暂缓项能否重新评估的关键前提</p>

            {/* 五要素清单 */}
            <ul className="mt-4 space-y-3.5">
              {/* 要素-目的 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-primary/10 text-primary flex items-center justify-center">
                  <Crosshair className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">目的 · 要验证的可证伪判断</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">验证我能否保持稳定每日复习（考研暂缓项的关键前提），而不是验证“我能不能考上“</p>
                </div>
              </li>
              {/* 要素-产物 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <Package className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">需保留的产物</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">连续 10 天的复习记录（每天实际时长 + 当日最难开始的时刻，一行即可）</p>
                </div>
              </li>
              {/* 要素-验收标准 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <ClipboardCheck className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">验收标准</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">10 天中至少 7 天完成 45 分钟；记录中断当天的现实原因（事件，不写自我评价）</p>
                </div>
              </li>
              {/* 要素-时间投入 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <Clock className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">预计时间投入</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">每天 45 分钟，共 10 天</p>
                </div>
              </li>
              {/* 要素-失败调整 */}
              <li className="flex items-start gap-3">
                <span className="shrink-0 w-7 h-7 rounded-md bg-surface-container-high text-on-surface-variant flex items-center justify-center">
                  <LifeBuoy className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold text-on-surface">失败后如何调整</p>
                  <p className="text-sm text-on-surface-variant leading-relaxed mt-0.5">若低于 7 天：区分任务过大/现实受阻/安排冲突/失去兴趣四种原因后再判断，不据此否定考研或否定自己；可改为固定时段测试</p>
                </div>
              </li>
            </ul>

            {/* 立即下一步 / 停止 */}
            <div className="mt-4 space-y-2">
              <div className="flex items-start gap-2 bg-primary/10 text-primary rounded-md px-3 py-2">
                <Zap className="w-4 h-4 mt-0.5 shrink-0" />
                <p className="text-xs leading-relaxed"><span className="font-bold">立即下一步：</span>在日历上圈出明天的 45 分钟</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-1.5 text-xs text-on-surface-variant bg-surface-container rounded-sm px-2.5 py-1">
                  <OctagonX className="w-3.5 h-3.5" />停止条件：身体或课业出现明显冲突即停
                </span>
              </div>
            </div>
          </article>

          {/* 回合选择区 */}
          <section id="cycle-selector" className="bg-surface-container rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <p className="text-sm font-medium">选择一个回合先做（选择后才会标记）：</p>
            <div className="flex flex-wrap items-center gap-2">
              <button
                id="btn-select-cycle-1"
                onClick={() => handleSelectCycle(1)}
                className={`${
                  selectedCycle === 1
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface text-on-surface border border-outline-variant/30 hover:bg-surface-container-high'
                } px-4 py-2 rounded-md text-sm font-medium active:scale-[0.98] transition-all inline-flex items-center gap-2`}
              >
                {selectedCycle === 1 && <Check className="w-3.5 h-3.5" />}
                先做回合 1
              </button>
              <button
                id="btn-select-cycle-2"
                onClick={() => handleSelectCycle(2)}
                className={`${
                  selectedCycle === 2
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface text-on-surface border border-outline-variant/30 hover:bg-surface-container-high'
                } px-4 py-2 rounded-md text-sm font-medium active:scale-[0.98] transition-all inline-flex items-center gap-2`}
              >
                {selectedCycle === 2 && <Check className="w-3.5 h-3.5" />}
                先做回合 2
              </button>
              <button
                id="btn-select-cycle-3"
                onClick={() => handleSelectCycle(3)}
                className={`${
                  selectedCycle === 3
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface text-on-surface border border-outline-variant/30 hover:bg-surface-container-high'
                } px-4 py-2 rounded-md text-sm font-medium active:scale-[0.98] transition-all inline-flex items-center gap-2`}
              >
                {selectedCycle === 3 && <Check className="w-3.5 h-3.5" />}
                先做回合 3
              </button>
            </div>
            <p className="text-xs text-on-surface-variant sm:basis-full sm:pt-1">你也可以说：这些都太大 / 这周没时间——我们会据此缩小回合，而不是催你。</p>
          </section>
        </div>

        {/* 右侧 sticky 概要栏 */}
        <aside id="cycle-sidebar" className="w-full lg:w-72 shrink-0 lg:sticky lg:top-24 space-y-4">
          <div className="bg-surface shadow-card rounded-lg p-4 space-y-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary" />回合设计概要
            </h3>
            <div className="space-y-2.5">
              <div className="flex items-start gap-2">
                <Puzzle className="w-3.5 h-3.5 text-on-surface-variant mt-0.5 shrink-0" />
                <p className="text-xs text-on-surface-variant leading-relaxed"><span className="font-medium text-on-surface">回合互补性：</span>作品（回合1）/ 真实数据+反馈（回合2）/ 自我节奏约束（回合3），三类证据不重复</p>
              </div>
              <div className="flex items-start gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-on-surface-variant mt-0.5 shrink-0" />
                <p className="text-xs text-on-surface-variant leading-relaxed"><span className="font-medium text-on-surface">授权边界：</span>CapLab 只设计并记录计划，不会替你发送消息、报名、购买或公开发布</p>
              </div>
            </div>
          </div>

          <div className="bg-surface shadow-card rounded-lg p-4 space-y-2">
            <a
              id="link-go-review"
              href="/review-report"
              className="w-full bg-primary text-on-primary px-3 py-2 rounded-md text-sm font-medium hover:opacity-90 active:scale-[0.98] transition-all inline-flex items-center justify-center gap-1.5"
            >
              带着结果去复盘<ArrowRight className="w-3.5 h-3.5" />
            </a>
            <a
              id="link-back-paths"
              href="/path-convergence"
              className="w-full bg-surface-container text-on-surface px-3 py-2 rounded-md text-sm font-medium hover:bg-surface-container-high active:scale-[0.98] transition-all inline-flex items-center justify-center gap-1.5"
            >
              <ArrowLeft className="w-3.5 h-3.5" />返回路径比较
            </a>
          </div>
        </aside>
      </div>
    </main>
  );
}
