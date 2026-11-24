import type { Metadata, Viewport } from 'next';
import './globals.css';
import { AccountGate } from '@/components/account-gate';

export const metadata: Metadata = {
  title: {
    default: 'CapLab - AI 生涯路径收敛平台',
    template: '%s | CapLab',
  },
  description:
    '面向大学生的 AI 生涯路径收敛平台。不替你做终身决定，而是用低成本现实行动验证选择。',
  keywords: ['CapLab', '生涯规划', '大学生', '路径收敛', '证据化决策'],
  applicationName: 'CapLab',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#31503b',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        <a
          href="#main-content"
          className="no-print sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
        >
          跳转到主要内容
        </a>
        <div id="main-content"><AccountGate>{children}</AccountGate></div>
      </body>
    </html>
  );
}
