import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import ChatMessage from '../ChatMessage.tsx';
import { Message, Sender } from '../../types.ts';

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: '1',
    sender: Sender.USER,
    text: 'Hello',
    timestamp: Date.now(),
    ...overrides,
  };
}

describe('ChatMessage', () => {
  it('renders user messages aligned to the right with "Inquirer" label', () => {
    render(<ChatMessage message={makeMessage({ sender: Sender.USER, text: 'What is hymn 2?' })} />);

    expect(screen.getByText('Inquirer')).toBeInTheDocument();
    expect(screen.getByText('What is hymn 2?')).toBeInTheDocument();
  });

  it('renders AI messages with "Official Guidance" label', () => {
    render(<ChatMessage message={makeMessage({ sender: Sender.AI, text: 'The Spirit of God' })} />);

    expect(screen.getByText('Official Guidance')).toBeInTheDocument();
  });

  it('renders a loading skeleton when AI text is empty', () => {
    const { container } = render(<ChatMessage message={makeMessage({ sender: Sender.AI, text: '' })} />);

    expect(container.querySelector('.shimmer')).toBeInTheDocument();
  });

  it('renders source citations for AI messages', () => {
    render(<ChatMessage message={makeMessage({
      sender: Sender.AI,
      text: 'Answer',
      sources: [{ title: 'General Handbook 19.4', url: 'https://example.com' }],
    })} />);

    expect(screen.getByText(/General Handbook 19.4/)).toBeInTheDocument();
  });

  it('does not render an audio player when no audioUrl is present', () => {
    const { container } = render(<ChatMessage message={makeMessage({ sender: Sender.AI, audioUrl: undefined })} />);

    expect(container.querySelector('audio')).not.toBeInTheDocument();
  });

  it('renders an audio player when audioUrl is present', () => {
    const { container } = render(<ChatMessage message={makeMessage({
      sender: Sender.AI,
      audioUrl: '/audio/hymn/2',
      audioTitle: 'The Spirit of God',
    })} />);

    expect(container.querySelector('audio')).toBeInTheDocument();
  });
});
