import { Message } from '../types';

// TODO: Replace this URL with your actual Render Backend URL
// Example: "https://music-assist-backend.onrender.com"
const API_BASE_URL = "https://music-assist-backend.onrender.com";

export const musicAssistApi = {
  sendMessage: async (text: string, history: Message[]) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          history: history
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