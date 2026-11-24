export async function privateDraft(owner: string, kind: 'chats' | 'resume', data?: unknown) {
  const res = await fetch('/api/draft',{method:'POST',headers:{'Content-Type':'application/json','x-caplab-owner':owner},body:JSON.stringify({kind,data})});
  if (!res.ok) throw Error('读取或保存个人草稿失败');
  return res.json();
}
