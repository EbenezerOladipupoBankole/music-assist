
export enum Sender {
  USER = 'user',
  AI = 'ai'
}

export interface Source {
  title: string;
  url: string;
}

export interface Message {
  id: string;
  sender: Sender;
  text: string;
  timestamp: number;
  sources?: Source[];
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
}
