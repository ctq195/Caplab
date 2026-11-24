import { database, identity } from '@/lib/demo-auth';

export async function POST(request: Request) {
  const user = await identity();
  if (!user || request.headers.get('x-caplab-owner') !== user.id) return Response.json(null,{status:401});
  const {kind,data} = await request.json();
  if (!['resume','chats'].includes(kind)) return Response.json(null,{status:400});
  const db = database();
  if (data !== undefined) {
    db.prepare('INSERT INTO drafts VALUES (?,?,?) ON CONFLICT(owner,kind) DO UPDATE SET data=excluded.data').run(user.id,kind,JSON.stringify(data));
    return Response.json(true);
  }
  const row = db.prepare('SELECT data FROM drafts WHERE owner=? AND kind=?').get(user.id,kind);
  return Response.json(row ? JSON.parse(String(row.data)) : null);
}
