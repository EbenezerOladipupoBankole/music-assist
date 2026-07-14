import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Sidebar from '../Sidebar.tsx';
import { SavedConversation, UserProfile } from '../../types.ts';

function baseProps(overrides: Partial<Parameters<typeof Sidebar>[0]> = {}) {
  return {
    isOpen: true,
    onClose: vi.fn(),
    onNewChat: vi.fn(),
    history: [] as SavedConversation[],
    currentConversationId: null,
    onSelectConversation: vi.fn(),
    user: null as UserProfile | null,
    onLogout: vi.fn(),
    onLoginClick: vi.fn(),
    ...overrides,
  };
}

describe('Sidebar', () => {
  it('shows a sign-in prompt when signed out', () => {
    render(<Sidebar {...baseProps()} />);
    expect(screen.getByText(/sign in to account/i)).toBeInTheDocument();
  });

  it('shows the user name and an end-session action when signed in', () => {
    const user: UserProfile = { uid: 'u1', displayName: 'Jane Doe', email: 'jane@example.com', photoURL: null };
    render(<Sidebar {...baseProps({ user })} />);

    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText(/end session/i)).toBeInTheDocument();
  });

  it('shows an empty state when there is no conversation history', () => {
    render(<Sidebar {...baseProps()} />);
    expect(screen.getByText(/no recent history/i)).toBeInTheDocument();
  });

  it('renders history entries and selects one on click', async () => {
    const user = userEvent.setup();
    const onSelectConversation = vi.fn();
    const history: SavedConversation[] = [{ id: 'c1', title: 'Hymn 2 question' }];

    render(<Sidebar {...baseProps({ history, onSelectConversation })} />);

    await user.click(screen.getByText('Hymn 2 question'));
    expect(onSelectConversation).toHaveBeenCalledWith('c1');
  });

  it('calls onNewChat when "New Consultation" is clicked', async () => {
    const user = userEvent.setup();
    const onNewChat = vi.fn();
    render(<Sidebar {...baseProps({ onNewChat })} />);

    await user.click(screen.getByText(/new consultation/i));
    expect(onNewChat).toHaveBeenCalled();
  });

  it('calls onLoginClick when the sign-in button is clicked', async () => {
    const user = userEvent.setup();
    const onLoginClick = vi.fn();
    render(<Sidebar {...baseProps({ onLoginClick })} />);

    await user.click(screen.getByText(/sign in to account/i));
    expect(onLoginClick).toHaveBeenCalled();
  });

  it('calls onLogout when "End Session" is clicked', async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    const profile: UserProfile = { uid: 'u1', displayName: 'Jane Doe', email: 'jane@example.com', photoURL: null };
    render(<Sidebar {...baseProps({ user: profile, onLogout })} />);

    await user.click(screen.getByText(/end session/i));
    expect(onLogout).toHaveBeenCalled();
  });
});
