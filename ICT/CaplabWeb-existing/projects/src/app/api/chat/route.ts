import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { database, identity } from '@/lib/demo-auth';

export async function POST(request: Request) {
  const user = await identity();
  if (!user || request.headers.get('x-caplab-owner') !== user.id) return Response.json({error:'身份已变化，请刷新页面'}, {status:401});
  const {action = 'message', chat, message, decision, token, confirmation_text} = await request.json();
  if (typeof chat !== 'string' || !/^[A-Za-z0-9_-]{1,64}$/.test(chat) || !['message','propose_goal','confirm','status'].includes(action))
    return Response.json({error:'无效的会话请求'}, {status:400});
  const endpoint = process.env.CAPLAB_INVOCATIONS_URL || 'http://127.0.0.1:8080/invocations';
  try {
    const headers: Record<string,string> = {'Content-Type':'application/json','X-Hw-Agentarts-Session-Id':chat};
    if (process.env.CAPLAB_RUNTIME_TOKEN) headers.Authorization = 'Bearer ' + process.env.CAPLAB_RUNTIME_TOKEN;
    else if (new URL(endpoint).hostname === '127.0.0.1') {
      const dataDir = process.env.CAPLAB_LOCAL_DATA || path.resolve(process.cwd(),'../../agentarts-caplab/.cache');
      const localToken = await readFile(path.join(dataDir,'gateway.token'),'utf8');
      headers.Authorization = 'Bearer ' + localToken.trim();
    }
    const steps = action === 'message' ? database().prepare('SELECT goal,title,done FROM steps WHERE owner=? AND chat=?').all(user.id,chat) : [];
    const upstream = await fetch(endpoint,{method:'POST', headers, cache:'no-store', signal:AbortSignal.timeout(100000),
      body:JSON.stringify({action, session_id:chat, _server_user_id:user.id, steps, message, decision, token, confirmation_text})});
    if (!upstream.ok) throw Error();
    const data = await upstream.json();
    if (data.status !== 'success') return Response.json({error:data.response || '本轮未保存，请查看当前草稿'}, {status:409});
    return Response.json(data);
  } catch { return Response.json({error:'暂时无法连接 CapLab 智能体，请检查后端服务后重试。'}, {status:502}); }
}
