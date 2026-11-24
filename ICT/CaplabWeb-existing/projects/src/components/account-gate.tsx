'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import type { Identity } from '@/lib/demo-auth';

const Account = createContext('');
export const useOwner = () => useContext(Account);

export function AccountGate({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [user,setUser] = useState<Identity | null>();
  const [name,setName] = useState('');
  const [password,setPassword] = useState('');
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  const [choosing,setChoosing] = useState(false);
  useEffect(() => {
    fetch('/api/session', { cache:'no-store' }).then(r => r.json()).then(setUser)
      .catch(() => { setUser(null); setError('读取身份失败，请重试'); });
    const refresh = (e: StorageEvent) => { if (e.key === 'caplab-identity-change') location.reload(); };
    window.addEventListener('storage', refresh);
    return () => window.removeEventListener('storage', refresh);
  }, []);
  async function enter(mode: 'account' | 'guest' | 'logout') {
    setBusy(true); setError('');
    try {
      const r = await fetch('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode,name,password})});
      const data = await r.json();
      if (!r.ok) throw Error(data.error);
      setUser(data); setPassword(''); setName(''); setChoosing(false);
      localStorage.setItem('caplab-identity-change', crypto.randomUUID());
      if (mode === 'logout') location.replace('/');
    } catch (err) { setError(err instanceof Error ? err.message : '登录失败'); }
    finally { setBusy(false); }
  }
  if (user === undefined) return <p className="p-6">正在打开 CapLab…</p>;
  if (!user && (path !== '/' || choosing)) return <main className="mx-auto mt-20 max-w-md space-y-5 p-6">
    <h1 className="font-serif text-3xl">从这里开始探索</h1>
    <Button disabled={busy} onClick={() => enter('guest')}>以游客身份继续</Button>
    <form className="grid gap-3 rounded-xl border bg-card p-5" onSubmit={e => { e.preventDefault(); void enter('account'); }}>
      <h2>用账号保存探索记录</h2>
      <label>测试账号<input className="block w-full rounded border p-2" required value={name} onChange={e => setName(e.target.value)} /></label>
      <label>测试密码<input className="block w-full rounded border p-2" type="password" required value={password} onChange={e => setPassword(e.target.value)} /></label>
      <p className="text-sm text-muted-foreground">首次填写会创建验证账号。下次用相同账号和密码继续。</p>
      <Button disabled={busy}>账号登录</Button>
    </form>{error && <p role="alert">{error}</p>}</main>;
  return <Account.Provider value={user?.id || ''}><div className="no-print flex justify-end gap-3 px-5 py-1 text-xs">
    {user ? <><span>{user.name || '游客'}</span><button disabled={busy} onClick={() => enter('logout')}>退出 / 切换身份</button></> : <button onClick={() => setChoosing(true)}>游客 / 账号登录</button>}
    {error && <span role="alert">{error}</span>}</div><div key={user?.id}>{children}</div></Account.Provider>;
}
