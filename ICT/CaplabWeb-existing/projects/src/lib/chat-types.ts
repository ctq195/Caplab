export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  streaming?: boolean;
}

export interface Attachment {
  name: string;
  sizeLabel: string;
  kind: 'file' | 'image';
}
