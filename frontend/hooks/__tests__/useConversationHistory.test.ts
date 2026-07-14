import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useConversationHistory } from '../useConversationHistory.ts';
import { musicAssistApi } from '../../services/apiService.ts';

vi.mock('../../services/apiService.ts', () => ({
  musicAssistApi: {
    getUserConversations: vi.fn(),
  },
}));

const getUserConversationsMock = vi.mocked(musicAssistApi.getUserConversations);

beforeEach(() => {
  getUserConversationsMock.mockReset();
});

describe('useConversationHistory', () => {
  it('fetches history when a userId is provided', async () => {
    getUserConversationsMock.mockResolvedValue([{ id: 'c1', title: 'Hymn question' }]);

    const { result } = renderHook(() => useConversationHistory('user1'));

    await waitFor(() => expect(result.current.history).toHaveLength(1));
    expect(getUserConversationsMock).toHaveBeenCalledWith('user1');
  });

  it('clears history when userId becomes null', async () => {
    getUserConversationsMock.mockResolvedValue([{ id: 'c1', title: 'Hymn question' }]);

    const { result, rerender } = renderHook(({ userId }) => useConversationHistory(userId), {
      initialProps: { userId: 'user1' as string | null },
    });

    await waitFor(() => expect(result.current.history).toHaveLength(1));

    rerender({ userId: null });

    await waitFor(() => expect(result.current.history).toHaveLength(0));
  });

  it('does not fetch when there is no userId', () => {
    renderHook(() => useConversationHistory(null));

    expect(getUserConversationsMock).not.toHaveBeenCalled();
  });
});
