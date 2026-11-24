'use client';

import Link from 'next/link';
import { STAGES } from '@/lib/site-config';
import {
  ClipboardList,
  FileText,
  Image as ImageIcon,
  CheckCircle2,
  Lightbulb,
  ArrowRight,
  Download,
  Trash2,
} from 'lucide-react';

interface StagePanelProps {
  currentStage: number; // 1-5
  pendingCount: number;
  onExport: () => void;
  onDelete: () => void;
}

export function StagePanel({ currentStage, pendingCount, onExport, onDelete }: StagePanelProps) {
  return (
    <div className="space-y-5">
      {/* 五阶段步骤条 */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-foreground">阶段进度</h2>
        <ol>
          {STAGES.map((s, idx) => {
            const stageNo = idx + 1;
            const isActive = stageNo === currentStage;
            const isDone = stageNo < currentStage;
            const isLast = stageNo === STAGES.length;
            return (
              <li key={s.short} className="relative flex gap-3 pb-4">
                <span className="flex flex-col items-center">
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-[11px] ${
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : isDone
                          ? 'bg-primary/20 text-primary'
                          : 'border border-border bg-card text-muted-foreground/50'
                    }`}
                  >
                    {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : stageNo}
                  </span>
                  {!isLast && <span className="w-px flex-1 bg-border/40 mt-1" />}
                </span>
                <div className="-mt-0.5">
                  <Link
                    href={s.href}
                    className={`text-sm hover:text-primary ${
                      isActive
                        ? 'font-semibold text-primary'
                        : isDone
                          ? 'font-medium text-foreground'
                          : 'font-medium text-muted-foreground/60'
                    }`}
                  >
                    {s.short}
                  </Link>
                  <p className="text-[11px] text-muted-foreground/40 mt-0.5">
                    {isActive && pendingCount > 0 ? `${pendingCount} 项待确认` : s.full}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      {/* 说明 */}
      <div className="rounded-xl border border-border/50 bg-muted/50 p-3.5 text-[11px] leading-relaxed text-muted-foreground space-y-1.5">
        <p className="flex items-center gap-1.5 text-foreground font-medium">
          <ClipboardList className="w-3.5 h-3.5 text-primary" />
          三分呈现
        </p>
        <p>对话中会区分：已确认事实 / 模型推断（明确标注）/ 待核验未知。未确认内容只保持草稿。</p>
      </div>

      {/* 已确认事实提示 */}
      <div className="space-y-2.5">
        <h2 className="text-sm font-semibold text-foreground">工作方式</h2>
        <ul className="space-y-2 text-xs text-foreground">
          <li className="flex items-start gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-success shrink-0 mt-0.5" />
            <span className="text-muted-foreground">一次只问一个关键问题，回答后再继续</span>
          </li>
          <li className="flex items-start gap-1.5">
            <Lightbulb className="w-4 h-4 text-warning shrink-0 mt-0.5" />
            <span className="text-muted-foreground">所有模型推断都是可修正的假设</span>
          </li>
        </ul>
      </div>

      {/* 跳转 */}
      <div className="space-y-2 rounded-xl border border-border/50 bg-muted/50 p-3.5">
        <h2 className="text-sm font-semibold text-foreground">相关工具</h2>
        <Link
          href="/path-convergence"
          className="flex items-center justify-between gap-2 text-xs text-foreground hover:text-primary transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-muted-foreground" />
            查看完整路径比较
          </span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <ImageIcon className="w-4 h-4" />
          上传材料中的关键信息需你确认
        </div>
      </div>

      {/* 数据操作 */}
      <div className="flex items-center gap-2 pt-1 border-t border-border/60">
        <button
          type="button"
          onClick={onExport}
          className="flex-1 inline-flex items-center justify-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg px-2 py-2 transition-colors"
        >
          <Download className="w-4 h-4" />
          导出数据
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="flex-1 inline-flex items-center justify-center gap-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 rounded-lg px-2 py-2 transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          删除数据
        </button>
      </div>
    </div>
  );
}
