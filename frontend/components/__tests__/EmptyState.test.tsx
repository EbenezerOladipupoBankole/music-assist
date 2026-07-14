import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EmptyState from '../EmptyState.tsx';
import { SUGGESTED_PROMPTS } from '../../constants.ts';

describe('EmptyState', () => {
  it('renders every suggested prompt', () => {
    render(<EmptyState onPromptClick={vi.fn()} />);

    for (const prompt of SUGGESTED_PROMPTS) {
      expect(screen.getByText(prompt)).toBeInTheDocument();
    }
  });

  it('calls onPromptClick with the clicked prompt text', async () => {
    const user = userEvent.setup();
    const onPromptClick = vi.fn();
    render(<EmptyState onPromptClick={onPromptClick} />);

    await user.click(screen.getByText(SUGGESTED_PROMPTS[0]));

    expect(onPromptClick).toHaveBeenCalledWith(SUGGESTED_PROMPTS[0]);
  });
});
