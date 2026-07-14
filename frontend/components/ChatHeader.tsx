import React from 'react';
import { UserProfile } from '../types.ts';

interface ChatHeaderProps {
  user: UserProfile | null;
  onMenuClick: () => void;
  onNewChat: () => void;
  onLoginClick: () => void;
}

/** Mobile-only top bar - hidden on lg+ screens where the sidebar is always visible. */
const ChatHeader: React.FC<ChatHeaderProps> = ({ user, onMenuClick, onNewChat, onLoginClick }) => {
  return (
    <header className="lg:hidden h-16 border-b border-slate-100 flex items-center justify-between px-5 bg-white/90 backdrop-blur-md sticky top-0 z-20">
      <div className="flex items-center gap-2.5">
        <button
          className="p-2 -ml-2 text-slate-500 hover:text-slate-900 active:bg-slate-50 rounded-lg transition-colors"
          onClick={onMenuClick}
          aria-label="Open sidebar"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
        <h2 className="font-serif font-bold text-base tracking-tight text-slate-900 italic">Music Assist</h2>
      </div>
      {!user ? (
        <button
          onClick={onLoginClick}
          className="text-2xs font-bold uppercase text-slate-900 border border-slate-900 px-3.5 py-1.5 rounded-lg active:bg-slate-50 transition-colors"
        >
          Login
        </button>
      ) : (
        <button
          onClick={onNewChat}
          title="New Consultation"
          aria-label="Start new consultation"
          className="w-9 h-9 rounded-xl bg-slate-900 shadow-subtle flex items-center justify-center text-white active:scale-95 transition-transform"
        >
          <svg className="w-4 h-4" fill="none" stroke="white" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M12 4v16m8-8H4" /></svg>
        </button>
      )}
    </header>
  );
};

export default ChatHeader;
