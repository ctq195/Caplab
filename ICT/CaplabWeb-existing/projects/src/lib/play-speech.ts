const speechPlaybackRate = 1.18;

// Keep incomplete interleaved PCM frames until the next network chunk arrives.
export async function playSpeech(text: string, context: AudioContext, signal: AbortSignal) {
  const response = await fetch('/api/speech', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }), signal,
  });
  if (!response.ok || !response.body) throw new Error('语音播放暂时不可用，可以继续打字。');
  const channels = Number(response.headers.get('x-channels'));
  const rate = Number(response.headers.get('x-sample-rate'));
  if (![1, 2].includes(channels) || rate < 8000 || rate > 96000) throw new Error('音频格式不可用。');
  const reader = response.body.getReader();
  let tail = new Uint8Array(0);
  let end = context.currentTime;
  let last: Promise<void> | undefined;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    signal.throwIfAborted();
    const bytes = new Uint8Array(tail.length + value.length);
    bytes.set(tail);
    bytes.set(value, tail.length);
    const frames = Math.floor(bytes.length / (channels * 2));
    tail = bytes.slice(frames * channels * 2);
    if (!frames) continue;
    const buffer = context.createBuffer(channels, frames, rate);
    const samples = new DataView(bytes.buffer);
    for (let c = 0; c < channels; c++) {
      const output = buffer.getChannelData(c);
      for (let i = 0; i < frames; i++) output[i] = samples.getInt16((i * channels + c) * 2, true) / 32768;
    }
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.playbackRate.value = speechPlaybackRate;
    source.connect(context.destination);
    last = new Promise<void>((resolve) => { source.onended = () => { source.disconnect(); resolve(); }; });
    end = Math.max(end, context.currentTime + 0.015);
    source.start(end);
    end += buffer.duration / speechPlaybackRate;
  }
  if (!last) throw new Error('没有收到语音，可以继续打字。');
  await new Promise<void>((resolve, reject) => {
    const abort = () => reject(new DOMException('Call ended', 'AbortError'));
    if (signal.aborted) return abort();
    signal.addEventListener('abort', abort, { once: true });
    void last?.then(() => { signal.removeEventListener('abort', abort); resolve(); });
  });
}
