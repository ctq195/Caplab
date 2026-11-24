'use client';
import { useOwner } from '@/components/account-gate';
import { privateDraft } from '@/lib/private-draft';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { ArrowRight, ClipboardCheck, MessagesSquare } from 'lucide-react';
import { PageShell } from '@/components/page-shell';
import { interviewFollowup, interviewReport, interviewStart, type InterviewReport, type InterviewSetup, type InterviewStart, type InterviewTurn } from '@/lib/interview-session';
import { parseResume, resumeText } from '@/lib/resume-document';

const emptySetup: InterviewSetup = { company: '', role: '', round: '岗位面', description: '', resume: '' };
const fieldClass = 'w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm';
const maxTurns = 3;

export default function InterviewPage() {
  return <Suspense><InterviewRoom /></Suspense>;
}

function InterviewRoom() {
  const owner = useOwner();
  const params = useSearchParams();
  const [setup, setSetup] = useState(emptySetup);
  const [opening, setOpening] = useState<InterviewStart | null>(null);
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<InterviewTurn[]>([]);
  const [answer, setAnswer] = useState('');
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function loadDraft() {
    try {
      const stored = await privateDraft(owner,'resume');
      const text = stored ? resumeText(parseResume(stored)) : '';
      if (!text) {
        setError('简历工坊还没有可用内容，也可以直接粘贴简历。');
        return;
      }
      setSetup((previous) => ({ ...previous, resume: text.slice(0, 16000) }));
      setError('');
    } catch {
      setError('这份草稿无法读取，请粘贴简历内容。');
    }
  }

  useEffect(() => {
    if (params.get('resume') === 'draft') loadDraft();
  }, [params]);

  async function run(action: 'start' | 'followup' | 'report', nextTurns = turns) {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/interview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, setup, turns: nextTurns }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.error === 'string' ? result.error : '请求失败，请重试。');

      if (action === 'start') {
        const beginning = interviewStart.parse(result);
        setOpening(beginning);
        setQuestion(beginning.question);
      } else if (action === 'followup') {
        setQuestion(interviewFollowup.parse(result).question);
      } else {
        setReport(interviewReport.parse(result));
        setQuestion('');
      }
      setTurns(nextTurns);
      setAnswer('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '请求中断，请重试。');
    } finally {
      setBusy(false);
    }
  }

  function submitAnswer() {
    if (!answer.trim()) return;
    const nextTurns = [...turns, { question, answer: answer.trim() }];
    void run(nextTurns.length >= maxTurns ? 'report' : 'followup', nextTurns);
  }

  return (
    <PageShell icon={MessagesSquare} eyebrow="求职准备" title="模拟面试" backHref="/resume" backLabel="返回简历工坊"
      description="用职位描述和真实经历练一轮。每次回答后，面试官会针对你的回答继续追问。">
      {error && <p role="alert" className="mb-4 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
      {opening === null ? (
        <form className="space-y-5 rounded-2xl border bg-card p-5 sm:p-7" onSubmit={(event) => { event.preventDefault(); void run('start'); }}>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="space-y-2 text-sm"><span>目标岗位</span>
              <input required maxLength={150} disabled={busy} className={fieldClass} value={setup.role} onChange={(event) => setSetup({ ...setup, role: event.target.value })} />
            </label>
            <label className="space-y-2 text-sm"><span>目标公司（选填）</span>
              <input maxLength={150} disabled={busy} className={fieldClass} value={setup.company} onChange={(event) => setSetup({ ...setup, company: event.target.value })} />
            </label>
            <label className="space-y-2 text-sm"><span>面试轮次</span>
              <select className={fieldClass} disabled={busy} value={setup.round} onChange={(event) => setSetup({ ...setup, round: event.target.value as InterviewSetup['round'] })}>
                <option>岗位面</option><option>行为面</option><option>HR 面</option>
              </select>
            </label>
          </div>
          <div className="grid items-start gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm"><span>职位描述（JD）</span>
              <textarea required rows={8} maxLength={12000} disabled={busy} className={fieldClass} value={setup.description} onChange={(event) => setSetup({ ...setup, description: event.target.value })} />
            </label>
            <div className="space-y-2">
              <label className="block space-y-2 text-sm"><span>简历内容</span>
                <textarea aria-label="简历内容" required rows={8} maxLength={16000} disabled={busy} className={fieldClass} value={setup.resume} onChange={(event) => setSetup({ ...setup, resume: event.target.value })} />
              </label>
              <button type="button" className="btn-ghost" disabled={busy} onClick={loadDraft}>载入简历工坊草稿</button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">开始后会将岗位描述与上面填写的简历内容发送给已配置的 AI 服务生成练习题。</p>
          <button className="btn-primary" disabled={busy || !setup.role.trim() || !setup.description.trim() || !setup.resume.trim()}>
            {busy ? '正在生成首题…' : '开始模拟面试'} <ArrowRight size={16} />
          </button>
        </form>
      ) : (
        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <div className="min-w-0 space-y-4">
            {turns.map((turn, index) => <details key={index} className="rounded-xl border bg-card p-4 text-sm">
              <summary className="cursor-pointer font-medium">{turn.question}</summary>
              <p className="mt-3 whitespace-pre-wrap leading-6 text-muted-foreground">{turn.answer}</p>
            </details>)}
            {report ? (
              <section className="space-y-4 rounded-2xl border bg-card p-5">
                <h2 className="flex items-center gap-2 text-lg font-semibold"><ClipboardCheck size={20} /> 本轮复盘</h2>
                {report.strengths.length > 0 && <div><h3 className="font-semibold">做得好的地方</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{report.strengths.map((text, index) => <li key={index}>{text}</li>)}</ul></div>}
                <div><h3 className="font-semibold">下次可以改进</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{report.improvements.map((text, index) => <li key={index}>{text}</li>)}</ul></div>
                <p className="rounded-lg bg-accent p-3 text-sm leading-6">{report.action}</p>
                <button className="btn-secondary" onClick={() => { setOpening(null); setTurns([]); setReport(null); }}>再练一轮</button>
              </section>
            ) : (
              <form className="space-y-4 rounded-2xl border bg-card p-5" onSubmit={(event) => { event.preventDefault(); submitAnswer(); }}>
                <p className="text-sm text-primary">第 {turns.length + 1} 题</p>
                <h2 className="text-lg font-semibold leading-7">{question}</h2>
                <label className="block space-y-2 text-sm"><span>你的回答</span>
                  <textarea className={fieldClass} rows={5} maxLength={4500} disabled={busy} value={answer} onChange={(event) => setAnswer(event.target.value)} />
                </label>
                <div className="flex flex-wrap gap-2">
                  <button className="btn-primary" disabled={busy || !answer.trim()}>{busy ? '面试官正在整理…' : turns.length + 1 >= maxTurns ? '提交并查看复盘' : '提交回答'}</button>
                  {turns.length > 0 && <button type="button" className="btn-secondary" disabled={busy} onClick={() => void run('report')}>结束并复盘</button>}
                </div>
              </form>
            )}
          </div>
          <aside className="space-y-3 rounded-2xl border bg-card p-5">
            <h2 className="font-semibold">岗位与简历对照</h2>
            {opening.matches.map((match, index) => (
              <div key={index} className="border-t pt-3 text-sm">
                <p className="font-semibold">{match.requirement}</p>
                <p className="mt-1 text-xs text-primary">{match.status}</p>
                <p className="mt-1 leading-6 text-muted-foreground">{match.evidence}</p>
              </div>
            ))}
          </aside>
        </div>
      )}
      <p className="mt-5 text-xs text-muted-foreground"><a className="underline" href="https://github.com/jennifer88huang/interview-skills">面试流程参考</a></p>
    </PageShell>
  );
}
