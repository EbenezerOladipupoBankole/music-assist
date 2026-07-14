import { afterEach, describe, expect, it, vi } from 'vitest';
import { musicAssistApi } from '../apiService.ts';

function jsonResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    json: async () => body,
  } as Response;
}

/** Builds a fake streaming Response whose body yields the given NDJSON lines. */
function streamingResponse(lines: string[]) {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      for (const line of lines) {
        controller.enqueue(encoder.encode(line + '\n'));
      }
      controller.close();
    },
  });
  return { ok: true, status: 200, body } as unknown as Response;
}

describe('musicAssistApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('sendMessage', () => {
    it('posts the message and returns the parsed JSON', async () => {
      const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ response: 'Hi there' }));
      vi.stubGlobal('fetch', fetchMock);

      const result = await musicAssistApi.sendMessage('hello', 'conv1', 'user1', 'Jane');

      expect(result).toEqual({ response: 'Hi there' });
      const [url, options] = fetchMock.mock.calls[0];
      expect(url).toContain('/chat');
      expect(JSON.parse(options.body)).toEqual({
        message: 'hello',
        conversation_id: 'conv1',
        user_id: 'user1',
        user_name: 'Jane',
      });
    });

    it('throws when the server responds with an error status', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, false, 500)));

      await expect(musicAssistApi.sendMessage('hello')).rejects.toThrow('500');
    });
  });

  describe('streamMessage', () => {
    it('routes metadata and content chunks to the right callbacks', async () => {
      const lines = [
        JSON.stringify({ type: 'metadata', conversation_id: 'conv1', sources: [] }),
        JSON.stringify({ type: 'content', delta: 'Hello ' }),
        JSON.stringify({ type: 'content', delta: 'world' }),
      ];
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse(lines)));

      const onChunk = vi.fn();
      const onMetadata = vi.fn();

      await musicAssistApi.streamMessage('hi', null, null, null, onChunk, onMetadata);

      expect(onMetadata).toHaveBeenCalledWith(expect.objectContaining({ conversation_id: 'conv1' }));
      expect(onChunk).toHaveBeenNthCalledWith(1, 'Hello ');
      expect(onChunk).toHaveBeenNthCalledWith(2, 'world');
    });

    it('throws when the stream emits an error chunk', async () => {
      const lines = [JSON.stringify({ type: 'error', message: 'boom' })];
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamingResponse(lines)));

      await expect(
        musicAssistApi.streamMessage('hi', null, null, null, vi.fn(), vi.fn())
      ).rejects.toThrow('boom');
    });

    it('ignores malformed lines instead of throwing', async () => {
      const encoder = new TextEncoder();
      const body = new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('not valid json\n'));
          controller.enqueue(encoder.encode(JSON.stringify({ type: 'content', delta: 'ok' }) + '\n'));
          controller.close();
        },
      });
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, body } as unknown as Response));

      const onChunk = vi.fn();
      await musicAssistApi.streamMessage('hi', null, null, null, onChunk, vi.fn());

      expect(onChunk).toHaveBeenCalledWith('ok');
    });
  });

  describe('getUserConversations', () => {
    it('returns the parsed conversation list', async () => {
      const conversations = [{ id: 'c1', title: 'Hymn question' }];
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(conversations)));

      const result = await musicAssistApi.getUserConversations('user1');

      expect(result).toEqual(conversations);
    });

    it('throws on a non-ok response', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, false, 404)));

      await expect(musicAssistApi.getUserConversations('user1')).rejects.toThrow('404');
    });
  });

  describe('getConversationHistory', () => {
    it('returns the parsed message history', async () => {
      const history = [{ id: 'm1', sender: 'user', text: 'hi', timestamp: 1 }];
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(history)));

      const result = await musicAssistApi.getConversationHistory('conv1');

      expect(result).toEqual(history);
    });
  });
});
