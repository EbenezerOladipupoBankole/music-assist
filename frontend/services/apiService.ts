import { Message } from '../types';
import { API_BASE_URL } from '../constants.ts';

export const musicAssistApi = {
  sendMessage: async (text: string, history: Message[], conversationId?: string | null, userId?: string | null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          history: history,
          conversation_id: conversationId,
          user_id: userId
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
  }
};