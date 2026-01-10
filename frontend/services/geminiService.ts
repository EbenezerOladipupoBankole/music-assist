
import { GoogleGenAI } from "@google/genai";
import { SYSTEM_INSTRUCTION } from "../constants.ts";
import { Message, Sender, Source } from "../types.ts";

// GeminiService provides AI-powered guidance for music specialists
export class GeminiService {
  /**
   * Sends a prompt to the Gemini model with conversation history.
   * Utilizes Google Search Grounding for verified documentation.
   */
  async sendMessage(prompt: string, history: Message[] = []) {
    try {
      // Initialize the SDK with the environment API key as per guidelines
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

      // Transform history to Gemini format (user/model roles)
      const contents = history.map(msg => ({
        role: msg.sender === Sender.USER ? 'user' : 'model',
        parts: [{ text: msg.text }]
      }));
      
      // Add the current prompt as the latest user turn
      contents.push({ role: 'user', parts: [{ text: prompt }] });

      // Use gemini-3-pro-preview for complex reasoning and grounding capabilities
      const response = await ai.models.generateContent({
        model: "gemini-3-pro-preview",
        contents,
        config: {
          systemInstruction: SYSTEM_INSTRUCTION,
          // Enabling Google Search Grounding for retrieval-augmented responses
          tools: [{ googleSearch: {} }],
          temperature: 0.7,
        },
      });

      // The .text property is a getter that extracts the string output
      const text = response.text || "I'm sorry, I couldn't generate a response.";
      
      // Extract grounding metadata to provide source attribution in the UI
      const groundingChunks = response.candidates?.[0]?.groundingMetadata?.groundingChunks || [];
      const sources: Source[] = groundingChunks
        .filter((chunk: any) => chunk.web)
        .map((chunk: any) => ({
          title: chunk.web.title || "Official Reference",
          url: chunk.web.uri
        }));

      return {
        text,
        sources
      };
    } catch (error) {
      console.error("Music-Assist Gemini Service Error:", error);
      throw error;
    }
  }
}

export const gemini = new GeminiService();
