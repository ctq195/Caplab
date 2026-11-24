'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FlaskConical, Menu, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { isActivePath, NAV_ITEMS } from '@/lib/site-config';
import { cn } from '@/lib/utils';

export function SiteHeader() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // 移动端菜单打开时锁定滚动，避免背景穿透
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  return (
    <header className="no-print sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/" className="group flex shrink-0 items-center gap-2.5" aria-label="CapLab 首页">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm transition-transform duration-300 ease-spring group-hover:rotate-[-8deg]">
            <FlaskConical className="h-[19px] w-[19px]" />
          </span>
          <span className="text-[17px] font-bold tracking-tight text-foreground">CapLab</span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="主导航">
          {NAV_ITEMS.map((item) => {
            const isActive = isActivePath(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'relative rounded-lg px-3 py-2 text-[13px] font-medium transition-colors duration-200',
                  isActive
                    ? 'text-primary'
                    : 'text-muted-foreground hover:bg-muted/70 hover:text-foreground',
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                {item.label}
                {isActive ? (
                  <span className="absolute inset-x-3 -bottom-[9px] h-0.5 rounded-full bg-primary" />
                ) : null}
              </Link>
            );
          })}
        </nav>

        <Link
          href="/chat"
          className="btn-primary hidden !min-h-9 !rounded-lg !px-4 !text-[13px] sm:inline-flex"
        >
          开始对话
        </Link>

        <button
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          className="flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground lg:hidden"
          aria-label={mobileOpen ? '关闭导航菜单' : '打开导航菜单'}
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* 移动端菜单：淡入 + 轻微位移 */}
      {mobileOpen ? (
        <nav
          id="mobile-nav"
          className="animate-fade-in border-t border-border/60 bg-card px-4 pb-5 pt-3 lg:hidden"
          aria-label="移动端主导航"
        >
          <div className="grid grid-cols-2 gap-2">
            {NAV_ITEMS.map((item) => {
              const isActive = isActivePath(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center rounded-xl px-3.5 py-3 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
          <Link href="/chat" className="btn-primary mt-3 w-full">
            开始对话
          </Link>
        </nav>
      ) : null}
    </header>
  );
}
