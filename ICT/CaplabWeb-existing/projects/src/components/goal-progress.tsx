'use client';
import { useState,useEffect } from 'react';
import { useOwner } from './account-gate';

type Step = { id:string; title:string; done:number };
export function GoalProgress({chat,goal}: {chat:string; goal:string}) {
  const owner = useOwner();
  const [steps,setSteps] = useState<Step[]>([]);
  const [plan,setPlan] = useState('');
  const [busy,setBusy] = useState(true);
  const [error,setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/steps',{method:'POST',headers:{'Content-Type':'application/json','x-caplab-owner':owner},
      body:JSON.stringify({chat,goal,action:'read'}),signal:controller.signal}).then(async r => {
      if (!r.ok) throw Error(); setSteps(await r.json());
    }).catch(() => { if (!controller.signal.aborted) setError('读取行动失败'); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  },[chat,goal,owner]);
  async function change(action: string, fields: object) {
    setBusy(true); setError('');
    try {
      const res = await fetch('/api/steps',{method:'POST',headers:{'Content-Type':'application/json','x-caplab-owner':owner},body:JSON.stringify({action,chat,goal,...fields})});
      if (!res.ok) throw Error(); setSteps(await res.json());
    } catch { setError('行动未保存，请重试。'); } finally { setBusy(false); }
  }
  const count = steps.filter(s => s.done).length;
  const pct = steps.length ? Math.round(100*count/steps.length) : 0;
  return <section className="space-y-3 rounded-xl border bg-card p-4" aria-label="我的行动目标">
    <h2 className="text-sm font-semibold text-primary">我的行动目标</h2><p>{goal}</p>
    {steps.length ? <><p aria-live="polite">已完成 {count}/{steps.length} 项 · 还差 {100-pct}%</p>
      <progress aria-label="行动完成度" className="block w-full accent-primary" value={count} max={steps.length}/>
      {steps.map(s => <label key={s.id} className="flex items-center gap-2"><input type="checkbox" disabled={busy} checked={!!s.done}
        onChange={e => change('mark',{id:s.id,done:e.target.checked})}/>{s.title}</label>)}</> :
      <form onSubmit={e => { e.preventDefault(); void change('plan',{titles:plan.split('\n').map(t => t.trim()).filter(Boolean)}); }}>
        <label>为这个目标定几个小行动，每行一项<textarea className="my-2 block w-full rounded border p-2" placeholder="找一位学姐了解实习安排" value={plan} onChange={e => setPlan(e.target.value)}/></label>
        <button className="btn-secondary" disabled={busy || !plan.trim()}>确认行动清单</button></form>}
    {error && <p role="alert">{error}</p>}</section>;
}
