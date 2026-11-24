'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowUp, ArrowUpRight, AudioLines, BookOpen, Compass, FlaskConical, GitBranch, NotebookPen, Sprout } from 'lucide-react';
import { CAPABILITIES } from '@/lib/site-config';

const tools = [
  { href: '/path-convergence', title: '比较方向', desc: '把几条路放在一起，看清门槛与取舍。', icon: GitBranch },
  { href: '/evidence-cycle', title: '行动实验', desc: '为一个疑问设计小任务，带回现实反馈。', icon: FlaskConical },
  { href: '/review-report', title: '探索复盘', desc: '翻看已有证据，决定下一步怎么走。', icon: NotebookPen },
  ...CAPABILITIES,
];

export default function HomePage() {
  const router = useRouter();
  const [draft, setDraft] = useState('');

  const startText = () => {
    const text = draft.trim();
    router.push(text ? `/chat?q=${encodeURIComponent(text)}` : '/chat');
  };
  const startCall = () => router.push('/chat?mode=call');

  return (
    <main className="mx-auto max-w-6xl px-5 pb-16 sm:px-9">
      <header className="flex min-h-18 items-center justify-between border-b border-border py-4">
        <Link href="/" aria-label="CapLab 首页" className="flex items-center gap-2.5">
          <span className="grid size-10 place-items-center rounded-2xl bg-primary text-primary-foreground"><FlaskConical size={22} /></span>
          <span className="text-xl font-bold tracking-tight">CapLab</span>
        </Link>
        <a href="#tools" className="btn-ghost">功能导览 <BookOpen size={16} /></a>
      </header>
      <section className="grid items-center gap-6 py-9 sm:py-14 lg:grid-cols-[1.1fr_1fr] lg:gap-12">
        <div>
          <h1 className="font-serif text-[clamp(2.5rem,5vw,4.7rem)] font-semibold leading-[1.12]">
            <span className="mb-2 block font-sans text-[.72em] tracking-tight text-primary">CapLab</span>生涯探索实验室
          </h1>
          <p className="mt-5 max-w-md text-base leading-7 text-muted-foreground">考研、实习，还是先找工作？如果越想越焦虑，我们可以先聊聊。一起回看那些让你期待或犹豫的时刻，分清自己的愿望和别人的期待，再用一个小行动，试试哪条路更适合你。</p>

          {/* 统一主入口：打字 / 语音，参考 DeepSeek 首页输入区 */}
          <form
            className="mt-7 max-w-xl rounded-[1.7rem] border border-border bg-card p-4 shadow-card transition-colors focus-within:border-primary"
            onSubmit={(event) => { event.preventDefault(); startText(); }}
          >
            <label htmlFor="home-entry" className="sr-only">说说你正在纠结的事</label>
            <textarea
              id="home-entry"
              rows={3}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  startText();
                }
              }}
              placeholder="问点什么，一起探索"
              className="block w-full resize-none bg-transparent px-1.5 py-1 text-base leading-7 focus-visible:outline-none"
            />
            <div className="mt-3 flex items-center justify-between gap-3">
              <button type="button" onClick={startCall} className="btn-secondary min-h-11 gap-2 px-4 text-sm">
                <AudioLines size={17} className="text-primary" /> 语音通话
              </button>
              <button
                type="submit"
                aria-label="发送并开始对话"
                disabled={!draft.trim()}
                className="grid size-11 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground transition hover:brightness-110 active:scale-95 disabled:opacity-35"
              >
                <ArrowUp size={18} />
              </button>
            </div>
            <p className="mt-2 px-1.5 text-xs leading-5 text-muted-foreground">Enter 发送 · Shift+Enter 换行，语音通话会使用麦克风</p>
          </form>

          <div className="mt-5 flex flex-wrap gap-2.5">
            <Link href="/chat" className="btn-ghost border border-border bg-card">和 CapLab 对话</Link>
            <Link href="/resume" className="btn-ghost border border-border bg-card">简历工坊</Link>
            <Link href="/interview" className="btn-ghost border border-border bg-card">模拟面试</Link>
          </div>
        </div>
        <aside aria-label="探索示例" className="action-swatch">
          <div className="action-sheet">
            <p className="flex items-center gap-2 text-sm font-semibold text-primary"><Compass size={17} /> 探索手记 · 示例</p>
            <p className="my-5 font-serif text-2xl font-semibold">“我适合做产品吗？”</p>
            <div className="border-t border-dashed border-border pt-4 text-sm leading-6">
              <p className="flex items-center gap-2 font-semibold text-primary"><Sprout size={17} /> 先试一件事</p>
              <p className="mt-1">找一位产品实习生，聊聊最近一周具体做了什么。</p>
              <p className="mt-3 text-muted-foreground">记下一件你想亲手试试的工作。</p>
            </div>
          </div>
        </aside>
      </section>
      <section id="tools" aria-labelledby="tools-title" className="scroll-mt-5 border-t border-border pt-7">
        <h2 id="tools-title" className="font-serif text-2xl font-semibold">探索工具</h2>
        <div className="mt-4 grid gap-x-7 sm:grid-cols-2 lg:grid-cols-3">
          {tools.map(({ href, title, desc, icon: Icon }) => (
            <Link key={title} href={href} className="group flex items-start gap-3 rounded-lg border-b border-border px-2 py-5 transition-colors hover:bg-accent">
              <Icon className="mt-1 shrink-0 text-primary" size={22} />
              <div className="flex-1"><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm leading-6 text-muted-foreground">{desc}</p></div>
              <ArrowUpRight size={16} className="mt-1 text-muted-foreground transition-transform group-hover:-translate-y-0.5" />
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
