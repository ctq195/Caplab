'use client';

import { FlaskConical } from 'lucide-react';
import type { ChatMessage } from '@/lib/chat-types';

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-sm sm:max-w-[80%] [overflow-wrap:anywhere] whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary ring-1 ring-primary/10">
        <FlaskConical className="h-4 w-4" />
      </span>
      <div className="max-w-[88%] rounded-2xl rounded-tl-md border border-border/60 bg-card px-4 py-3 text-sm leading-relaxed text-foreground shadow-card [overflow-wrap:anywhere] sm:max-w-[82%] dark:border-white/5 dark:shadow-none">
        {message.content ? (
          <span className="whitespace-pre-wrap">{message.content}</span>
        ) : message.streaming ? (
          <span className="inline-flex items-center gap-1.5 text-muted-foreground">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
          </span>
        ) : null}
        {message.streaming && message.content && (
          <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-primary align-text-bottom" />
        )}
      </div>
    </div>
  );
}
