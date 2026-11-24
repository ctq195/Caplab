import { NextRequest } from 'next/server';

export const runtime = 'nodejs';

interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

const SYSTEM_PROMPT = `你是 CapLab，陪中国大学生聊选专业、考研、实习和找工作。用自然、具体的中文，像一个认真听人说话、也懂生涯选择的同伴。

先回应对方眼下在问什么。能回答就直接答。对方想听建议时，可以从已经说过的情况出发，给一个有条件的建议，或讲清两种选择各适合什么人。需要了解背景时，先把手上能说清楚的讲明白，再直接问一个具体问题，例如“哪门课你上着比较有劲？” 问完就停，省去解释为什么要问。对方想先看几个方向时，挑两三个就好，说说平时会学什么、做什么。只有一句话或一句问候时，可以轻松接一句。

平常聊天用口语和短段落，几句够用就停。跳过“信息还不够”“我不会先给你推荐”这样的铺垫。把建档、画像、证据闭环等流程留在后台，别把流程标签、待核验清单或固定的“下一步”段落念给对方。已有对话用来理解上下文，别沿用旧回复的套话。对方明确要表格、详细比较或计划时，按对方要的形式写。

对方在倾诉时，接住他们提到的那件事。对方只是想说说，可以聊到那里就停。别急着布置任务、反复追问或替对方定义感受。对方想行动时，可以提一件这几天做得了的事，比如翻两门课的课程表，或者问做过实习的同学一天在忙什么。给建议时尊重对方自己的选择。

事实和你的判断要说清楚。用“听起来你更在意……”或“如果你更在意……，我会先看……”这类自然说法。别捏造经历、出处、案例、薪资、报考条件或时间。涉及具体政策和日期，只引用当前确有的来源。没有可核实的时间，可以告诉对方去哪一份官方通知里找。写简历只用对方真实做过的事，表达可以改，数字与成果要有来源。

遇到自伤、伤人或即时危险，先关心对方现在是否安全，温和地建议联系身边可信任的人、学校心理中心或紧急求助。暂停生涯建议，不做诊断。`;

const VOICE_PROMPT = `当前正在语音通话。回答适合念出来，通常两三句，用口语和自然的停顿。顺着对方刚说的事接话，语气轻快、真诚。肯定对方时说清哪一点值得肯定。需要问就问一个，聊完也可以自然停住。遇到危机时语气平稳。不要使用 Markdown。`;

export async function POST(req: NextRequest) {
  let body: { messages?: ChatMessage[]; message?: string; voice?: boolean };
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: '请求体不是合法 JSON' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const apiKey = process.env.DEEPSEEK_API_KEY;
  const baseUrl = process.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com';
  const model = process.env.DEEPSEEK_MODEL || 'deepseek-flash';

  if (!apiKey) {
    return new Response(
      JSON.stringify({
        error: '尚未配置 DEEPSEEK_API_KEY，无法调用模型。请在环境变量中配置后重试。',
      }),
      { status: 503, headers: { 'Content-Type': 'application/json' } },
    );
  }

  // 组装消息：兼容 {messages:[...]} 与 {message:"..."}
  const history: ChatMessage[] = Array.isArray(body.messages)
    ? body.messages.filter((m) => m && typeof m.content === 'string' && m.content.trim())
    : [];
  if (history.length === 0 && body.message) {
    history.push({ role: 'user', content: body.message });
  }
  if (history.length === 0) {
    return new Response(JSON.stringify({ error: 'messages 或 message 不能为空' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const payload = {
    model,
    messages: [{ role: 'system', content: body.voice ? `${SYSTEM_PROMPT}\n\n${VOICE_PROMPT}` : SYSTEM_PROMPT }, ...history],
    stream: true,
    ...(body.voice ? { max_tokens: 350 } : {}),
    temperature: 0.7,
  };

  let upstream: Response;
  try {
    upstream = await fetch(`${baseUrl.replace(/\/$/, '')}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(payload),
      signal: req.signal,
    });
  } catch (e) {
    return new Response(
      JSON.stringify({ error: `模型服务请求失败：${e instanceof Error ? e.message : '未知错误'}` }),
      { status: 502, headers: { 'Content-Type': 'application/json' } },
    );
  }

  if (!upstream.ok || !upstream.body) {
    const errText = await upstream.text().catch(() => '');
    return new Response(
      JSON.stringify({ error: `模型服务返回 ${upstream.status}`, detail: errText.slice(0, 500) }),
      { status: upstream.status || 502, headers: { 'Content-Type': 'application/json' } },
    );
  }

  // SSE 透传：把 OpenAI 兼容的 SSE chunk 原样转成 text/event-stream
  const encoder = new TextEncoder();
  const reader = upstream.body.getReader();

  let cancelled = false;
  const stream = new ReadableStream({
    async start(controller) {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done || cancelled) break;
          controller.enqueue(value);
        }
      } catch (e) {
        if (cancelled) return;
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ error: e instanceof Error ? e.message : '流中断' })}\n\n`,
          ),
        );
      } finally {
        if (!cancelled) {
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        }
      }
    },
    cancel() {
      cancelled = true;
      reader.cancel().catch(() => {});
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}

export async function GET() {
  return new Response(
    JSON.stringify({
      name: 'CapLab 对话 API',
      version: '2.0.0-streaming',
      model: process.env.DEEPSEEK_MODEL || 'deepseek-flash',
      configured: Boolean(process.env.DEEPSEEK_API_KEY),
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
}
