
import { Message, Sender, Source } from "../types.ts";

/**
 * MUSIC-ASSIST API SERVICE
 * Connects to the FastAPI/Python backend provided by the project team.
 */

const BACKEND_URL = "http://localhost:8000/chat"; // Update this to your friend's server URL

export class MusicAssistService {
  async sendMessage(prompt: string, history: Message[]): Promise<{ text: string; sources: Source[] }> {
    try {
      // Transforming history for the backend if needed
      const chatHistory = history.map(m => ({
        role: m.sender === Sender.USER ? "user" : "assistant",
        content: m.text
      }));

      // Send the query to the backend chat endpoint
      const response = await fetch(BACKEND_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: prompt, conversation_id: null })
      });

      if (!response.ok) {
        const body = await response.text().catch(() => "");
        throw new Error(`Backend error: ${response.status} ${body}`);
      }

      const data = await response.json();

      // Map backend ChatResponse to the frontend shape
      return {
        text: data.response,
        sources: data.sources || []
      };
    } catch (error) {
      console.error("Music-Assist API Error:", error);
      // Return a friendly fallback message for the UI when backend is unavailable
      return {
        text: "I was unable to retrieve guidance at this moment. Please ensure the sacred music archive is accessible.",
        sources: []
      };
    }
  }
}

export const musicAssistApi = new MusicAssistService();
