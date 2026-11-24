import { z } from 'zod';

export const interviewSetup = z.object({
  role: z.string().trim().min(1).max(150),
  company: z.string().trim().max(150),
  round: z.enum(['岗位面', '行为面', 'HR 面']),
  description: z.string().trim().min(1).max(12000),
  resume: z.string().trim().min(1).max(16000),
});

const turn = z.object({ question: z.string().min(1).max(1500), answer: z.string().trim().min(1).max(4500) });
const context = { setup: interviewSetup, turns: z.array(turn).max(6) };
export const interviewRequest = z.discriminatedUnion('action', [
  z.object({ action: z.literal('start'), ...context }),
  z.object({ action: z.literal('followup'), setup: interviewSetup, turns: z.array(turn).min(1).max(6) }),
  z.object({ action: z.literal('report'), setup: interviewSetup, turns: z.array(turn).min(1).max(6) }),
]);

export const interviewStart = z.object({
  matches: z.array(z.object({
    requirement: z.string(), evidence: z.string(), status: z.enum(['已有依据', '需要补充']),
  })).min(1).max(5),
  question: z.string().min(1).max(1500),
});
export const interviewFollowup = z.object({ question: z.string().min(1).max(1500) });
export const interviewReport = z.object({
  strengths: z.array(z.string()),
  improvements: z.array(z.string()).min(1),
  action: z.string().min(1),
});

export type InterviewSetup = z.infer<typeof interviewSetup>;
export type InterviewTurn = z.infer<typeof turn>;
export type InterviewStart = z.infer<typeof interviewStart>;
export type InterviewReport = z.infer<typeof interviewReport>;
