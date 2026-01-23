import { Message, Source } from "../types.ts";

/**
 * MUSIC-ASSIST API SERVICE.
 * Connects to the backend API using the URL from environment variables.
 */
let API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// Safety check: If the URL is the placeholder (from the template) or missing, default to localhost
if (!API_BASE_URL || API_BASE_URL.includes('random-hash')) {
  API_BASE_URL = 'https://music-assist-backend-158647252148.us-central1.run.app';
}

interface BackendChatResponse {
  response: string;
  sources: Array<{
    type: 'local' | 'web';
    title: string;
    source: string;
    url?: string;
  }>;
  conversation_id: string;
  timestamp: string;
}

export class MusicAssistService {
  private conversationId: string | null = null;

  async sendMessage(
    prompt: string,
    history: Message[],
    conversationId?: string | null
  ): Promise<{ text: string; sources: Source[]; conversationId: string }> {
    try {
      const currentConversationId = conversationId || this.conversationId;

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: prompt,
          conversation_id: currentConversationId,
          user_id: null
        })
      });

      if (!response.ok) {
        if (response.status === 503) {
          throw new Error("RAG pipeline not initialized. Please contact administrator.");
        }
        throw new Error(`Backend error: ${response.status} ${response.statusText}`);
      }

      const data: BackendChatResponse = await response.json();

      if (!data || typeof data.response !== 'string') {
        console.error("Invalid response structure from backend:", data);
        throw new Error("Received an invalid response from the backend service.");
      }

      this.conversationId = data.conversation_id;

      const mappedSources: Source[] = (data.sources || []).map(source => ({
        title: source.title || source.source,
        url: source.url || source.source
      }));

      return {
        text: data.response,
        sources: mappedSources,
        conversationId: data.conversation_id,
      };
    } catch (error) {
      console.error("Music-Assist API Error:", error);
      
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Cannot connect to the backend at ${API_BASE_URL}. Please ensure the server is running and accessible.`);
      }
      
      throw error;
    }
  }
}

export const musicAssistApi = new MusicAssistService();
