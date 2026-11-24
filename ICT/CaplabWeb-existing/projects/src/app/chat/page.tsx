'use client';

import { Suspense, useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { flushSync } from 'react-dom';
import {
  ClipboardList,
  Plus,
  MoreHorizontal,
  PanelLeft,
  PanelLeftClose,
  Paperclip,
  ArrowUp,
  FileText,
  Image as ImageIcon,
} from 'lucide-react';
import { useOwner } from '@/components/account-gate';
import { GoalProgress } from '@/components/goal-progress';
import { privateDraft } from '@/lib/private-draft';
import { VoiceCall } from '@/components/voice-call';
import { MessageBubble } from '@/components/message-bubble';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import type { ChatMessage, Attachment } from '@/lib/chat-types';

let idCounter = 0;
const nextId = () => `msg-${Date.now()}-${idCounter++}`;

const WELCOME: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: '嗨，我是 CapLab。最近有什么事想聊？考研、实习、找工作，或者只是有点拿不定主意，都可以从这里说起。',
};

interface SavedChat {
  id: string;
  messages: ChatMessage[];
}

type Round = {
  model_mode: 'demo' | 'live';
  revision: number;
  active_stage: string;
  confirmed_goal: string | null;
  proposal: { token: string; summary: string; changes: {path:string; value:unknown}[] } | null;
  response: string;
};
const stageNames: Record<string,string> = {profile_intake:'说说近况', profile_confirmation:'核对理解', path_convergence:'比较方向', path_evidence_cycle:'尝试行动', evidence_review:'回顾发现', closed:'本轮结束', blocked:'暂停探索'};

function saveableMessages(messages: ChatMessage[]) {
  return messages.filter((message) => message.content.trim())
    .map((message) => message.streaming ? { ...message, streaming: false } : message);
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="grid min-h-dvh place-items-center text-sm text-muted-foreground">正在载入对话…</div>}>
      <ChatView />
    </Suspense>
  );
}

