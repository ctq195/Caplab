import { database, identity } from '@/lib/demo-auth';
import { randomUUID } from 'node:crypto';

export async function POST(request: Request) {
  const user = await identity();
  if (!user || request.headers.get('x-caplab-owner') !== user.id) return Response.json(null,{status:401});
  const {chat,goal,action,titles,id,done} = await request.json();
  if (typeof chat !== 'string' || !/^[\w-]{1,64}$/.test(chat) || typeof goal !== 'string' || !goal.trim()) return Response.json(null,{status:400});
  const db = database();
  const key = [user.id,chat,goal];
  const list = () => db.prepare('SELECT id,title,done FROM steps WHERE owner=? AND chat=? AND goal=? ORDER BY rowid').all(...key);
  if (action === 'plan') {
    if (!Array.isArray(titles) || !titles.length || titles.length > 20 || titles.some(t => typeof t !== 'string' || !t.trim() || t.length > 200)) return Response.json(null,{status:400});
    db.exec('BEGIN IMMEDIATE');
    try {
      if (!list().length) {
        const add = db.prepare('INSERT INTO steps(id,owner,chat,goal,title) VALUES (?,?,?,?,?)');
        for (const title of titles) add.run(randomUUID(),...key,title.trim());
      }
      db.exec('COMMIT');
    } catch (error) { db.exec('ROLLBACK'); throw error; }
  } else if (action === 'mark' && typeof done === 'boolean' && typeof id === 'string') {
    db.prepare('UPDATE steps SET done=? WHERE owner=? AND chat=? AND goal=? AND id=?').run(Number(done),...key,id);
  } else if (action !== 'read') return Response.json(null,{status:400});
  return Response.json(list());
}
