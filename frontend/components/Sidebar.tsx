import React from 'react';
import { SavedConversation, UserProfile } from '../types.ts';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
  history: SavedConversation[];
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  user: UserProfile | null;
  onLogout: () => void;
  onLoginClick: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onNewChat,
  history,
  currentConversationId,
  onSelectConversation,
  user,
  onLogout,
  onLoginClick,
}) => {
  return (
    <>
      {/* Mobile Sidebar Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 mobile-sidebar-overlay"
          onClick={onClose}
        />
      )}

      {/* Sidebar - Desktop + Mobile Drawer */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50 w-72 bg-slate-50/60 lg:bg-transparent border-r border-slate-100 p-5 lg:p-6
        transition-transform duration-300 ease-in-out lg:translate-x-0
        ${isOpen ? 'translate-x-0 shadow-prominent' : '-translate-x-full lg:flex'}
        flex flex-col
      `}>
        <div className="flex items-center justify-between mb-9">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl flex items-center justify-center overflow-hidden bg-white shadow-subtle ring-1 ring-slate-100">
              <img src="/logo.png" alt="Music Assist Logo" className="w-4/5 h-4/5 object-contain" />
            </div>
            <div>
              <h1 className="font-serif font-bold text-lg tracking-tight leading-none text-slate-900">Music Assist</h1>
              <span className="text-2xs font-bold text-teal-600 uppercase">Ecclesiastical AI</span>
            </div>
          </div>
          <button
            className="lg:hidden p-2 -mr-2 text-slate-400 hover:text-slate-600 transition-colors"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2.5 px-4 py-3 rounded-xl bg-white text-slate-900 font-bold text-sm transition-all border border-slate-200 shadow-subtle hover:border-teal-200 hover:shadow-elevated active:scale-[0.98] mb-8"
        >
          <svg className="w-4 h-4 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 4v16m8-8H4" /></svg>
          New Consultation
        </button>

        <div className="flex-1 overflow-y-auto space-y-1 pr-2 scrollbar-hide">
          <p className="px-4 text-2xs font-bold uppercase text-slate-400 mb-3">Past Consultations</p>
          {history.length > 0 ? history.map((conv) => (
            <button
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`w-full text-left px-4 py-3 rounded-xl transition-all group relative cursor-pointer z-10 ${currentConversationId === conv.id
                ? 'bg-white text-teal-900 shadow-subtle ring-1 ring-teal-100'
                : 'hover:bg-white/80 text-slate-500 hover:text-slate-900'
                }`}
            >
              <div className="flex items-center gap-3 pointer-events-none">
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${currentConversationId === conv.id ? 'bg-teal-500' : 'bg-slate-300'}`}></div>
                <p className="text-xs font-semibold truncate">{conv.title}</p>
              </div>
            </button>
          )) : (
            <div className="px-4 py-8 text-center border border-dashed border-slate-200 rounded-2xl">
              <p className="text-xs text-slate-300 font-medium italic">No recent history</p>
            </div>
          )}
        </div>

        <div className="mt-auto pt-5 border-t border-slate-200/70">
          {user ? (
            <div className="flex items-center gap-3">
              {user.photoURL ? (
                <img src={user.photoURL} alt="" className="w-9 h-9 rounded-full border border-slate-100 shadow-subtle" />
              ) : (
                <div className="w-9 h-9 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold shadow-subtle shrink-0">
                  {user.displayName?.charAt(0)}
                </div>
              )}
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-bold truncate text-slate-800 leading-tight">{user.displayName}</p>
                <button onClick={onLogout} className="text-2xs font-bold text-red-500 hover:text-red-600 uppercase">End Session</button>
              </div>
            </div>
          ) : (
            <button onClick={onLoginClick} className="w-full py-3.5 rounded-xl bg-slate-900 text-white text-xs font-bold shadow-elevated hover:bg-slate-800 hover:shadow-prominent transition-all uppercase tracking-wide">
              Sign In to Account
            </button>
          )}
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
