import { cookies } from 'next/headers';
import { createHash, randomBytes, randomUUID, scryptSync, timingSafeEqual } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

export type Identity = { id: string; name: string | null };
const cookieName = 'caplab_session';
const sessionDays = 14;
let connection: DatabaseSync | undefined;

export function database() {
  if (connection) return connection;
  const dir = process.env.CAPLAB_DEMO_DATA || path.join(process.cwd(), '.cache', 'caplab');
  mkdirSync(dir, { recursive: true });
  const db = new DatabaseSync(path.join(dir, 'sessions.sqlite'));
  db.exec(`PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT UNIQUE, salt TEXT, password_hash BLOB);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, owner TEXT NOT NULL, expires INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS steps(id TEXT PRIMARY KEY, owner TEXT, chat TEXT, goal TEXT, title TEXT, done INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS drafts(owner TEXT, kind TEXT, data TEXT, PRIMARY KEY(owner, kind));`);
  connection = db;
  return db;
}
const digest = (value: string) => createHash('sha256').update(value).digest('hex');

export async function identity(): Promise<Identity | null> {
  const token = (await cookies()).get(cookieName)?.value;
  if (!token) return null;
  const row = database().prepare('SELECT id,name FROM sessions JOIN users ON owner=id WHERE token=? AND expires>?').get(digest(token), Date.now());
  return row ? { id: String(row.id), name: row.name == null ? null : String(row.name) } : null;
}

export async function logout() {
  const jar = await cookies();
  const token = jar.get(cookieName)?.value;
  if (token) database().prepare('DELETE FROM sessions WHERE token=?').run(digest(token));
  jar.delete(cookieName);
}

export async function login(name: string | null, password: string, secure: boolean) {
  const db = database();
  let id = randomUUID() as string;
  if (name !== null) {
    const row = db.prepare('SELECT id,salt,password_hash FROM users WHERE name=?').get(name);
    if (row) {
      if (!timingSafeEqual(scryptSync(password, String(row.salt), 32), Buffer.from(row.password_hash as Uint8Array))) return false;
      id = String(row.id);
    } else {
      const salt = randomBytes(16).toString('hex');
      db.prepare('INSERT INTO users VALUES (?,?,?,?)').run(id, name, salt, scryptSync(password, salt, 32));
    }
  } else db.prepare('INSERT INTO users(id) VALUES (?)').run(id);
  await logout();
  const token = randomBytes(32).toString('hex');
  db.prepare('INSERT INTO sessions VALUES (?,?,?)').run(digest(token), id, Date.now() + sessionDays * 86400000);
  (await cookies()).set(cookieName, token, { httpOnly: true, sameSite: 'lax', path: '/', secure, maxAge: sessionDays * 86400 });
  return true;
}
