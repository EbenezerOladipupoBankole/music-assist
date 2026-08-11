import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useChat } from '../useChat.ts';
import { musicAssistApi } from '../../services/apiService.ts';

vi.mock('../../services/apiService.ts', () => ({
  musicAssistApi: {
    streamMessage: vi.fn(),
  },
}));

const streamMessageMock = vi.mocked(musicAssistApi.streamMessage);

function baseOptions(overrides: Partial<Parameters<typeof useChat>[0]> = {}) {
  return {
    isAuthenticated: true,
    userId: 'user1',
    userName: 'Jane',
    onQuotaExceeded: vi.fn(),
    onConversationPersisted: vi.fn(),
    ...overrides,
  };
}

const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  clear: vi.fn()
};
vi.stubGlobal('localStorage', localStorageMock);

beforeEach(() => {
  localStorageMock.clear();
  streamMessageMock.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useChat', () => {
  it('appends a user message and an AI placeholder immediately on send', async () => {
    streamMessageMock.mockImplementation(async () => { });
    const { result } = renderHook(() => useChat(baseOptions()));

    await act(async () => {
      await result.current.handleSendMessage('What is hymn 2?');
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].text).toBe('What is hymn 2?');
  });

  it('accumulates streamed chunks into the AI message text', async () => {
    streamMessageMock.mockImplementation(async (_text: any, _cid: any, _uid: any, _uname: any, onChunk: any) => {
      onChunk('Hello ');
      onChunk('world');
    });

    const { result } = renderHook(() => useChat(baseOptions()));

    await act(async () => {
      await result.current.handleSendMessage('hi');
    });

    expect(result.current.messages[1].text).toBe('Hello world');
  });

  it('sets the conversation id from streamed metadata and notifies onConversationPersisted', async () => {
    const onConversationPersisted = vi.fn();
    streamMessageMock.mockImplementation(async (_text: any, _cid: any, _uid: any, _uname: any, _onChunk: any, onMetadata: any) => {
      onMetadata({ type: 'metadata', conversation_id: 'conv_123' });
    });

    const { result } = renderHook(() => useChat(baseOptions({ onConversationPersisted })));

    await act(async () => {
      await result.current.handleSendMessage('hi');
    });

    expect(result.current.currentConversationId).toBe('conv_123');
    expect(onConversationPersisted).toHaveBeenCalled();
  });

  it('shows a fallback error message when the stream fails', async () => {
    streamMessageMock.mockRejectedValue(new Error('network down'));

    const { result } = renderHook(() => useChat(baseOptions()));

    await act(async () => {
      await result.current.handleSendMessage('hi');
    });

    expect(result.current.messages[1].text).toMatch(/unable to retrieve guidance/i);
  });

  it('blocks unauthenticated users past the free query limit', async () => {
    localStorageMock.getItem.mockReturnValue('5');
    const onQuotaExceeded = vi.fn();

    const { result } = renderHook(() => useChat(baseOptions({ isAuthenticated: false, userId: null, onQuotaExceeded })));

    await act(async () => {
      await result.current.handleSendMessage('hi');
    });

    expect(onQuotaExceeded).toHaveBeenCalled();
    expect(streamMessageMock).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });

  it('startNewChat clears messages and the current conversation id', async () => {
    streamMessageMock.mockImplementation(async (_text: any, _cid: any, _uid: any, _uname: any, _onChunk: any, onMetadata: any) => {
      onMetadata({ type: 'metadata', conversation_id: 'conv_123' });
    });
    const { result } = renderHook(() => useChat(baseOptions()));

    await act(async () => {
      await result.current.handleSendMessage('hi');
    });
    act(() => {
      result.current.startNewChat();
    });

    expect(result.current.messages).toHaveLength(0);
    expect(result.current.currentConversationId).toBeNull();
  });

  it('ignores blank/whitespace-only messages', async () => {
    const { result } = renderHook(() => useChat(baseOptions()));

    await act(async () => {
      await result.current.handleSendMessage('   ');
    });

    expect(result.current.messages).toHaveLength(0);
    expect(streamMessageMock).not.toHaveBeenCalled();
  });
});
