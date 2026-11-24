'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  FlaskConical,
  GitMerge,
  CircleHelp,
  Scale,
  Ban,
  ArrowUpCircle,
  GitBranch,
  PauseCircle,
  XCircle,
  CheckCircle2,
  TimerReset,
  ArrowRight,
  Check,
  SlidersHorizontal,
  ArrowLeft,
  ScanSearch,
  CircleDot,
  ShieldCheck,
  Minus,
  Info,
  SearchCheck,
  Download,
} from 'lucide-react';

export default function PathConvergencePage() {
  const [accepted, setAccepted] = useState(false);

  const [weightsOpen, setWeightsOpen] = useState(false);
  const handleAdjustWeights = () => {
    setWeightsOpen((open) => !open);
  };

  const handleExport = () => {
    window.print();
  };

  const handleAccept = () => {
    setAccepted(true);
    console.log('结论标记 accepted，进入证据回合设计');
  };

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* 页面整体：左主结论区 + 右侧窄栏 */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* ============ 左侧主结论区 ============ */}
        <div className="flex-1 min-w-0 space-y-6">
          {/* 页头区 */}
          <section id="page-header" className="space-y-3">
            {/* 阶段标签 */}
            <span className="inline-flex items-center gap-1.5 bg-primary-container text-primary rounded-full px-3 py-1 text-xs font-medium">
              <GitMerge className="w-3.5 h-3.5" />
              阶段 3/5 · 路径收敛
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">路径比较与阶段性收敛</h1>
          </section>

          {/* 本轮决策问题卡 */}
          <section id="decision-question-card" className="bg-card shadow-card rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <CircleHelp className="w-4 h-4 text-primary" />
              <h2 className="text-base font-semibold text-foreground">本轮决策问题</h2>
            </div>
            <p id="decision-question-text" className="text-sm text-foreground leading-relaxed pl-6">
              2026 暑期实习投递前，优先准备 AI 产品实习、数据分析实习，还是考研？
            </p>
            <div className="pl-6 space-y-1.5 pt-1">
              <p className="text-xs text-muted-foreground flex items-start gap-1.5">
                <Scale className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                <span>比较依据：硬门槛 / 准备差距 / 现实成本 / 证据缺口</span>
              </p>
              <p className="text-xs text-muted-foreground flex items-start gap-1.5">
                <Ban className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                <span>你的权重：未指定（以下不替你发明价值排序，仅并列比较）</span>
              </p>
            </div>
          </section>

          {/* 路径比较表（核心组件） */}
          <section id="path-comparison-section" className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-foreground">四条路径并列比较</h2>
              <span className="text-xs text-muted-foreground hidden sm:inline">结论为阶段性，见下方有效期</span>
            </div>

            {/* 桌面表格 */}
            <div id="path-table" className="hidden md:block overflow-x-auto rounded-lg border border-border/50 bg-card shadow-card">
              <div className="min-w-[900px]">
              {/* 表头 */}
              <div className="grid grid-cols-[1.1fr_1.3fr_1.3fr_1.2fr_1.2fr_0.9fr] bg-muted px-4 py-3 gap-3">
                <span className="text-xs font-semibold text-muted-foreground">路径</span>
                <span className="text-xs font-semibold text-muted-foreground">硬门槛</span>
                <span className="text-xs font-semibold text-muted-foreground">我的准备差距</span>
                <span className="text-xs font-semibold text-muted-foreground">现实成本</span>
                <span className="text-xs font-semibold text-muted-foreground">证据缺口</span>
                <span className="text-xs font-semibold text-muted-foreground">当前归类</span>
              </div>

              <div className="divide-y divide-border/40">
                {/* 列表-路径1：AI 产品实习（主路径） */}
                <div id="path-row-ai-pm" className="grid grid-cols-[1.1fr_1.3fr_1.3fr_1.2fr_1.2fr_0.9fr] px-4 py-4 gap-3 relative hover:bg-muted/40 transition-colors">
                  <span className="absolute left-0 top-0 bottom-0 w-1 bg-primary"></span>
                  <div className="pl-2 flex flex-col gap-1.5">
                    <span className="text-sm font-semibold text-foreground">AI 产品实习</span>
                    <span className="inline-flex items-center w-fit px-2 py-0.5 rounded-sm text-xs font-medium bg-primary text-white">主路径</span>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    通常要求产品相关实习或可展示的产品分析/原型作品；强沟通与需求拆解
                    <span className="block text-xs mt-1 text-muted-foreground/80">注：要求因公司而异</span>
                  </p>
                  <p className="text-sm text-muted-foreground leading-relaxed">无正式产品实习；项目中需求整理为协作完成，独立贡献边界待证实</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">需在本地（不异地）找到岗位；每周 12h 可支撑作品集准备</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">是否能独立完成一次需求拆解并产出原型</p>
                  <div className="flex items-start">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-xs font-medium bg-primary/10 text-primary">
                      <ArrowUpCircle className="w-3 h-3" />优先准备
                    </span>
                  </div>
                </div>

                {/* 列表-路径2：数据分析实习（复合副路径） */}
                <div id="path-row-data" className="grid grid-cols-[1.1fr_1.3fr_1.3fr_1.2fr_1.2fr_0.9fr] px-4 py-4 gap-3 relative hover:bg-muted/40 transition-colors">
                  <span className="absolute left-0 top-0 bottom-0 w-1 bg-primary-container"></span>
                  <div className="pl-2 flex flex-col gap-1.5">
                    <span className="text-sm font-semibold text-foreground">数据分析实习</span>
                    <span className="inline-flex items-center w-fit px-2 py-0.5 rounded-sm text-xs font-medium bg-primary-container text-primary">副路径</span>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">SQL / Python 数据处理、可展示的分析项目</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    仅有 Titanic 教程跟做，缺独立项目；课程统计基础尚可
                    <span className="inline-flex items-center gap-1 align-middle text-[11px] text-warning bg-warning/10 px-1.5 py-px rounded-sm ml-1">
                      来源：成绩单截图，待确认
                    </span>
                  </p>
                  <p className="text-sm text-muted-foreground leading-relaxed">与产品准备在 SQL/分析能力上可复用</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">独立完成一份基于真实数据的分析报告</p>
                  <div className="flex items-start">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-xs font-medium bg-primary-container text-primary">
                      <GitBranch className="w-3 h-3" />复合并行
                    </span>
                  </div>
                </div>

                {/* 列表-路径3：考研（暂缓路径） */}
                <div id="path-row-kaoyan" className="grid grid-cols-[1.1fr_1.3fr_1.3fr_1.2fr_1.2fr_0.9fr] px-4 py-4 gap-3 relative hover:bg-muted/40 transition-colors">
                  <span className="absolute left-0 top-0 bottom-0 w-1 bg-warning"></span>
                  <div className="pl-2 flex flex-col gap-1.5">
                    <span className="text-sm font-semibold text-foreground">考研（计算机相关方向）</span>
                    <span className="inline-flex items-center w-fit px-2 py-0.5 rounded-sm text-xs font-medium bg-warning/15 text-warning">暂缓</span>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    固定考试时间线与长期稳定投入；报名/招生目录当年发布
                    <span className="inline-flex items-center gap-1 align-middle text-[11px] text-warning bg-warning/10 px-1.5 py-px rounded-sm ml-1">
                      <FlaskConical className="w-3 h-3" />待核验
                    </span>
                  </p>
                  <p className="text-sm text-muted-foreground leading-relaxed">每日稳定投入未经验证；复习节奏尚未开始</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">家庭仅支持 ≤6 个月、不支持 gap；与暑期实习时间窗口冲突</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">能否在一个月内保持每日有效复习（可先小规模验证）</p>
                  <div className="flex items-start">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-xs font-medium bg-warning/15 text-warning">
                      <PauseCircle className="w-3 h-3" />先验证
                    </span>
                  </div>
                </div>

                {/* 列表-路径4：直接 gap（排除路径） */}
                <div id="path-row-gap" className="grid grid-cols-[1.1fr_1.3fr_1.3fr_1.2fr_1.2fr_0.9fr] px-4 py-4 gap-3 relative hover:bg-muted/40 transition-colors">
                  <span className="absolute left-0 top-0 bottom-0 w-1 bg-destructive"></span>
                  <div className="pl-2 flex flex-col gap-1.5">
                    <span className="text-sm font-semibold text-foreground">直接 gap 一年再决定</span>
                    <span className="inline-flex items-center w-fit px-2 py-0.5 rounded-sm text-xs font-medium bg-destructive/15 text-destructive">排除</span>
                  </div>
                  <div className="col-span-4 text-sm text-muted-foreground leading-relaxed">
                    <p><span className="font-medium text-foreground">排除理由：</span>与硬约束冲突——家庭不支持 gap。</p>
                    <p className="mt-1.5"><span className="font-medium text-foreground">恢复条件：</span>若经济与家庭支持条件变化，可重新评估。</p>
                  </div>
                  <div className="flex items-start">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-xs font-medium bg-destructive/15 text-destructive">
                      <XCircle className="w-3 h-3" />当前排除
                    </span>
                  </div>
                </div>
              </div>
              </div>
            </div>

            {/* 移动端卡片列表（表格横向滚动替代） */}
            <div id="path-cards-mobile" className="md:hidden space-y-3">
              {/* 移动卡片-路径1：AI 产品实习 */}
              <div id="m-path-ai-pm" className="bg-card shadow-card rounded-lg overflow-hidden relative">
                <span className="absolute left-0 top-0 bottom-0 w-1 bg-primary"></span>
                <div className="pl-4 pr-4 py-3 flex items-center justify-between">
                  <span className="text-sm font-semibold text-foreground">AI 产品实习</span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-medium bg-primary text-white">主路径</span>
                </div>
                <div className="px-4 pb-4 space-y-2.5">
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">硬门槛：</span>通常要求产品相关实习或可展示的产品分析/原型作品；强沟通与需求拆解（要求因公司而异）</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">准备差距：</span>无正式产品实习；需求整理为协作完成，独立贡献边界待证实</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">现实成本：</span>需本地（不异地）岗位；每周 12h 可支撑作品集准备</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">证据缺口：</span>是否能独立完成一次需求拆解并产出原型</p>
                </div>
              </div>

              {/* 移动卡片-路径2：数据分析实习 */}
              <div id="m-path-data" className="bg-card shadow-card rounded-lg overflow-hidden relative">
                <span className="absolute left-0 top-0 bottom-0 w-1 bg-primary-container"></span>
                <div className="pl-4 pr-4 py-3 flex items-center justify-between">
                  <span className="text-sm font-semibold text-foreground">数据分析实习</span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-medium bg-primary-container text-primary">副路径</span>
                </div>
                <div className="px-4 pb-4 space-y-2.5">
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">硬门槛：</span>SQL / Python 数据处理、可展示的分析项目</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">准备差距：</span>仅有 Titanic 教程跟做，缺独立项目；统计基础尚可（成绩单截图，待确认）</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">现实成本：</span>与产品准备在 SQL/分析能力上可复用</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">证据缺口：</span>独立完成一份基于真实数据的分析报告</p>
                </div>
              </div>

              {/* 移动卡片-路径3：考研 */}
              <div id="m-path-kaoyan" className="bg-card shadow-card rounded-lg overflow-hidden relative">
                <span className="absolute left-0 top-0 bottom-0 w-1 bg-warning"></span>
                <div className="pl-4 pr-4 py-3 flex items-center justify-between">
                  <span className="text-sm font-semibold text-foreground">考研（计算机相关方向）</span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-medium bg-warning/15 text-warning">暂缓</span>
                </div>
                <div className="px-4 pb-4 space-y-2.5">
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">硬门槛：</span>固定考试时间线与长期稳定投入；报名/招生目录当年发布（待核验）</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">准备差距：</span>每日稳定投入未经验证；复习节奏尚未开始</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">现实成本：</span>家庭仅支持 ≤6 个月、不支持 gap；与暑期实习窗口冲突</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">证据缺口：</span>能否在一个月内保持每日有效复习（可小规模验证）</p>
                </div>
              </div>

              {/* 移动卡片-路径4：gap */}
              <div id="m-path-gap" className="bg-card shadow-card rounded-lg overflow-hidden relative">
                <span className="absolute left-0 top-0 bottom-0 w-1 bg-destructive"></span>
                <div className="pl-4 pr-4 py-3 flex items-center justify-between">
                  <span className="text-sm font-semibold text-foreground">直接 gap 一年再决定</span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-medium bg-destructive/15 text-destructive">排除</span>
                </div>
                <div className="px-4 pb-4 space-y-2.5">
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">排除理由：</span>与硬约束冲突——家庭不支持 gap。</p>
                  <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">恢复条件：</span>若经济与家庭支持条件变化，可重新评估。</p>
                </div>
              </div>
            </div>
          </section>

          {/* 证据三分卡 */}
          <section id="evidence-triptych" className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 支持证据 */}
            <div id="evidence-support-card" className="bg-card shadow-card rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-success" />
                <h3 className="text-sm font-semibold text-foreground">支持证据</h3>
              </div>
              <ul className="space-y-3">
                {/* 支持证据1 */}
                <li id="support-1" className="text-xs text-muted-foreground leading-relaxed pl-1">
                  <span className="flex items-start gap-1.5">
                    <span className="w-3.5 h-3.5 mt-0.5 shrink-0 text-success">•</span>
                    <span>访谈 2 位校友 PM 后仍主动保持兴趣
                      <span className="inline-flex items-center text-[10px] text-muted-foreground bg-muted px-1.5 py-px rounded-sm ml-1 align-middle">来源：用户陈述</span>
                    </span>
                  </span>
                </li>
                {/* 支持证据2 */}
                <li id="support-2" className="text-xs text-muted-foreground leading-relaxed pl-1">
                  <span className="flex items-start gap-1.5">
                    <span className="w-3.5 h-3.5 mt-0.5 shrink-0 text-success">•</span>
                    <span>在有明确反馈的任务上投入度更高
                      <span className="inline-flex items-center text-[10px] text-muted-foreground bg-muted px-1.5 py-px rounded-sm ml-1 align-middle">模型推断，已部分确认</span>
                    </span>
                  </span>
                </li>
                {/* 支持证据3 */}
                <li id="support-3" className="text-xs text-muted-foreground leading-relaxed pl-1">
                  <span className="flex items-start gap-1.5">
                    <span className="w-3.5 h-3.5 mt-0.5 shrink-0 text-success">•</span>
                    <span>小程序项目承担需求整理
                      <span className="inline-flex items-center text-[10px] text-muted-foreground bg-muted px-1.5 py-px rounded-sm ml-1 align-middle">来源：简历.pdf，协作边界已注明</span>
                    </span>
                  </span>
                </li>
              </ul>
            </div>

            {/* 反对证据 */}
            <div id="evidence-against-card" className="bg-card shadow-card rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2">
                <XCircle className="w-4 h-4 text-destructive" />
                <h3 className="text-sm font-semibold text-foreground">反对证据</h3>
              </div>
              <ul className="space-y-3">
                {/* 反对证据1 */}
                <li id="against-1" className="text-xs text-muted-foreground leading-relaxed pl-1">
                  <span className="flex items-start gap-1.5">
                    <span className="w-3.5 h-3.5 mt-0.5 shrink-0 text-destructive">•</span>
                    <span>无独立产品作品/实习，独立贡献边界未证实</span>
                  </span>
                </li>
                {/* 反对证据2 */}
                <li id="against-2" className="text-xs text-muted-foreground leading-relaxed pl-1">
                  <span className="flex items-start gap-1.5">
                    <span className="w-3.5 h-3.5 mt-0.5 shrink-0 text-destructive">•</span>
                    <span>兴趣可能受「体面感」影响
                      <span className="inline-flex items-center text-[10px] text-muted-foreground bg-muted px-1.5 py-px rounded-sm ml-1 align-middle">模型推断</span>
                    </span>
                  </span>
                </li>
                {/* 反对证据3 */}
                <li id="against-3" className="text-xs text-muted-foreground leading-relaxed pl-1">
                  <span className="flex items-start gap-1.5">
                    <span className="w-3.5 h-3.5 mt-0.5 shrink-0 text-destructive">•</span>
                    <span>Titanic 为教程跟做，不能作为独立数据分析能力证据</span>
                  </span>
                </li>
              </ul>
            </div>

            {/* 未知项 */}
            <div id="evidence-unknown-card" className="bg-card shadow-card rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2">
                <CircleHelp className="w-4 h-4 text-muted-foreground" />
                <h3 className="text-sm font-semibold text-foreground">未知项</h3>
              </div>
              <ul className="space-y-3">
                {/* 未知项1 */}
                <li id="unknown-1" className="text-xs text-muted-foreground leading-relaxed pl-1">
                  <span className="flex items-start gap-1.5">
                    <span className="w-3.5 h-3.5 mt-0.5 shrink-0 text-muted-foreground">•</span>
                    <span>本地可投递的产品/数据实习岗位数量与要求
                      <span className="inline-flex items-center gap-1 text-[10px] text-warning bg-warning/10 px-1.5 py-px rounded-sm ml-1 align-middle">
                        <FlaskConical className="w-2.5 h-2.5" />动态，待核验
                      </span>
                    </span>
                  </span>
                </li>
                {/* 未知项2 */}
                <li id="unknown-2" className="text-xs text-muted-foreground leading-relaxed pl-1">
                  <span className="flex items-start gap-1.5">
                    <span className="w-3.5 h-3.5 mt-0.5 shrink-0 text-muted-foreground">•</span>
                    <span>考研当年报名时间、招生目录与费用
                      <span className="inline-flex items-center gap-1 text-[10px] text-warning bg-warning/10 px-1.5 py-px rounded-sm ml-1 align-middle">
                        <FlaskConical className="w-2.5 h-2.5" />动态，待核验
                      </span>
                    </span>
                  </span>
                </li>
              </ul>
            </div>
          </section>

          {/* 会改变排序的新证据 / 有效期 */}
          <section id="revisit-triggers-card" className="bg-card shadow-card rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <TimerReset className="w-4 h-4 text-primary" />
              <h2 className="text-base font-semibold text-foreground">会改变排序的新证据 · 有效期</h2>
            </div>
            <p className="text-sm text-foreground leading-relaxed pl-6">
              本结论有效期：<span className="font-semibold text-primary">至 2026-03</span>（主攻方向决定点）；若以下新证据出现，排序可能改变：
            </p>
            <ul className="pl-6 space-y-2.5 pt-1">
              {/* 触发器1 */}
              <li id="trigger-1" className="text-sm text-muted-foreground leading-relaxed flex items-start gap-2">
                <ArrowRight className="w-3.5 h-3.5 mt-1 shrink-0 text-primary" />
                <span>独立完成一次需求拆解 + 原型并得到懂标准的人评价 <span className="text-foreground">→</span> 强化/削弱主路径</span>
              </li>
              {/* 触发器2 */}
              <li id="trigger-2" className="text-sm text-muted-foreground leading-relaxed flex items-start gap-2">
                <ArrowRight className="w-3.5 h-3.5 mt-1 shrink-0 text-primary" />
                <span>独立产出一份真实数据分析报告 <span className="text-foreground">→</span> 可能与副路径互换</span>
              </li>
              {/* 触发器3 */}
              <li id="trigger-3" className="text-sm text-muted-foreground leading-relaxed flex items-start gap-2">
                <ArrowRight className="w-3.5 h-3.5 mt-1 shrink-0 text-primary" />
                <span>连续 4 周每日复习可执行 <span className="text-foreground">→</span> 考研从暂缓上调</span>
              </li>
              {/* 触发器4 */}
              <li id="trigger-4" className="text-sm text-muted-foreground leading-relaxed flex items-start gap-2">
                <ArrowRight className="w-3.5 h-3.5 mt-1 shrink-0 text-primary" />
                <span>本地岗位池经核验明显偏小 <span className="text-foreground">→</span> 下调直接实习准备度</span>
              </li>
            </ul>
          </section>

          {/* 结论元信息行 */}
          <section id="conclusion-meta" className="flex flex-wrap items-center gap-3">
            <span id="badge-readiness" className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-primary-container text-primary">
              <FlaskConical className="w-3.5 h-3.5" />
              准备度：ready_for_low_cost_test（适合先做低成本验证）
            </span>
            <span id="badge-stability" className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">
              <ScanSearch className="w-3.5 h-3.5" />
              路径稳定度：medium
            </span>
          </section>

          {weightsOpen ? (
            <section id="weights-panel" className="bg-card shadow-card rounded-lg p-4 space-y-3">
              <h2 className="text-sm font-semibold">调整比较权重</h2>
              <p className="text-xs text-muted-foreground">
                CapLab 不预设价值排序。请在下方填写你自己认可的权重（0-10），保存后才参与排序；留空表示维持并列比较。
              </p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {['硬门槛', '准备差距', '现实成本', '证据缺口'].map((label) => (
                  <label key={label} className="text-xs text-muted-foreground">
                    {label}
                    <input
                      type="number"
                      min={0}
                      max={10}
                      placeholder="未指定"
                      className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm text-foreground"
                    />
                  </label>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setWeightsOpen(false)}
                className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
              >
                保存我的权重
              </button>
            </section>
          ) : null}

          {/* 底部操作区 */}
          <section id="action-area" className="bg-card shadow-card rounded-lg p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <div className="flex flex-col sm:flex-row gap-2.5 flex-1">
                <Link
                  href="/evidence-cycle"
                  onClick={handleAccept}
                  className="inline-flex items-center justify-center gap-2 bg-primary text-white px-4 py-2 rounded-md text-sm font-medium hover:opacity-90 active:scale-[0.98] transition-all"
                >
                  <Check className="w-4 h-4" />
                  接受这个阶段性结论
                </Link>
                <button
                  id="btn-adjust-weights"
                  type="button"
                  onClick={handleAdjustWeights}
                  className="inline-flex items-center justify-center gap-2 border border-border/30 text-foreground bg-transparent px-4 py-2 rounded-md text-sm font-medium hover:bg-muted transition-colors"
                >
                  <SlidersHorizontal className="w-4 h-4" />
                  调整比较权重
                </button>
                <Link
                  href="/chat"
                  className="inline-flex items-center justify-center gap-2 border border-border/30 text-foreground bg-transparent px-4 py-2 rounded-md text-sm font-medium hover:bg-muted transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  返回画像确认补充证据
                </Link>
              </div>
              <span className="text-xs text-muted-foreground sm:text-right whitespace-nowrap">确认后进入证据回合设计 →</span>
            </div>
            <p id="accept-hint" className="text-xs text-muted-foreground leading-relaxed">
              接受后结论才会被标记 accepted；你也可以保留未决定。沉默不算确认。
            </p>
          </section>
        </div>

        {/* ============ 右侧窄栏：关键缺口与版本信息 ============ */}
        <aside id="side-rail" className="lg:w-72 shrink-0 space-y-4">
          {/* 关键缺口速览 */}
          <div id="side-gap-card" className="bg-card shadow-card rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <ScanSearch className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">下一步关键缺口</h3>
            </div>
            <ul className="space-y-2.5">
              {/* 缺口1 */}
              <li id="side-gap-1" className="text-xs text-muted-foreground leading-relaxed flex items-start gap-1.5">
                <CircleDot className="w-3 h-3 mt-0.5 shrink-0 text-primary" />
                <span>独立完成一次需求拆解 + 原型（主路径决定性证据）</span>
              </li>
              {/* 缺口2 */}
              <li id="side-gap-2" className="text-xs text-muted-foreground leading-relaxed flex items-start gap-1.5">
                <CircleDot className="w-3 h-3 mt-0.5 shrink-0 text-primary" />
                <span>基于真实数据独立产出一份分析报告（副路径）</span>
              </li>
              {/* 缺口3 */}
              <li id="side-gap-3" className="text-xs text-muted-foreground leading-relaxed flex items-start gap-1.5">
                <CircleDot className="w-3 h-3 mt-0.5 shrink-0 text-warning" />
                <span>核验本地岗位池与考研当年政策
                  <span className="inline-flex items-center gap-1 text-[10px] text-warning bg-warning/10 px-1.5 py-px rounded-sm ml-1 align-middle">
                    <FlaskConical className="w-2.5 h-2.5" />待核验
                  </span>
                </span>
              </li>
            </ul>
          </div>

          {/* 纪律提醒 */}
          <div id="side-discipline-card" className="bg-card shadow-card rounded-lg p-4 space-y-2.5">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold text-foreground">本页遵守的纪律</h3>
            </div>
            <ul className="space-y-2">
              <li className="text-xs text-muted-foreground leading-relaxed flex items-start gap-1.5">
                <Minus className="w-3 h-3 mt-0.5 shrink-0" />
                <span>不用人格/兴趣标签直接决定路径</span>
              </li>
              <li className="text-xs text-muted-foreground leading-relaxed flex items-start gap-1.5">
                <Minus className="w-3 h-3 mt-0.5 shrink-0" />
                <span>不用星级、精确概率或无解释总分</span>
              </li>
              <li className="text-xs text-muted-foreground leading-relaxed flex items-start gap-1.5">
                <Minus className="w-3 h-3 mt-0.5 shrink-0" />
                <span>人物案例只说明「可能性」，不代表成功率</span>
              </li>
              <li className="text-xs text-muted-foreground leading-relaxed flex items-start gap-1.5">
                <Minus className="w-3 h-3 mt-0.5 shrink-0" />
                <span>结论阶段性有效，附有效期与改变条件</span>
              </li>
            </ul>
          </div>

          {/* 版本信息 */}
          <div id="side-version-card" className="bg-card shadow-card rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-muted-foreground" />
              <h3 className="text-sm font-semibold text-foreground">资料检索</h3>
            </div>
            <div className="space-y-1.5 text-xs text-muted-foreground">
              <p className="flex items-center gap-1.5">
                <SearchCheck className="w-3.5 h-3.5 shrink-0" />
                <span>检索模式：混合检索（本地规则库）</span>
              </p>
            </div>
            <button
              id="btn-export"
              type="button"
              onClick={handleExport}
              className="w-full inline-flex items-center justify-center gap-2 border border-border/30 text-foreground bg-transparent px-3 py-2 rounded-md text-xs font-medium hover:bg-muted transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              导出本页（PDF/打印）
            </button>
          </div>
        </aside>
      </div>
    </main>
  );
}
