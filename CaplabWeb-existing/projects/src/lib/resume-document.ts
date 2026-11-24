import { z } from 'zod';

const itemSchema = z.looseObject({ id: z.string(), visible: z.boolean().optional() });
const sectionSchema = z.looseObject({
  name: z.string(),
  visible: z.boolean().optional(),
  content: z.string().optional(),
  items: z.array(itemSchema).optional(),
});
const resumeSchema = z.looseObject({
  basics: z.looseObject({ name: z.string() }),
  sections: z.record(z.string(), z.unknown()),
  metadata: z.record(z.string(), z.unknown()),
});

export type Resume = z.infer<typeof resumeSchema>;
type ResumeItem = z.infer<typeof itemSchema>;

export const resumeDraftKey = 'caplab-resume-v4';

export const basicFields = [
  ['name', '姓名'], ['headline', '求职方向'], ['email', '邮箱'], ['phone', '电话'], ['location', '城市'],
] as const;

export const sections = {
  education: ['教育经历', ['institution', '学校'], ['area', '专业'], ['studyType', '学历'], ['score', '成绩'], ['date', '时间']],
  experience: ['实习与工作', ['company', '公司'], ['position', '职位'], ['location', '地点'], ['date', '时间']],
  projects: ['项目经历', ['name', '项目名称'], ['description', '个人角色'], ['date', '时间'], ['keywords', '关键词']],
  skills: ['技能', ['name', '技能名称'], ['description', '掌握情况'], ['keywords', '关键词']],
  volunteer: ['志愿经历', ['organization', '组织'], ['position', '职责'], ['location', '地点'], ['date', '时间']],
  awards: ['奖项', ['title', '奖项名称'], ['awarder', '授予方'], ['date', '时间']],
  certifications: ['证书', ['name', '证书名称'], ['issuer', '发证方'], ['date', '时间']],
  languages: ['语言', ['name', '语言'], ['description', '熟练度']],
  publications: ['发表成果', ['name', '成果名称'], ['publisher', '出版方'], ['date', '时间']],
  interests: ['兴趣', ['name', '兴趣'], ['keywords', '关键词']],
  references: ['推荐人', ['name', '姓名'], ['description', '关系']],
  profiles: ['个人主页', ['network', '平台'], ['username', '用户名']],
} as const;
export type SectionId = keyof typeof sections;
const sectionIds = Object.keys(sections) as SectionId[];
const commonSections: SectionId[] = ['education', 'experience', 'projects', 'skills'];
const emptyUrl = { label: '', href: '' };

export function emptyResume(): Resume {
  const sectionRecords = Object.fromEntries(sectionIds.map((id) => [
    id, { id, name: sections[id][0], columns: 1, visible: true, separateLinks: true, items: [] },
  ]));
  return {
    basics: { name: '', headline: '', email: '', phone: '', location: '', url: emptyUrl, customFields: [],
      picture: { url: '', size: 64, aspectRatio: 1, borderRadius: 0, effects: { hidden: false, border: false, grayscale: false } } },
    sections: { ...sectionRecords, summary: { id: 'summary', name: '个人简介', columns: 1, visible: true, separateLinks: true, content: '' }, custom: {} },
    metadata: {
      template: 'rhyhorn', layout: [[['summary', ...sectionIds]]], css: { value: '', visible: false },
      page: { margin: 18, format: 'a4', options: { breakLine: true, pageNumbers: true } },
      theme: { background: '#ffffff', text: '#202720', primary: '#31503b' },
      typography: { font: { family: 'IBM Plex Serif', subset: 'latin', variants: ['regular'], size: 14 }, lineHeight: 1.5, hideIcons: false, underlineLinks: true },
      notes: '',
    },
  };
}

export function parseResume(input: unknown): Resume {
  const wrapped = z.object({ data: resumeSchema }).safeParse(input);
  const parsed = wrapped.success ? wrapped.data.data : resumeSchema.parse(input);
  for (const key of ['summary', ...sectionIds]) {
    if (parsed.sections[key] !== undefined) sectionSchema.parse(parsed.sections[key]);
  }
  const defaults = emptyResume();
  return {
    ...parsed,
    basics: { ...defaults.basics, ...parsed.basics },
    sections: { ...defaults.sections, ...parsed.sections },
    metadata: { ...defaults.metadata, ...parsed.metadata },
  };
}

export function readSection(resume: Resume, id: SectionId | 'summary') {
  return sectionSchema.parse(resume.sections[id]);
}

export function editableSections(resume: Resume) {
  return [...commonSections, ...sectionIds.filter((id) => !commonSections.includes(id) && readSection(resume, id).items?.length)];
}

export function newResumeItem(id: SectionId): ResumeItem {
  const fields = sections[id].slice(1) as readonly (readonly [string, string])[];
  return {
    ...Object.fromEntries(fields.map(([key]) => [key, key === 'keywords' ? [] : ''])),
    id: 'c' + crypto.randomUUID().replaceAll('-', '').slice(0, 23),
    visible: true,
    summary: '', url: emptyUrl, level: 1, icon: '',
  };
}

export function plainText(value: unknown): string {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === 'string').join('、');
  if (typeof value !== 'string' || !/<[^>]+>|&(?:[a-z]+|#[0-9]+|#x[0-9a-f]+);/i.test(value) || typeof document === 'undefined') return typeof value === 'string' ? value : '';
  const template = document.createElement('template');
  template.innerHTML = value.replace(/<br\s*\/?>|<\/(?:p|li|div|h[1-6])>/gi, '\n');
  template.content.querySelectorAll('script, style').forEach((element) => element.remove());
  return template.content.textContent?.replace(/\n$/, '') ?? '';
}

export function richText(value: string) {
  return value.split('\n').map((line) => '<p>' + line.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;') + '</p>').join('');
}

export function resumeText(resume: Resume, includeContact = false) {
  const basics = basicFields.filter(([key]) => includeContact || (key !== 'email' && key !== 'phone'))
    .map(([key]) => plainText(resume.basics[key])).filter(Boolean);
  const summary = readSection(resume, 'summary');
  return [
    basics.join(' · '),
    summary.visible === false ? '' : plainText(summary.content),
    ...editableSections(resume).map((id) => {
      const section = readSection(resume, id);
      const fields = sections[id].slice(1) as readonly (readonly [string, string])[];
      const lines = section.visible === false ? [] : (section.items ?? [])
        .filter((item) => item.visible !== false)
        .map((item) => [...fields.map(([key]) => plainText(item[key])), plainText(item.summary)].map((value) => value.trim()).filter(Boolean).join(' · ')).filter(Boolean);
      return lines.length ? [section.name, ...lines].join('\n') : '';
    }),
  ].map((value) => value.trim()).filter(Boolean).join('\n\n');
}
