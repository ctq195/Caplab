import Link from 'next/link';
import { ArrowLeft, type LucideIcon } from 'lucide-react';

interface PageShellProps {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  description?: string;
  backHref?: string;
  backLabel?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export function PageShell({
  icon: Icon,
  eyebrow,
  title,
  description,
  backHref = '/',
  backLabel = '返回开场',
  actions,
  children,
}: PageShellProps) {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-6 sm:px-6 sm:pt-8 lg:px-8">
      <Link
        href={backHref}
        className="group mb-6 inline-flex items-center gap-1.5 rounded-md text-xs font-medium text-muted-foreground transition-colors hover:text-primary"
      >
        <ArrowLeft className="h-3.5 w-3.5 transition-transform duration-200 group-hover:-translate-x-0.5" />
        {backLabel}
      </Link>

      <header className="animate-fade-up mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl">
          <span className="eyebrow">
            <Icon className="h-3.5 w-3.5" />
            {eyebrow}
          </span>
          <h1 className="mt-3.5 text-[26px] font-bold leading-tight tracking-tight text-foreground sm:text-[32px]">
            {title}
          </h1>
          {description ? (
            <p className="mt-2.5 text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </header>

      {children}
    </main>
  );
}
