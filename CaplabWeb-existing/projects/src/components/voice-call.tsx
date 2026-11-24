'use client';

import { useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { ArrowUp, AudioLines, Phone, PhoneOff } from 'lucide-react';
import Link from 'next/link';
import { openMicrophone } from '@/lib/open-microphone';
import { prepareRecording } from '@/lib/prepare-recording';
import { recordTurn } from '@/lib/record-turn';
import { playSpeech } from '@/lib/play-speech';

type CallPhase = 'idle' | 'connecting' | 'recording' | 'transcribing' | 'thinking' | 'speaking' | 'muted';

const callStatus = {
  idle: '今天想聊点什么？',
  connecting: '正在连接…',
  recording: '我在听',
  transcribing: '正在转写…',
  thinking: '正在想你的问题…',
  speaking: 'CapLab 正在说',
  muted: '收音已暂停',
} satisfies Record<CallPhase, string>;

const greeting = '嗨，我在！今天想聊点什么？';

export function VoiceCall({ ref, reply, cancelReply, openText, historyControl }: {
  ref?: React.Ref<{ start: () => void }>;
  historyControl: React.ReactNode;
  reply: (text: string) => Promise<string | undefined>;
  cancelReply: () => void;
  openText: (draft: string, send?: boolean) => void;
}) {
  const [draft, setDraft] = useState('');
  const [phase, setPhase] = useState<CallPhase>('idle');
  const [inputLevel, setInputLevel] = useState(0);
  const [inputMuted, setInputMuted] = useState(false);
  const [microphones, setMicrophones] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState('');
  const preferredMicrophone = useRef('');
  const [transcript, setTranscript] = useState('');
  const [answer, setAnswer] = useState('');
  const [caption, setCaption] = useState('');
  const [issue, setIssue] = useState('');
  const session = useRef<AbortController | null>(null);
  const audio = useRef<AudioContext | null>(null);
  const trackStream = useRef<MediaStream | null>(null);
  const finish = useRef<(() => void) | null>(null);
  const callbacks = useRef({ reply, cancelReply });
  useEffect(() => { callbacks.current = { reply, cancelReply }; }, [reply, cancelReply]);

  const release = useCallback(() => {
    if (!session.current) return;
    session.current.abort();
    session.current = null;
    callbacks.current.cancelReply();
    trackStream.current?.getTracks().forEach((track) => track.stop());
    trackStream.current = null;
    finish.current = null;
    if (audio.current) {
      const context = audio.current;
      audio.current = null;
      if (context.state !== 'closed') context.close().catch(() => {});
    }
  }, []);
  useEffect(() => release, [release]);

  async function start(shouldGreet = true) {
    if (session.current) return;
    setIssue('');
    setCaption('');
    setInputLevel(0);
    setInputMuted(false);
    if (shouldGreet) {
      setTranscript('');
      setAnswer('');
    }
    if (!window.AudioContext || !navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setIssue('当前浏览器无法录音。请用支持麦克风的浏览器打开，或继续打字。');
      return;
    }
    const controller = new AbortController();
    session.current = controller;
    const { signal } = controller;
    function fail(message: string) {
      if (signal.aborted) return;
      release();
      setPhase('idle');
      setIssue(message);
    }

    try {
      const context = new AudioContext();
      audio.current = context;
      setPhase('connecting');
      // The submit button can unlock playback if navigation started the call before a user gesture.
      void context.resume().catch(() => {});
      const { stream, inputs, deviceId: selectedDevice } = await openMicrophone(preferredMicrophone.current, signal);
      if (signal.aborted) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      trackStream.current = stream;
      const tracks = stream.getAudioTracks();
      const track = tracks[0];
      setDeviceId(selectedDevice);
      setMicrophones(inputs);
      setInputMuted(track.muted);
      track.addEventListener('mute', () => setInputMuted(true), { signal });
      track.addEventListener('unmute', () => setInputMuted(false), { signal });
      track.addEventListener('ended', () => fail('麦克风已断开，请选择一个可用的麦克风后重试。'), { signal });

      async function speak(text: string) {
        if (context.state !== 'running') {
          setIssue('浏览器没有启用声音，请先看文字回复。');
          return;
        }
        try {
          await playSpeech(text, context, signal);
        } catch (error) {
          if (signal.aborted) throw error;
          setIssue('语音播放暂时不可用，先看文字回复。');
        }
      }

      if (shouldGreet && context.state === 'running') {
        tracks.forEach((track) => { track.enabled = false; });
        setCaption(greeting);
        setPhase('speaking');
        await speak(greeting);
      }

      let prompt = '说完后点「说完了」，你可以慢慢说。';
      while (!signal.aborted) {
        tracks.forEach((track) => { track.enabled = true; });
        setCaption(prompt);
        setPhase('recording');
        const clip = await recordTurn(
          stream,
          context,
          signal,
          (stop) => { if (!signal.aborted) finish.current = stop; },
          (level) => { if (!signal.aborted) setInputLevel(level); },
        );
        if (signal.aborted) return;
        if (!clip) {
          prompt = '这次没有录到声音，请再说一次。';
          continue;
        }

        tracks.forEach((track) => { track.enabled = false; });
        setCaption('');
        setPhase('transcribing');
        const recording = await prepareRecording(clip);
        if (signal.aborted) return;
        if (!recording) {
          prompt = '这次录音是静音。请检查系统是否将麦克风静音，或切换麦克风后再说。';
          continue;
        }
        const response = await fetch('/api/transcribe', { method: 'POST', body: recording, signal });
        const result = await response.json().catch(() => null) as { text?: string; error?: string } | null;
        if (signal.aborted) return;
        if (!response.ok) {
          setIssue(result?.error || '这次语音转写失败，请再说一次。');
          continue;
        }
        const text = result?.text?.trim();
        if (!text) {
          prompt = '收到了声音，但没有转写出文字。请靠近麦克风再说一次。';
          continue;
        }

        setTranscript(text);
        setAnswer('');
        setPhase('thinking');
        const replyText = await callbacks.current.reply(text);
        if (signal.aborted) return;
        if (!replyText) {
          setIssue('这次没有收到回复，可以再试一次。');
          continue;
        }
        setAnswer(replyText);
        setPhase('speaking');
        await speak(replyText);
        prompt = '轮到你说了。说完后点「说完了」。';
      }
    } catch (error) {
      if (signal.aborted) return;
      const message = error instanceof Error ? error.message : '通话中断，请重试。';
      const name = error instanceof DOMException ? error.name : '';
      if (name === 'NotAllowedError') fail('未获得麦克风权限。请在浏览器中允许麦克风，或继续打字。');
      else if (name === 'NotFoundError' || name === 'OverconstrainedError') {
        setDeviceId('');
        preferredMicrophone.current = '';
        fail('找不到选中的麦克风。请检查设备，再重新发起通话。');
      } else if (name === 'NotReadableError') fail('麦克风无法读取。请检查系统输入设置，再重新发起通话。');
      else fail(message);
    }
  }

  function submitRecording() {
    const stop = finish.current;
    if (!stop) return;
    finish.current = null;
    void audio.current?.resume().catch(() => {});
    setInputLevel(0);
    setIssue('');
    setCaption('');
    setPhase('transcribing');
    stop();
  }

  useImperativeHandle(ref, () => ({ start: () => { void start(); } }));

  const active = phase !== 'idle';
  return (
    <main className="voice-entry flex min-h-dvh flex-col px-6 py-7 text-center">
      <header className="mx-auto flex w-full max-w-md items-center justify-between">
        <Link href="/" aria-label="返回 CapLab 首页" className="flex items-center gap-2 font-semibold text-primary"><AudioLines size={20} /> CapLab</Link>
        {historyControl}
      </header>
      <section className={`mx-auto my-auto flex w-full max-w-md flex-col items-center ${active ? "py-6" : "py-12"}`}>
        <div aria-hidden="true" className={`voice-orb ${active ? "!w-32" : ""} ${(phase === 'recording' && inputLevel > 0) || phase === 'speaking' ? 'voice-orb-active' : ''}`}><AudioLines size={46} strokeWidth={1.4} /></div>
        <h1 className="mt-9 font-serif text-4xl leading-tight text-foreground" aria-live="polite">{callStatus[phase]}</h1>
        <p className="mt-4 text-base leading-7 text-muted-foreground empty:hidden">
          {active ? caption : '考研、实习、找工作，都可以聊。'}
        </p>
        {phase === 'recording' && (
          <div className="mt-3 flex w-full max-w-xs flex-col items-center gap-2 text-sm text-primary">
            <p>{inputMuted ? '浏览器未收到麦克风信号' : inputLevel > 0 ? '正在收音' : '麦克风已开启 · 等待声音'}</p>
            <meter className="h-3 w-36 accent-primary" min={0} max={10} value={inputLevel} aria-label="麦克风实时音量" />
            {microphones.length > 0 && (
              <label className="flex w-full items-center justify-center gap-2 text-muted-foreground">
                <span className="shrink-0">麦克风</span>
                <select className="min-w-0 rounded-lg border border-border bg-card px-2 py-1.5 text-foreground" value={deviceId} onChange={(event) => {
                  preferredMicrophone.current = event.target.value;
                  release();
                  void start(false);
                }}>
                  {microphones.map((device, index) => (
                    <option key={device.deviceId} value={device.deviceId}>{device.label || `麦克风 ${index + 1}`}</option>
                  ))}
                </select>
              </label>
            )}
          </div>
        )}
        {(transcript || answer) && (
          <div className="mt-5 max-h-[30dvh] w-full space-y-3 overflow-y-auto rounded-2xl border border-border bg-card p-4 text-left text-sm leading-relaxed" aria-live="polite">
            {transcript && <p><strong className="mr-2 text-primary">转写</strong>{transcript}</p>}
            {answer && <p><strong className="mr-2 text-primary">CapLab</strong>{answer}</p>}
          </div>
        )}
        {issue && <p role="alert" className="mt-4 text-sm text-muted-foreground">{issue}</p>}
        {active ? (
          <>
            {phase === 'recording' && <button type="button" className="btn-primary mt-6 min-w-40" onClick={submitRecording}>说完了</button>}
            <button type="button" className="btn-ghost mt-3 text-destructive" onClick={() => { release(); setPhase('idle'); setCaption(''); }}>
              <PhoneOff size={18} /> 挂断
            </button>
            <div className="mt-2 flex flex-wrap justify-center gap-2">
              {phase === 'recording' && <button className="btn-ghost" onClick={() => { release(); setPhase('muted'); }}>暂停收音</button>}
              {phase === 'muted' && <button className="btn-ghost" onClick={() => { void start(false); }}>继续收音</button>}
              {(phase === 'thinking' || phase === 'speaking') && <button className="btn-ghost" onClick={() => { release(); void start(false); }}>打断，换我说</button>}
              <button className="btn-ghost" onClick={() => { release(); openText(''); }}>打字聊</button>
            </div>
          </>
        ) : (
          <form className="mt-7 w-full rounded-3xl border border-border bg-card p-3 text-left shadow-card focus-within:border-primary" onSubmit={(event) => {
            event.preventDefault();
            if (draft.trim()) openText(draft.trim(), true);
          }}>
            <textarea aria-label="你想聊什么" rows={2} value={draft} onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  if (draft.trim()) openText(draft.trim(), true);
                }
              }}
              placeholder="想聊什么？" className="block w-full resize-none bg-transparent px-2 py-1 text-base leading-7 focus-visible:outline-none" />
            <div className="mt-2 flex items-center justify-between">
              <button type="button" className="btn-ghost" onClick={() => { void start(); }}><Phone size={16} /> 语音通话</button>
              <button type="submit" aria-label="发送消息" disabled={!draft.trim()} className="btn-primary !min-h-11 !px-4"><ArrowUp size={17} />发送</button>
            </div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">语音通话会使用麦克风，点「说完了」后由 MOSS 转写。</p>
          </form>
        )}
      </section>
    </main>
  );
}
