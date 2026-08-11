import { Message, SavedConversation } from '../types.ts';
import { API_BASE_URL } from '../constants.ts';

/** Shape of the metadata chunk emitted by the streaming endpoint. */
export interface ChatMetadata {
  type: 'metadata';
  conversation_id?: string;
  sources?: Array<{ title: string; url: string; type?: string }>;
}

export const musicAssistApi = {
  sendMessage: async (text: string, conversationId?: string | null, userId?: string | null, userName?: string | null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId,
          user_id: userId,
          user_name: userName
        }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("API Error:", error);
      throw error;
    }
  },

  streamMessage: async (
    text: string,
    conversationId: string | null,
    userId: string | null,
    userName: string | null,
    onChunk: (chunk: string) => void,
    onMetadata: (metadata: ChatMetadata) => void,
    signal?: AbortSignal
  ) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          conversation_id: conversationId,
          user_id: userId,
          user_name: userName
        }),
        signal,
      });

      if (!response.ok) {
        throw new Error(`Streaming failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No reader available");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;

          let data: { type: string; message?: string; delta?: string } | undefined;
          try {
            data = JSON.parse(line);
          } catch (e) {
            console.warn("Failed to parse chunk:", line, e);
            continue;
          }
          if (!data) continue;

          // A server-sent "error" event must actually fail the request - it
          // used to be thrown inside the JSON.parse try/catch above, where it
          // was caught by the same handler and silently logged as a parse
          // warning instead of propagating.
          if (data.type === "error") {
            throw new Error(data.message);
          } else if (data.type === "metadata") {
            onMetadata(data as ChatMetadata);
          } else if (data.type === "content") {
            onChunk(data.delta ?? '');
          }
        }
      }
    } catch (error) {
      console.error("Streaming API Error:", error);
      throw error;
    }
  },

  getUserConversations: async (userId: string, signal?: AbortSignal): Promise<SavedConversation[]> => {
    const response = await fetch(`${API_BASE_URL}/conversations/${userId}`, { signal });
    if (!response.ok) {
      throw new Error(`Failed to fetch conversations: ${response.status}`);
    }
    return response.json();
  },

  getConversationHistory: async (conversationId: string, signal?: AbortSignal): Promise<Message[]> => {
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/history`, { signal });
    if (!response.ok) {
      throw new Error(`Failed to load conversation: ${response.status}`);
    }
    return response.json();
  },
};
