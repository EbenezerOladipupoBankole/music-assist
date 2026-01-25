import { Message } from '../types';

// Use environment variable for API URL or default to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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