import { getApp } from "firebase/app";
import { getFunctions, httpsCallable, connectFunctionsEmulator, Functions } from "firebase/functions";
import { Message, Sender, Source } from "../types.ts";

/**
 * MUSIC-ASSIST API SERVICE
 * Connects to the Firebase Cloud Functions backend.
 */

let functionsInstance: Functions | null = null;

function getSmartFunctions() {
  if (!functionsInstance) {
    const app = getApp();
    functionsInstance = getFunctions(app);
    // Determine environment
    const isLocal = typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");
    if (isLocal) {
      // Connect to the local Firebase emulator suite
      connectFunctionsEmulator(functionsInstance, "localhost", 5001);
    }
  }
  return functionsInstance;
}

export class MusicAssistService {
  async sendMessage(
    prompt: string,
    history: Message[], // Kept for context, though backend uses conversation_id
    conversationId: string | null
  ): Promise<{ text: string; sources: Source[]; conversationId: string }> {
    try {
      const functions = getSmartFunctions();
      // 'chat' is the name of the Cloud Function
      const chatFunction = httpsCallable(functions, 'chat');

      const response = await chatFunction({ 
        message: prompt, 
        conversation_id: conversationId 
      });

      const data = response.data as any;

      // Map backend ChatResponse to the frontend shape
      return {
        text: data.response,
        sources: data.sources || [],
        conversationId: data.conversation_id,
      };
    } catch (error) {
      console.error("Music-Assist API Error:", error);
      // Return a friendly fallback message for the UI when backend is unavailable
      return {
        text: "I was unable to retrieve guidance at this moment. Please ensure the sacred music archive is accessible.",
        sources: [],
        // Return the previous ID or a new temporary one if it was null
        conversationId: conversationId || `error_${Date.now()}`,
      };
    }
  }
}

export const musicAssistApi = new MusicAssistService();
