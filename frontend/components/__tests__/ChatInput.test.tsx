import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatInput from '../ChatInput.tsx';

describe('ChatInput', () => {
  it('calls onSend with the typed text when submitted', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    await user.type(screen.getByPlaceholderText(/ask about hymns/i), 'What is hymn 2?');
    await user.keyboard('{Enter}');

    expect(onSend).toHaveBeenCalledWith('What is hymn 2?');
  });

  it('clears the input after sending', async () => {
    const user = userEvent.setup();
    render(<ChatInput onSend={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/ask about hymns/i);
    await user.type(textarea, 'Hello');
    await user.keyboard('{Enter}');

    expect(textarea).toHaveValue('');
  });

  it('does not send on shift+enter (inserts a newline instead)', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    await user.type(screen.getByPlaceholderText(/ask about hymns/i), 'line one{Shift>}{Enter}{/Shift}line two');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('does not send an empty or whitespace-only message', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    await user.type(screen.getByPlaceholderText(/ask about hymns/i), '   ');
    await user.keyboard('{Enter}');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('disables the textarea and send button when disabled=true', () => {
    render(<ChatInput onSend={vi.fn()} disabled />);

    expect(screen.getByPlaceholderText(/ask about hymns/i)).toBeDisabled();
  });

  it('disables the send button while the input is empty', () => {
    render(<ChatInput onSend={vi.fn()} />);

    const submitButton = document.querySelector('button[type="submit"]');
    expect(submitButton).toBeDisabled();
  });
});
