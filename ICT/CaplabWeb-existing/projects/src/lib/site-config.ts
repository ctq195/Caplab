import {
  BookOpenText,
  ClipboardCheck,
  Compass,
  FileUser,
  GitMerge,
  MessagesSquare,
  FlaskConical,
  type LucideIcon,
} from 'lucide-react';

export const STAGES = [
  { short: '建档', full: '资料建档', href: '/chat', icon: Compass },
  { short: '画像', full: '画像确认', href: '/chat', icon: FlaskConical },
  { short: '收敛', full: '路径收敛', href: '/path-convergence', icon: GitMerge },
  { short: '回合', full: '证据回合', href: '/evidence-cycle', icon: FlaskConical },
  { short: '复盘', full: '证据复盘', href: '/review-report', icon: ClipboardCheck },
] as const satisfies ReadonlyArray<{
  short: string;
  full: string;
  href: string;
  icon: LucideIcon;
}>;

export const NAV_ITEMS = [
  { href: '/', label: '开场' },
  { href: '/chat', label: '对话工作台' },
  { href: '/path-convergence', label: '路径收敛' },
  { href: '/evidence-cycle', label: '证据回合' },
  { href: '/resume', label: '简历工坊' },
  { href: '/interview', label: '模拟面试' },
  { href: '/review-report', label: '复盘报告' },
] as const;

export const CAPABILITIES = [
  {
    id: 'cap-resume',
    href: '/resume',
    icon: FileUser,
    title: '简历工坊',
    desc: 'JD 定制、逐字段来源绑定、拒绝无来源数字',
  },
  {
    id: 'cap-interview',
    href: '/interview',
    icon: MessagesSquare,
    title: '模拟面试',
    desc: '连环追问贡献边界，四维反馈',
  },
  {
    id: 'cap-knowledge',
    href: '/chat',
    icon: BookOpenText,
    title: '知识库问答',
    desc: '考研 / 考公 / 留学 / 求职实习的规则与时间线，带来源与核验日期',
  },
] as const satisfies ReadonlyArray<{
  id: string;
  href: string;
  icon: LucideIcon;
  title: string;
  desc: string;
}>;

export function isActivePath(pathname: string | null, href: string) {
  if (!pathname) return false;
  return href === '/' ? pathname === '/' : pathname.startsWith(href);
}
