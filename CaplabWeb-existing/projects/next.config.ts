import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Next.js 16 默认使用 Turbopack；显式声明以避免与旧 webpack 配置冲突。
  turbopack: {},
  devIndicators: false,
  serverExternalPackages: ['coze-coding-dev-sdk'],
  allowedDevOrigins: ['*.dev.coze.site'],
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*',
        pathname: '/**',
      },
    ],
  },
};

export default nextConfig;
