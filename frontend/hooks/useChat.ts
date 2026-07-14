import { useCallback, useEffect, useRef, useState } from 'react';
import { Message, Sender } from '../types.ts';
import { musicAssistApi, ChatMetadata } from '../services/apiService.ts';

const QUERY_COUNT_STORAGE_KEY = 'music_assist_query_count';
const FREE_QUERY_LIMIT = 5;

interface UseChatOptions {
  isAuthenticated: boolean;
  userId: string | null;
  userName: string | null;
  onQuotaExceeded: () => void;
  /** Called whenever a message has just been persisted server-side, so the
   * caller can refresh whatever conversation list it's showing. */
  onConversationPersisted: () => void;
}

function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError';
}

export function useChat({ isAuthenticated, userId, userName, onQuotaExceeded, onConversationPersisted }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState('System Standby');
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [queryCount, setQueryCount] = useState<number>(() => {
    return parseInt(localStorage.getItem(QUERY_COUNT_STORAGE_KEY) || '0', 10);
  });

  const loadAbortRef = useRef<AbortController | null>(null);
  const sendAbortRef = useRef<AbortController | null>(null);

  // Cancel any in-flight conversation load / message send on unmount, so a
  // late stream chunk can't call setState on an unmounted component.
  useEffect(() => {
    return () => {
      loadAbortRef.current?.abort();
      sendAbortRef.current?.abort();
    };
  }, []);

  const loadConversation = useCallback(async (convId: string) => {
    loadAbortRef.current?.abort();
    const controller = new AbortController();
    loadAbortRef.current = controller;

    setIsLoading(true);
    try {
      const data = await musicAssistApi.getConversationHistory(convId, controller.signal);
      setMessages(data);
      setCurrentConversationId(convId);
    } catch (err) {
      if (isAbortError(err)) return;
      console.error("Failed to load conversation", err);
    } finally {
      if (loadAbortRef.current === controller) {
        setIsLoading(false);
      }
    }
  }, []);

  const startNewChat = useCallback(() => {
    loadAbortRef.current?.abort();
    sendAbortRef.current?.abort();
    setMessages([]);
    setCurrentConversationId(null);
  }, []);

  const handleSendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;

    if (!isAuthenticated && queryCount >= FREE_QUERY_LIMIT) {
      onQuotaExceeded();
      return;
    }

    sendAbortRef.current?.abort();
    const controller = new AbortController();
    sendAbortRef.current = controller;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      sender: Sender.USER,
      text,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setStatusText('Reviewing handbook...');

    const aiMsgId = crypto.randomUUID();
    const initialAiMsg: Message = {
      id: aiMsgId,
      sender: Sender.AI,
      text: '',
      timestamp: Date.now(),
      sources: [],
    };
    setMessages(prev => [...prev, initialAiMsg]);

    try {
      if (!isAuthenticated) {
        const newCount = queryCount + 1;
        setQueryCount(newCount);
        localStorage.setItem(QUERY_COUNT_STORAGE_KEY, newCount.toString());
      }

      let accumulatedText = '';

      await musicAssistApi.streamMessage(
        text,
        currentConversationId,
        userId,
        userName,
        (chunk) => {
          accumulatedText += chunk;
          setMessages(prev => prev.map(m =>
            m.id === aiMsgId ? { ...m, text: accumulatedText } : m
          ));
        },
        (metadata: ChatMetadata) => {
          if (metadata.conversation_id && !currentConversationId) {
            setCurrentConversationId(metadata.conversation_id);
            onConversationPersisted();
          }
          if (metadata.sources || metadata.audio_url) {
            setMessages(prev => prev.map(m =>
              m.id === aiMsgId ? {
                ...m,
                sources: metadata.sources || m.sources,
                audioUrl: metadata.audio_url || m.audioUrl,
                audioTitle: metadata.audio_title || m.audioTitle,
              } : m
            ));
          }
        },
        controller.signal
      );

      if (controller.signal.aborted) return;

      setStatusText('Consultation complete');
      onConversationPersisted();
    } catch (error) {
      if (isAbortError(error)) return;

      console.error("App: Service Error", error);

      const errorMessage = "I was unable to retrieve guidance at this moment. Please ensure the sacred music archive is accessible.";

      setMessages(prev => prev.map(m =>
        m.id === aiMsgId ? { ...m, text: errorMessage } : m
      ));
      setStatusText('Service unavailable');
    } finally {
      if (sendAbortRef.current === controller) {
        setIsLoading(false);
        setTimeout(() => setStatusText('System Standby'), 3000);
      }
    }
  }, [isAuthenticated, queryCount, currentConversationId, userId, userName, onQuotaExceeded, onConversationPersisted]);

  return {
    messages,
    isLoading,
    statusText,
    currentConversationId,
    loadConversation,
    startNewChat,
    handleSendMessage,
  };
}
