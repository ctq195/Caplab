import { isVoiceOriginAllowed } from '@/lib/voice-origin';

export async function POST(request: Request) {
  if (!isVoiceOriginAllowed(request)) return Response.json({ error: '语音请求来源与当前站点不一致，请从 CapLab 页面重试。' }, { status: 403 });
  const key = process.env.MOSS_API_KEY;
  if (!key) return Response.json({ error: '语音识别尚未配置，可以先打字。' }, { status: 503 });
  const limit = 8 * 1024 * 1024;
  if (Number(request.headers.get('content-length')) > limit) return Response.json({ error: '录音超过 8 MB，请分段说。' }, { status: 413 });
  const type = (request.headers.get('content-type') || '').split(';')[0];
  const formats: Record<string, string> = { 'audio/webm': 'webm', 'audio/mp4': 'm4a', 'audio/ogg': 'ogg', 'audio/wav': 'wav' };
  if (!Object.hasOwn(formats, type)) return Response.json({ error: '当前录音格式无法识别，请更换浏览器后重试。' }, { status: 415 });
  const clip = await request.blob();
  if (!clip.size) return Response.json({ error: '录音为空，请检查麦克风后再试。' }, { status: 400 });
  if (clip.size > limit) return Response.json({ error: '录音超过 8 MB，请分段说。' }, { status: 413 });
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
