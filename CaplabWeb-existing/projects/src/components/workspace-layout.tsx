import { SiteHeader } from '@/components/site-header';
import { SiteFooter } from '@/components/site-footer';

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SiteHeader />
      <div className="flex min-h-[calc(100vh-4rem)] flex-col">
        <div className="flex-1">{children}</div>
        <SiteFooter />
      </div>
    </>
  );
}
