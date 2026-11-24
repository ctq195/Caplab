import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface SurfaceCardProps extends HTMLAttributes<HTMLElement> {
  as?: 'section' | 'article' | 'div' | 'aside';
  padded?: boolean;
  interactive?: boolean;
  children: ReactNode;
}

export function SurfaceCard({
  as: Tag = 'div',
  padded = true,
  interactive = false,
  className,
  children,
  ...props
}: SurfaceCardProps) {
  return (
    <Tag
      className={cn(
        'relative rounded-2xl border border-border/70 bg-card shadow-card',
        'dark:border-white/5 dark:shadow-none',
        padded && 'p-5 sm:p-6',
        interactive &&
          'group/card transition-all duration-300 ease-out hover:-translate-y-1 hover:border-primary/40 hover:shadow-float dark:hover:border-primary/30',
        className,
      )}
      {...props}
    >
      {children}
    </Tag>
  );
}

export function CardHeading({
  icon: Icon,
  title,
  hint,
  className,
}: {
  icon?: React.ComponentType<{ className?: string }>;
  title: ReactNode;
  hint?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-wrap items-center justify-between gap-2', className)}>
      <h2 className="flex items-center gap-2 text-base font-semibold text-foreground">
        {Icon ? <Icon className="h-4 w-4 text-primary" /> : null}
        {title}
      </h2>
      {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
    </div>
  );
}
