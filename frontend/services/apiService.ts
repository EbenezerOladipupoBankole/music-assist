
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

      // In a real scenario, we'd fetch from the actual endpoint:
      /*
      const response = await fetch(BACKEND_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: prompt, history: chatHistory })
      });
      
      if (!response.ok) throw new Error("Backend connection failed");
      return await response.json();
      */

      // FOR DEMONSTRATION: Simulating a successful RAG response from the backend
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            text: `Based on Chapter 19 of the General Handbook, choir members should be invited to participate and no auditions should be held for ward choirs. \n\nRegarding conducting 'The Spirit of God', it is typically conducted in a standard 4/4 pattern with a vigorous, joyful tempo.`,
            sources: [
              { title: "General Handbook 19.3.1", url: "https://www.churchofjesuschrist.org/study/manual/general-handbook/19-music" },
              { title: "Hymn 2: The Spirit of God", url: "https://www.churchofjesuschrist.org/media/music/songs/the-spirit-of-god" }
            ]
          });
        }, 1500);
      });
    } catch (error) {
      console.error("Music-Assist API Error:", error);
      throw error;
    }
  }
}

export const musicAssistApi = new MusicAssistService();