function ChatView() {
  const owner = useOwner();
  const [goalEntry,setGoalEntry] = useState(false);
  const [round,setRound] = useState<Round | null>(null);
  const [confirmBusy,setConfirmBusy] = useState(false);
  const [loadFailed,setLoadFailed] = useState(false);
  const saveQueue = useRef(Promise.resolve());
  const searchParams = useSearchParams();
  const [inputValue, setInputValue] = useState('');
  const [textMode, setTextMode] = useState(false);
  const [ready, setReady] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [activeId, setActiveId] = useState('');
  const [history, setHistory] = useState<SavedChat[]>([]);
  const [storageIssue, setStorageIssue] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  useEffect(() => {
    let active = true;
    privateDraft(owner,'chats').then((saved: {active:SavedChat; history:SavedChat[]} | null) => {
      if (!active) return;
      setActiveId(saved?.active.id ?? crypto.randomUUID());
      setHistory(saved?.history || []);
      setMessages(saved?.active.messages.length ? saved.active.messages : [WELCOME]);
      setTextMode(true);
      setReady(true);
    }).catch(() => { if (active) setLoadFailed(true); });
    return () => { active = false; };
  }, [owner]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>([]);
  const [error, setError] = useState<string | null>(null);

  const callRef = useRef<{ start: () => void }>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const entryHandled = useRef(false);
  const autoCall = useRef(false);

  // 自动滚动到底部
  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (!ready) return;
    const snapshot = { active: { id: activeId, messages: saveableMessages(messages) }, history };
    saveQueue.current = saveQueue.current.then(async () => {
      await privateDraft(owner,'chats',snapshot); setStorageIssue(false);
    }).catch(() => setStorageIssue(true));
  }, [activeId, messages, history, ready, owner]);

  const invoke = useCallback(async (chat: string, fields: object, signal?: AbortSignal): Promise<Round> => {
    const res = await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','x-caplab-owner':owner},
      body:JSON.stringify({chat,...fields}), signal});
    const data = await res.json();
    if (!res.ok) throw Error(data.error || '请求失败');
    return data;
  },[owner]);
  const latestRequest = useRef(0);
  useEffect(() => {
    if (!activeId) return;
    const seq = ++latestRequest.current;
    const controller = new AbortController();
    invoke(activeId,{action:'status'},controller.signal).then(data => {
      if (seq === latestRequest.current) setRound(data);
    }).catch(e => { if (!controller.signal.aborted && seq === latestRequest.current) setError(e.message); });
    return () => controller.abort();
  },[activeId,invoke]);

  async function decide(mode: 'confirm' | 'reject' | 'edit') {
    if (!round?.proposal || confirmBusy) return;
    setConfirmBusy(true); setError(null);
    const seq = ++latestRequest.current;
    try {
      const text = mode === 'confirm' ? '确认保存这份草稿' : '退回这份草稿';
      const data = await invoke(activeId,{action:'confirm',decision:mode === 'edit' ? 'revise' : mode,confirmation_text:text,token:round.proposal.token});
      if (seq !== latestRequest.current) return;
      setRound(data);
      setMessages(prev => [...prev,{id:nextId(),role:'assistant',content:data.response}]);
      if (mode === 'edit') { setInputValue(round.proposal.summary); setGoalEntry(round.proposal.changes.length === 1 && round.proposal.changes[0].path === "/sections/intake/decision_question"); textareaRef.current?.focus(); }
    } catch(e) {
      if (seq === latestRequest.current) {
        setError(e instanceof Error ? e.message : '确认失败');
        const fresh = await invoke(activeId,{action:'status'}).catch(() => null);
        if (fresh && seq === latestRequest.current) setRound(fresh);
      }
    } finally { setConfirmBusy(false); }
  }

  const autoGrow = () => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = `${Math.min(ta.scrollHeight, 112)}px`;
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    autoGrow();
  };

  const handleAttachClick = () => fileInputRef.current?.click();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const next: Attachment[] = [];
    Array.from(files).forEach((f) => {
      const sizeKb = f.size / 1024;
      const sizeLabel = sizeKb > 1024 ? `${(sizeKb / 1024).toFixed(1)}MB` : `${Math.round(sizeKb)}KB`;
      next.push({
        name: f.name,
        sizeLabel,
        kind: f.type.startsWith('image/') ? 'image' : 'file',
      });
    });
    setPendingAttachments((prev) => [...prev, ...next]);
    e.target.value = '';
  };

  const removeAttachment = (idx: number) => {
    setPendingAttachments((prev) => prev.filter((_, i) => i !== idx));
  };

  const uploadAttachments = async (attachments: Attachment[], userMessageId: string, signal: AbortSignal) => {
    const input = fileInputRef.current;
    if (!input?.files?.length || attachments.length === 0) return;
    const files = Array.from(input.files).slice(0, attachments.length);
    for (let i = 0; i < files.length; i += 1) {
      const formData = new FormData();
      formData.append('file', files[i]);
      try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData, signal });
        if (!res.ok) continue;
        const result = (await res.json()) as { data?: { message?: string } };
        const note = result.data?.message;
        if (note && !signal.aborted) {
          const receipt: ChatMessage = {
            id: nextId(),
            role: 'assistant',
            content: `已接收材料「${attachments[i].name}」：${note}`,
          };
          setMessages((prev) => prev.some((message) => message.id === userMessageId) ? [...prev, receipt] : prev);
        }
      } catch {
        // 上传失败不阻断对话，文件信息仍随消息发送
      }
    }
  };

  const sendMessage = async (text: string, attachments: Attachment[], voice = false, action = 'message') => {
    const content = text.trim();
    if (round?.proposal || confirmBusy) { setTextMode(true); setInputValue(content); return; }
    if (!content || (abortRef.current && !abortRef.current.signal.aborted)) return;

    setError(null);

    // 用户消息（附带文件信息）
    let userContent = content;
    if (attachments.length > 0) {
      const fileLines = attachments.map((a) => `[已上传${a.kind === 'image' ? '图片' : '文件'}：${a.name}（${a.sizeLabel}）]`);
      userContent = `${content}\n${fileLines.join('\n')}`;
    }
    const userMsg: ChatMessage = { id: nextId(), role: 'user', content: userContent };

    // 占位助手消息
    const assistantId = nextId();
    const assistantMsg: ChatMessage = { id: assistantId, role: 'assistant', content: '', streaming: true };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);
    setPendingAttachments([]);
    setInputValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    const controller = new AbortController();
    abortRef.current = controller;
    void uploadAttachments(attachments, userMsg.id, controller.signal);

    try {
      const seq = ++latestRequest.current;
      const data = await invoke(activeId,{action,message:userContent},controller.signal);
      if (seq !== latestRequest.current) return;
      setRound(data);
      setGoalEntry(false);
      if (data.proposal && voice) setTextMode(true);
      setMessages(prev => prev.map(m => m.id === assistantId ? {...m,content:data.response,streaming:false} : m));
      return data.response;
    } catch (e) {
      if (controller.signal.aborted) {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m)),
        );
      } else {
        const msg = e instanceof Error ? e.message : '发生未知错误';
        if (abortRef.current === controller) {
          setError(msg); setInputValue(content);
          const fresh = await invoke(activeId,{action:'status'}).catch(() => null);
          if (fresh && abortRef.current === controller) setRound(fresh);
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, streaming: false, content: m.content || `（生成失败：${msg}）` }
              : m,
          ),
        );
      }
      if (voice) throw e;
    } finally {
      if (abortRef.current === controller) {
        setIsStreaming(false);
        abortRef.current = null;
      }
    }
  };

  const handleSend = () => {
    void sendMessage(inputValue, pendingAttachments, false, goalEntry ? 'propose_goal' : 'message');
  };

  // 首页统一入口携带的参数：?q=... 直接进入文字对话并发送；?mode=call 自动发起语音通话
  useEffect(() => {
    if (!ready || entryHandled.current) return;
    entryHandled.current = true;
    const q = searchParams.get('q')?.trim();
    if (q) {
      window.history.replaceState(null, "", "/chat");
      setTextMode(true);
      void sendMessage(q, []);
      return;
    }
    if (searchParams.get('mode') === 'call') {
      autoCall.current = true;
      setTextMode(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, searchParams]);

  // VoiceCall 挂载完成（ref 就绪）后再启动通话，避免早于 ref 赋值调用
  useEffect(() => {
    if (ready && !textMode && autoCall.current) {
      autoCall.current = false;
      callRef.current?.start();
    }
  }, [ready, textMode]);

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const currentChat = messages.some((message) => message.role === 'user')
    ? { id: activeId, messages }
    : null;

  const switchChat = (chat?: SavedChat, archiveCurrent = true) => {
    if (chat?.id === activeId) {
      setTextMode(true);
      return;
    }
    ++latestRequest.current;
    setRound(null);
    setGoalEntry(false);
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setHistory((previous) => {
      const others = previous.filter((item) => item.id !== chat?.id);
      return currentChat && archiveCurrent
        ? [{ id: activeId, messages: saveableMessages(messages) }, ...others]
        : others;
    });
    setActiveId(chat?.id ?? nextId());
    setMessages(chat ? chat.messages.map((message) => message.id === WELCOME.id ? WELCOME : message) : [WELCOME]);
    setInputValue('');
    setError(null);
    setPendingAttachments([]);
    setTextMode(true);
  };

  const handleExport = () => {
    const data = messages.map((m) => ({ role: m.role, content: m.content }));
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'caplab-export.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDelete = () => {
    if (window.confirm('确定删除本次会话的全部消息吗？此操作不可撤销。')) {
      switchChat(undefined, false);
    }
  };

  const chats = currentChat ? [currentChat, ...history] : history;
  const historyList = (
    <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
      {storageIssue && <p role="status" className="mb-3 text-sm text-destructive">会话暂时未能保存到账号，请导出本次对话。</p>}
      {chats.length === 0 ? <p className="px-2 py-4 text-sm text-muted-foreground">还没有对话记录。</p> : (
        <ul className="space-y-1">
          {chats.map((chat) => (
            <li key={chat.id}>
              <button type="button" aria-current={chat.id === activeId ? 'true' : undefined}
                className="w-full rounded-lg px-3 py-2.5 text-left text-sm hover:bg-accent aria-[current=true]:bg-accent aria-[current=true]:font-semibold"
                onClick={() => { switchChat(chat); setDrawerOpen(false); }}>
                <span className="line-clamp-2 break-words">{chat.messages.find((message) => message.role === 'user')?.content}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  const newChatControl = (
    <button type="button" className="btn-secondary mx-3 my-3 justify-start" onClick={() => { switchChat(); setDrawerOpen(false); }}>
      <Plus size={16} /> 新会话
    </button>
  );

  const historyControl = (
    <>
      {!sidebarOpen && (
        <button type="button" className="btn-ghost hidden shrink-0 md:inline-flex" aria-label="展开历史对话"
          aria-expanded={false} onClick={() => setSidebarOpen(true)}><PanelLeft size={20} /></button>
      )}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetTrigger asChild>
          <button type="button" className="btn-ghost shrink-0 md:hidden" aria-label="展开历史对话"><PanelLeft size={20} /></button>
        </SheetTrigger>
        <SheetContent side="left" className="gap-0 bg-muted">
          <SheetHeader>
            <SheetTitle>历史对话</SheetTitle>
            <SheetDescription className="sr-only">选择一段对话，接着上次聊。</SheetDescription>
          </SheetHeader>
          {newChatControl}
          {historyList}
        </SheetContent>
      </Sheet>
    </>
  );

  if (!ready) return <p className="p-6">{loadFailed ? '读取会话失败，请刷新后重试。' : '正在恢复你的会话…'}</p>;
  return (
    <div className="flex min-h-dvh">
      {sidebarOpen && (
        <aside aria-label="历史对话" className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r border-border bg-muted md:flex">
          <div className="flex items-center justify-between px-4 pt-3">
            <h2 className="text-sm font-semibold">历史对话</h2>
            <button type="button" className="btn-ghost" aria-label="收起历史对话" aria-expanded="true"
              onClick={() => setSidebarOpen(false)}><PanelLeftClose size={19} /></button>
          </div>
          {newChatControl}
          {historyList}
        </aside>
      )}
      <div className="min-w-0 flex-1">
        {!textMode ? (
          <VoiceCall ref={callRef} historyControl={historyControl} reply={(text) => sendMessage(text, [], true)} cancelReply={handleStop}
            openText={(draft, send) => { setTextMode(true); if (send) void sendMessage(draft, []); else setInputValue(draft); }} />
        ) : (
          <main className="voice-entry mx-auto flex h-dvh w-full max-w-4xl flex-col lg:flex-row">
            {/* ========== 中间对话区 ========== */}
            <section className="flex-1 min-w-0 flex flex-col bg-background min-h-0">
              {/* 状态条 */}
              <div className="bg-background/85 backdrop-blur-xl border-b border-border/60 px-4 sm:px-5 py-2.5 flex items-center justify-between gap-3 shrink-0">
                <div className="flex shrink-0 items-center gap-1">
                  {historyControl}
                  {round?.model_mode === 'demo' && <span className="text-xs text-muted-foreground">规则演示</span>}
                  <Link href="/" aria-label="返回 CapLab 首页" className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                    <ClipboardList className="h-3.5 w-3.5" /> CapLab
                  </Link>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-x-2">
                  <button className="btn-ghost" disabled={isStreaming || !!round?.proposal} onClick={() => {setGoalEntry(!goalEntry); textareaRef.current?.focus();}}>{goalEntry ? '返回聊天' : '设定目标'}</button>
                  <button className="btn-ghost text-center" disabled={isStreaming} onClick={() => {
                    flushSync(() => setTextMode(false));
                    callRef.current?.start();
                  }}>打字太麻烦，我要打电话</button>
                  <details className="relative">
                    <summary aria-label="会话工具" className="btn-ghost cursor-pointer list-none"><MoreHorizontal size={18} /></summary>
                    <div className="absolute right-0 top-full z-20 grid w-40 rounded-xl border bg-card p-2 text-sm shadow-float">
                      <Link className="btn-ghost" href="/path-convergence">比较路径</Link>
                      <Link className="btn-ghost" href="/evidence-cycle">查看行动</Link>
                      <button className="btn-ghost" onClick={handleExport}>导出对话</button>
                      <button className="btn-ghost" onClick={handleDelete}>删除对话</button>
                    </div>
                  </details>
                </div>
              </div>

              {/* 气泡流 */}
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-5">
                {messages.map((m) => (
                  <MessageBubble key={m.id} message={m} />
                ))}
                {round?.proposal && <section className="rounded-xl border border-primary/30 bg-card p-4">
                  <h2 className="font-semibold">这样记准确吗？</h2><p className="my-2">{round.proposal.summary}</p>
                  <details><summary>查看具体改动</summary>{round.proposal.changes.map((c,i) => <p key={i} className="break-words text-sm">{c.path.split('/').pop()} · {typeof c.value === 'string' ? c.value : JSON.stringify(c.value)}</p>)}</details>
                  <div className="mt-3 flex gap-2">{(['confirm','edit','reject'] as const).map((m,i) => <button type="button" className="btn-secondary" disabled={confirmBusy || isStreaming} key={m} onClick={() => decide(m)}>{['确认保存','改一下','先不保存'][i]}</button>)}</div>
                </section>}
                {round?.confirmed_goal && <GoalProgress key={activeId+round.confirmed_goal} chat={activeId} goal={round.confirmed_goal}/>}
                {round && <details className="text-sm text-muted-foreground"><summary>查看探索进展</summary>{stageNames[round.active_stage] || round.active_stage} · 已确认版本 {round.revision} · {round.model_mode === 'demo' ? '本地规则演示' : '模型推理'}</details>}
                {error && (
                  <div className="text-xs text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                    {error}
                  </div>
                )}
              </div>

              {/* 底部输入区 */}
              <div className="bg-card border-t border-border/60 px-3 sm:px-4 py-3 shrink-0 space-y-2">
                {/* 快捷指令 */}
                <div className="flex items-center gap-2 overflow-x-auto scrollbar-none">
                  <button
                    type="button"
                    onClick={() => textareaRef.current?.focus()}
                    className="shrink-0 border border-border/70 rounded-full px-3.5 py-1.5 text-xs text-muted-foreground hover:border-primary/30 hover:bg-muted hover:text-foreground transition-colors"
                  >
                    开始或继续
                  </button>
                  <Link
                    href="/resume"
                    className="shrink-0 border border-border/70 rounded-full px-3.5 py-1.5 text-xs text-muted-foreground hover:border-primary/30 hover:bg-muted hover:text-foreground transition-colors"
                  >
                    生成简历
                  </Link>
                  <Link
                    href="/interview"
                    className="shrink-0 border border-border/70 rounded-full px-3.5 py-1.5 text-xs text-muted-foreground hover:border-primary/30 hover:bg-muted hover:text-foreground transition-colors"
                  >
                    模拟面试
                  </Link>
                  <Link
                    href="/review-report"
                    className="shrink-0 border border-border/70 rounded-full px-3.5 py-1.5 text-xs text-muted-foreground hover:border-primary/30 hover:bg-muted hover:text-foreground transition-colors"
                  >
                    结束并复盘
                  </Link>
                </div>

                {/* 待上传附件预览 */}
                {pendingAttachments.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {pendingAttachments.map((a, idx) => (
                      <span
                        key={`${a.name}-${idx}`}
                        className="inline-flex items-center gap-1.5 bg-muted rounded-lg px-2.5 py-1.5 text-xs text-foreground"
                      >
                        {a.kind === 'image' ? (
                          <ImageIcon className="w-3.5 h-3.5 text-muted-foreground" />
                        ) : (
                          <FileText className="w-3.5 h-3.5 text-muted-foreground" />
                        )}
                        {a.name} · {a.sizeLabel}
                        <button
                          type="button"
                          onClick={() => removeAttachment(idx)}
                          className="text-muted-foreground hover:text-destructive ml-0.5"
                          aria-label="移除附件"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                {/* 输入行 */}
                <div className="flex items-end gap-2">
                  <button
                    type="button"
                    aria-label="上传文件"
                    onClick={handleAttachClick}
                    className="w-10 h-10 shrink-0 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted flex items-center justify-center transition-colors"
                  >
                    <Paperclip className="w-5 h-5" />
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    value={inputValue}
                    onChange={handleInput}
                    onKeyDown={handleKeyDown}
                    disabled={!!round?.proposal || confirmBusy}
                    placeholder={round?.proposal ? "先核对上面的草稿，再继续聊" : goalEntry ? "写下你想达成的目标" : "想聊什么？"}
                    className="flex-1 resize-none bg-muted/70 border border-transparent rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/40 focus:bg-background focus:ring-4 focus:ring-primary/10 transition-all max-h-28"
                  />
                  {isStreaming ? (
                    <button
                      type="button"
                      aria-label="停止生成"
                      onClick={handleStop}
                      className="bg-muted text-foreground rounded-xl w-10 h-10 shrink-0 flex items-center justify-center hover:bg-muted-foreground/20 active:scale-95 transition-all"
                    >
                      <span className="w-3 h-3 bg-foreground rounded-sm" />
                    </button>
                  ) : (
                    <button
                      type="button"
                      aria-label="发送"
                      onClick={handleSend}
                      disabled={!inputValue.trim()}
                      className="bg-primary text-primary-foreground rounded-xl w-10 h-10 shrink-0 flex items-center justify-center hover:opacity-90 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <ArrowUp className="w-5 h-5" />
                    </button>
                  )}
                </div>

                <p className="text-[11px] text-muted-foreground/70 pl-12">
                  PDF / Word / 图片 · 内容仅在你确认后写入档案
                </p>
              </div>
            </section>

          </main>
        )}
      </div>
    </div>
  );
}
