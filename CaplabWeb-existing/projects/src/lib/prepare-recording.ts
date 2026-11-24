const sampleRate = 16000;

/** Keep the entire turn, including pauses, and optimize its level for transcription. */
export async function prepareRecording(clip: Blob) {
  let audio: AudioBuffer;
  try {
    audio = await new OfflineAudioContext(1, 1, sampleRate).decodeAudioData(await clip.arrayBuffer());
  } catch {
    // Some browsers can record formats that their Web Audio decoder cannot read.
    return clip;
  }

  const channels = Array.from({ length: audio.numberOfChannels }, (_, index) => audio.getChannelData(index));
  const pcm = new Float32Array(audio.length);
  let peak = 0;
  // Pick the strongest channel to avoid attenuating speech when one channel is silent.
  for (const channel of channels) {
    let channelPeak = 0;
    for (const sample of channel) channelPeak = Math.max(channelPeak, Math.abs(sample));
    if (channelPeak > peak) {
      pcm.set(channel);
      peak = channelPeak;
    }
  }
  if (peak < 0.0003) return null;

  const gain = Math.max(1, Math.min(20, 0.7 / peak));
  const wav = new ArrayBuffer(44 + pcm.length * 2);
  const bytes = new DataView(wav);
  bytes.setUint32(0, 0x52494646); // RIFF
  bytes.setUint32(4, wav.byteLength - 8, true);
  bytes.setUint32(8, 0x57415645); // WAVE
  bytes.setUint32(12, 0x666d7420); // fmt
  bytes.setUint32(16, 16, true);
  bytes.setUint16(20, 1, true); // PCM
  bytes.setUint16(22, 1, true); // mono
  bytes.setUint32(24, sampleRate, true);
  bytes.setUint32(28, sampleRate * 2, true);
  bytes.setUint16(32, 2, true);
  bytes.setUint16(34, 16, true);
  bytes.setUint32(36, 0x64617461); // data
  bytes.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) {
    const sample = Math.max(-1, Math.min(1, pcm[i] * gain));
    bytes.setInt16(44 + 2 * i, Math.round(sample * 32767), true);
  }
  const normalized = new Blob([wav], { type: 'audio/wav' });
  // For unusually long turns, keep the smaller original encoding.
  return normalized.size <= 8 * 1024 * 1024 ? normalized : clip;
}
