import { Message } from '../types';
import { API_BASE_URL } from '../constants.ts';

export const musicAssistApi = {
  sendMessage: async (text: string, history: Message[], conversationId?: string | null, userId?: string | null, userName?: string | null) => {
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
    history: Message[],
    conversationId: string | null,
    userId: string | null,
    userName: string | null,
    onChunk: (chunk: string) => void,
    onMetadata: (metadata: any) => void
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
          try {
            const data = JSON.parse(line);
            if (data.type === "metadata") {
              onMetadata(data);
            } else if (data.type === "content") {
              onChunk(data.delta);
            } else if (data.type === "error") {
              throw new Error(data.message);
            }
          } catch (e) {
            console.warn("Failed to parse chunk:", line, e);
          }
        }
      }
    } catch (error) {
      console.error("Streaming API Error:", error);
      throw error;
    }
  }
};