import { useCallback, useEffect, useState } from 'react';
import { musicAssistApi } from '../services/apiService.ts';
import { SavedConversation } from '../types.ts';

/** Sidebar conversation list for a signed-in user - refetches whenever
 * `userId` changes (sign-in/out), and exposes a manual refresh for after a
 * new conversation is created. */
export function useConversationHistory(userId: string | null) {
  const [history, setHistory] = useState<SavedConversation[]>([]);

  const refreshHistory = useCallback(async (uid: string) => {
    try {
      const data = await musicAssistApi.getUserConversations(uid);
      setHistory(data);
    } catch (err) {
      console.error("Failed to fetch history", err);
    }
  }, []);

  useEffect(() => {
    if (userId) {
      refreshHistory(userId);
    } else {
      setHistory([]);
    }
  }, [userId, refreshHistory]);

  return { history, refreshHistory };
}
