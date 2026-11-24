const loopbackLabel = /立体声混音|stereo mix|what u hear|wave out mix|loopback/i;
const microphoneLabel = /麦克风|microphone|mikrofon|microfone|micrófono|\bmic\b/i;

async function listInputs() {
  const devices = await navigator.mediaDevices.enumerateDevices().catch(() => []);
  return devices.filter((device) => device.kind === 'audioinput');
}

function findMicrophone(inputs: MediaDeviceInfo[]) {
  const microphones = inputs.filter((input) => microphoneLabel.test(input.label) && !loopbackLabel.test(input.label));
  return microphones.find((input) => input.deviceId !== 'default' && input.deviceId !== 'communications') ?? microphones[0];
}

function capture(deviceId?: string) {
  return navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: { ideal: 1 },
      ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    },
  });
}

export async function openMicrophone(preferred: string, signal: AbortSignal) {
  let inputs = await listInputs();
  signal.throwIfAborted();
  const defaultInput = inputs.find((input) => input.deviceId === 'default') ?? inputs[0];
  const replacement = !preferred && loopbackLabel.test(defaultInput?.label ?? '') ? findMicrophone(inputs) : undefined;
  const requested = preferred || replacement?.deviceId;
  let stream = await capture(requested);
  try {
    signal.throwIfAborted();
    inputs = await listInputs();
    signal.throwIfAborted();

    // Input labels can be hidden until the first permission grant.
    if (!requested && loopbackLabel.test(stream.getAudioTracks()[0]?.label ?? '')) {
      const microphone = findMicrophone(inputs);
      if (microphone) {
        const initialStream = stream;
        stream = await capture(microphone.deviceId);
        initialStream.getTracks().forEach((track) => track.stop());
      }
    }
    signal.throwIfAborted();
    const track = stream.getAudioTracks()[0];
    return { stream, inputs, deviceId: track.getSettings().deviceId ?? requested ?? '' };
  } catch (error) {
    stream.getTracks().forEach((track) => track.stop());
    throw error;
  }
}
