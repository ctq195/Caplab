import { identity, login, logout } from '@/lib/demo-auth';

export async function GET() { return Response.json(await identity()); }

export async function POST(request: Request) {
  const data = await request.json();
  if (data.mode === 'logout') { await logout(); return Response.json(null); }
  if (data.mode !== 'account' && data.mode !== 'guest') return Response.json({error:'请选择登录方式'}, {status:400});
  const name = data.mode === 'guest' ? null : String(data.name || '').trim();
  const password = String(data.password || '');
  if (name !== null && (!name || !password || name.length > 100 || password.length > 256))
    return Response.json({error:'请填写测试账号与密码'}, {status:400});
  if (!await login(name, password, new URL(request.url).protocol === 'https:'))
    return Response.json({error:'该账号的密码不匹配'}, {status:401});
  return Response.json(await identity());
}
