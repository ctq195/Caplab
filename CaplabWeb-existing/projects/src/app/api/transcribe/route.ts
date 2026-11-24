export async function POST(request: Request) {
  const origin = request.headers.get('origin');
  if (origin && origin !== new URL(request.url).origin) return new Response(null, { status: 403 });
  const key = process.env.MOSS_API_KEY;
  if (!key) return Response.json({ error: '语音识别尚未配置，可以先打字。' }, { status: 503 });
  const limit = 8 * 1024 * 1024;
  if (Number(request.headers.get('content-length')) > limit) return new Response(null, { status: 413 });
  const type = (request.headers.get('content-type') || '').split(';')[0];
  const formats: Record<string, string> = { 'audio/webm': 'webm', 'audio/mp4': 'm4a', 'audio/ogg': 'ogg', 'audio/wav': 'wav' };
  if (!Object.hasOwn(formats, type)) return new Response(null, { status: 415 });
  const clip = await request.blob();
  if (!clip.size || clip.size > limit) return new Response(null, { status: clip.size ? 413 : 400 });
  const form = new FormData();
  form.set('file', clip, 'utterance.' + formats[type]);
  form.set('model', 'moss-transcribe-diarize-pro');
  try {
    const response = await fetch('https://api.mosi.cn/v1/audio/transcriptions', {
      method: 'POST', headers: { Authorization: 'Bearer ' + key },
      body: form, signal: request.signal, cache: 'no-store',
    });
    if (!response.ok) return Response.json({ error: '语音识别服务暂时不可用（' + response.status + '）。' }, { status: 502 });
    const result = await response.json();
    return Response.json({ text: typeof result.text === 'string' ? result.text.trim() : '' }, { headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return Response.json({ error: '未能连接语音识别服务，请重试。' }, { status: 502 });
  }
}
