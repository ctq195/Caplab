/** Next.js can construct request.url with localhost even when the browser used 127.0.0.1. */
export function isVoiceOriginAllowed(request: Request) {
  const origin = request.headers.get('origin');
  if (!origin) return true;
  const url = new URL(request.url);
  const host = request.headers.get('host') ?? url.host;
  return origin === `${url.protocol}//${host}`;
}
