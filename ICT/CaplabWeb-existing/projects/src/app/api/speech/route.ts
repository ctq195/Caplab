import { isVoiceOriginAllowed } from '@/lib/voice-origin';

export async function POST(request: Request) {
  if (!isVoiceOriginAllowed(request)) return Response.json({ error: '语音请求来源与当前站点不一致，请从 CapLab 页面重试。' }, { status: 403 });
  const body = await request.json().catch(() => null);
  const text = typeof body?.text === 'string' ? body.text.trim() : '';
  if (!text || text.length > 4000) return Response.json({ error: '语音文本长度无效' }, { status: 400 });
  const key = process.env.MOSS_API_KEY;
  if (!key) return Response.json({ error: '语音服务尚未配置' }, { status: 503 });

  try {
    const audio = await fetch('https://api.mosi.cn/v1/audio/speech', {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'moss-tts-2.0-flash-preview',
        voice_id: '94aa4989-c7e9-5007-ae42-ab401823e6c9',
        input: text, stream: true, stream_format: 'audio', response_format: 'pcm',
      }),
      signal: request.signal,
      cache: 'no-store',
    });
    if (!audio.ok || !audio.body) {
      return Response.json({ error: `语音服务暂时不可用（${audio.status}）` }, { status: 502 });
    }
    return new Response(audio.body, { headers: {
      'Content-Type': 'audio/pcm', 'Cache-Control': 'no-store',
      'X-Sample-Rate': audio.headers.get('x-sample-rate') || '48000',
      'X-Channels': audio.headers.get('x-channels') || '2',
    } });
  } catch {
    return Response.json({ error: '暂时连不上语音服务' }, { status: 502 });
  }
}
