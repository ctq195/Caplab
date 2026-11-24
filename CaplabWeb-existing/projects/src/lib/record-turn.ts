/** Record until the user submits the turn or cancels the call. */
export function recordTurn(
  stream: MediaStream,
  context: AudioContext,
  signal: AbortSignal,
  setFinish: (finish: (() => void) | null) => void,
  onInputLevel: (level: number) => void,
) {
  return new Promise<Blob | null>((resolve, reject) => {
    signal.throwIfAborted();
    const type = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus'].find((format) => MediaRecorder.isTypeSupported(format));
    const recorder = new MediaRecorder(stream, { mimeType: type, audioBitsPerSecond: 96000 });
    const input = context.createMediaStreamSource(stream);
    const meter = context.createAnalyser();
    input.connect(meter);
    const samples = new Float32Array(meter.fftSize);
    const chunks: Blob[] = [];
    let level = 0;

    const stop = () => {
      if (recorder.state === 'recording') recorder.stop();
    };
    const timer = window.setInterval(() => {
      meter.getFloatTimeDomainData(samples);
      let energy = 0;
      for (const sample of samples) energy += sample * sample;
      const rms = Math.sqrt(energy / samples.length);
      const nextLevel = Math.max(0, Math.min(10, Math.round((20 * Math.log10(rms) + 65) / 4.5)));
      const displayedLevel = Math.max(nextLevel, level - 1);
      if (displayedLevel !== level) {
        level = displayedLevel;
        onInputLevel(level);
      }
    }, 80);

    function cleanup() {
      clearInterval(timer);
      setFinish(null);
      onInputLevel(0);
      input.disconnect();
      meter.disconnect();
      signal.removeEventListener('abort', stop);
    }

    recorder.ondataavailable = ({ data }) => { if (data.size) chunks.push(data); };
    recorder.onstop = () => {
      cleanup();
      if (signal.aborted) reject(signal.reason);
      else resolve(chunks.length ? new Blob(chunks, { type: recorder.mimeType }) : null);
    };
    recorder.onerror = () => {
      recorder.onstop = null;
      cleanup();
      reject(new Error('录音中断，请检查麦克风。'));
    };
    signal.addEventListener('abort', stop, { once: true });
    try {
      recorder.start();
      setFinish(stop);
    } catch (error) {
      cleanup();
      reject(error);
    }
  });
}
