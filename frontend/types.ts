
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

export interface UserProfile {
  displayName: string | null;
  email: string | null;
  photoURL: string | null;
  uid: string;
}

export interface SavedConversation {
  id: string;
  title: string;
}
