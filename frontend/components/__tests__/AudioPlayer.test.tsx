import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AudioPlayer from '../AudioPlayer.tsx';

// jsdom doesn't implement real media playback - stub the bits AudioPlayer calls.
beforeEach(() => {
  window.HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
  window.HTMLMediaElement.prototype.pause = vi.fn();
});

describe('AudioPlayer', () => {
  it('renders the provided title', () => {
    render(<AudioPlayer url="/audio/hymn/2" title="The Spirit of God (#2)" />);

    expect(screen.getByText('The Spirit of God (#2)')).toBeInTheDocument();
  });

  it('falls back to a default title when none is provided', () => {
    render(<AudioPlayer url="/audio/hymn/2" />);

    expect(screen.getByText('Official Hymn Recording')).toBeInTheDocument();
  });

  it('toggles the play/pause button label on click', async () => {
    const user = userEvent.setup();
    render(<AudioPlayer url="/audio/hymn/2" title="Test Hymn" />);

    const toggleButton = screen.getByRole('button', { name: /play hymn recording/i });
    await user.click(toggleButton);

    expect(await screen.findByRole('button', { name: /pause hymn recording/i })).toBeInTheDocument();
    expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalled();
  });
});
