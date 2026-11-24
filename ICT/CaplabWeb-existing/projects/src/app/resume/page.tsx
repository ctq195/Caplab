'use client';
import { useOwner } from '@/components/account-gate';
import { privateDraft } from '@/lib/private-draft';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowDownToLine, FileUser, Plus, Printer, Upload } from 'lucide-react';
import { PageShell } from '@/components/page-shell';
import { basicFields, editableSections, emptyResume, newResumeItem, parseResume, plainText, readSection, resumeText, richText, sections, type SectionId } from '@/lib/resume-document';

const fieldClass = 'w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm';

export default function ResumePage() {
  const owner = useOwner();
  const [resume, setResume] = useState(emptyResume);
  const [ready, setReady] = useState(false);
  const [notice, setNotice] = useState('');
  useEffect(() => {
    let active = true;
    privateDraft(owner,'resume').then(saved => {
      if (!active) return;
      if (saved) setResume(parseResume(saved));
      setReady(true);
    }).catch(() => setNotice('读取个人草稿失败，请刷新重试。'));
    return () => { active = false; };
  }, [owner]);
  useEffect(() => {
    if (!ready) return;
    void privateDraft(owner,'resume',resume).catch(() => setNotice('草稿未保存，请导出 JSON 保留。'));
  }, [resume, ready, owner]);

  const summary = readSection(resume, 'summary');
  const preview = resumeText(resume, true);
  const updateSection = (id: SectionId, getItems: (items: ReturnType<typeof readSection>['items']) => ReturnType<typeof readSection>['items']) => {
    setResume((previous) => {
      const section = readSection(previous, id);
      return { ...previous, sections: { ...previous.sections, [id]: { ...section, items: getItems(section.items) } } };
    });
  };

  async function importResume(file?: File) {
    if (!file) return;
    try {
      const data = parseResume(JSON.parse(await file.text()));
      setResume(data);
      setNotice('已导入 Reactive Resume 简历，核对后即可继续编辑。');
    } catch {
      setNotice('无法读取此文件，请选择 Reactive Resume v4 导出的 JSON。');
    }
  }

  function exportResume() {
    const href = URL.createObjectURL(new Blob([JSON.stringify(resume, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = href;
    link.download = 'CapLab-简历.json';
    link.click();
    URL.revokeObjectURL(href);
  }

  return (
    <PageShell icon={FileUser} eyebrow="求职准备" title="简历工坊"
      description="填写真实经历，右侧会同步更新。也可以导入 Reactive Resume 导出的 JSON，继续编辑并保存。"
      actions={<>
        <label className="btn-secondary cursor-pointer"><Upload size={16} /> 导入 JSON
          <input type="file" accept=".json,application/json" disabled={!ready} className="sr-only" onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = '';
            void importResume(file);
          }} />
        </label>
        <button className="btn-secondary" onClick={exportResume} disabled={!ready}><ArrowDownToLine size={16} /> 导出 JSON</button>
        <button className="btn-primary" onClick={() => window.print()} disabled={!preview}><Printer size={16} /> 打印 / 保存 PDF</button>
      </>}>
      {notice && <p role="status" className="mb-4 text-sm text-primary">{notice}</p>}
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="space-y-4 no-print">
          <section className="rounded-2xl border bg-card p-5">
            <h2 className="mb-4 text-lg font-semibold">基本资料</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {basicFields.map(([key, label]) => (
                <label key={key} className="space-y-1.5 text-sm">
                  <span>{label}</span>
                  <input className={fieldClass} type={key === 'email' ? 'email' : 'text'} value={plainText(resume.basics[key])}
                    onChange={(event) => setResume({ ...resume, basics: { ...resume.basics, [key]: event.target.value } })} />
                </label>
              ))}
            </div>
            <label className="mt-4 block space-y-1.5 text-sm">
              <span>个人简介</span>
              <textarea aria-label="个人简介" rows={3} className={fieldClass} value={plainText(summary.content)} onChange={(event) => {
                setResume({ ...resume, sections: { ...resume.sections, summary: { ...summary, content: richText(event.target.value) } } });
              }} />
            </label>
          </section>
          {editableSections(resume).map((id) => {
            const [title, ...fields] = sections[id] as readonly [string, ...Array<readonly [string, string]>];
            return (
              <section key={id} className="space-y-3 rounded-2xl border bg-card p-5">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-lg font-semibold">{title}</h2>
                  <button className="btn-ghost" aria-label={`添加${title}`} onClick={() => updateSection(id, (items) => [...(items ?? []), newResumeItem(id)])}><Plus size={16} />添加</button>
                </div>
                {readSection(resume, id).items?.map((item, index) => (
                  <fieldset key={item.id} className="space-y-3 rounded-xl border p-3">
                    <legend className="px-1 text-xs text-muted-foreground">{title} {index + 1}</legend>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {fields.map(([key, label]) => <label key={key} className="space-y-1.5 text-sm">
                        <span>{label}</span>
                        <input className={fieldClass} value={plainText(item[key])} onChange={(event) => {
                          const value = event.target.value;
                          updateSection(id, (items) => items?.map((row, rowIndex) => rowIndex === index
                            ? { ...row, [key]: key === 'keywords' ? value.split(/[、,，]/) : value } : row));
                        }} />
                      </label>)}
                    </div>
                    {'summary' in item && <label className="block space-y-1.5 text-sm">
                      <span>实际做过的事与结果</span>
                      <textarea className={fieldClass} rows={3} value={plainText(item.summary)} onChange={(event) => {
                        const value = event.target.value;
                        updateSection(id, (items) => items?.map((row, rowIndex) => rowIndex === index ? { ...row, summary: richText(value) } : row));
                      }} />
                    </label>}
                    <button type="button" className="text-sm text-destructive hover:underline" onClick={() => updateSection(id, (items) => items?.filter((_, rowIndex) => index !== rowIndex))}>移除这条经历</button>
                  </fieldset>
                ))}
              </section>
            );
          })}
        </div>
        <section className="space-y-3 lg:sticky lg:top-20">
          <div className="no-print flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">实时预览</h2>
            <Link href="/interview?resume=draft" className="btn-secondary">用这份简历练面试</Link>
          </div>
          <article className="resume-paper min-h-[34rem] rounded-lg border bg-white p-6 text-zinc-900 shadow-card sm:p-9" aria-label="简历预览">
            {preview ? preview.split('\n\n').map((block, index) => (
              <p key={index} className={`whitespace-pre-wrap break-words ${index === 0 ? 'text-lg font-semibold' : 'mt-4 border-t border-zinc-200 pt-3 text-sm leading-6'}`}>{block}</p>
            )) : <p className="no-print text-sm text-zinc-500">填写资料后在这里预览简历。</p>}
          </article>
        </section>
      </div>
      <p className="no-print mt-5 text-xs text-muted-foreground"><a className="underline" href="https://github.com/GrinZero/Reactive-Resume/tree/master">Reactive Resume v4 JSON 格式</a></p>
    </PageShell>
  );
}
