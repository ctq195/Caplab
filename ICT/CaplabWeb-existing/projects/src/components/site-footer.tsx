import Link from 'next/link';
import { FlaskConical, ShieldCheck } from 'lucide-react';
import { NAV_ITEMS } from '@/lib/site-config';

export function SiteFooter() {
  return (
    <footer className="no-print border-t border-border/60 bg-card/40">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1fr]">
          {/* 品牌区 */}
          <div className="max-w-sm">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <FlaskConical className="h-4 w-4" />
              </span>
              <span className="text-[15px] font-bold tracking-tight text-foreground">CapLab</span>
            </div>
            <p className="mt-4 text-[13px] leading-relaxed text-muted-foreground">
              不替你做终身决定，而是陪你把不确定的选择拆成低成本的现实行动，用证据收敛方向。
            </p>
            <p className="mt-3 font-serif text-xs italic tracking-wide text-muted-foreground/70">
              Don&apos;t plan the perfect path, prototype it.
            </p>
          </div>

          {/* 导航分组 */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground/80">
              探索流程
            </h3>
            <ul className="mt-4 space-y-2.5">
              {NAV_ITEMS.slice(0, 4).map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-[13px] text-muted-foreground transition-colors hover:text-primary"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground/80">
              附加能力
            </h3>
            <ul className="mt-4 space-y-2.5">
              {NAV_ITEMS.slice(4).map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-[13px] text-muted-foreground transition-colors hover:text-primary"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* 隐私与安全提示 */}
        <div className="mt-10 flex items-start gap-2.5 rounded-xl border border-border/50 bg-muted/40 px-4 py-3.5">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <p className="text-xs leading-relaxed text-muted-foreground">
            CapLab 不做心理诊断、不索要身份证号等无关隐私，你可随时导出或删除自己的数据；若你正经历强烈痛苦或即时危险，请优先联系可信任的人、学校心理中心或紧急求助。
          </p>
        </div>

        {/* 版权行 */}
        <div className="mt-8 flex flex-col gap-2 border-t border-border/50 pt-6 text-xs text-muted-foreground/80 sm:flex-row sm:items-center sm:justify-between">
          <span>© 2025 CapLab · Career Action Prototyping Lab</span>
        </div>
      </div>
    </footer>
  );
}
