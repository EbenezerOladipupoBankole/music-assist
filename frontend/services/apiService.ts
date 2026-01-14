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

      // Validate the response from the cloud function to ensure it has the expected shape.
      if (!data || typeof data.response !== 'string' || typeof data.conversation_id !== 'string') {
        console.error("Invalid response structure from 'chat' function:", data);
        throw new Error("Received an invalid response from the backend service.");
      }

      // Map backend ChatResponse to the frontend shape
      return {
        text: data.response,
        sources: data.sources || [],
        conversationId: data.conversation_id,
      };
    } catch (error) {
      console.error("Music-Assist API Error: Failed to call the 'chat' cloud function.", error);
      // Re-throw the original error so the UI layer can handle it and developers can see the full context.
      throw error;
    }
  }
}

export const musicAssistApi = new MusicAssistService();
