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
        fixed lg:static inset-y-0 left-0 z-50 w-72 bg-white border-r border-slate-200/60 p-6
        transition-transform duration-300 ease-in-out lg:translate-x-0
        ${isOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full lg:flex'}
        flex flex-col
      `}>
        <div className="flex items-center justify-between mb-10">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center overflow-hidden">
              <img src="/logo.png" alt="Music Assist Logo" className="w-full h-full object-contain" />
            </div>
            <div>
              <h1 className="font-serif font-black text-lg tracking-tight leading-none text-slate-900">Music Assist</h1>
              <span className="text-[10px] font-black text-teal-600 uppercase tracking-widest">Ecclesiastical AI</span>
            </div>
          </div>
          <button
            className="lg:hidden p-2 text-slate-400"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-50 text-slate-900 font-bold text-sm transition-all border border-slate-200/50 hover:bg-slate-100 active:scale-[0.98] mb-8"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 4v16m8-8H4" /></svg>
          New Consultation
        </button>

        <div className="flex-1 overflow-y-auto space-y-1 pr-2 scrollbar-hide">
          <p className="px-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-4">Past Consultations</p>
          {history.length > 0 ? history.map((conv) => (
            <button
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`w-full text-left px-4 py-3 rounded-xl transition-all group relative cursor-pointer z-10 ${currentConversationId === conv.id
                ? 'bg-teal-50 text-teal-900 shadow-sm border border-teal-100'
                : 'hover:bg-slate-50 text-slate-500 hover:text-slate-900'
                }`}
            >
              <div className="flex items-center gap-3 pointer-events-none">
                <div className={`w-1.5 h-1.5 rounded-full ${currentConversationId === conv.id ? 'bg-teal-500' : 'bg-slate-300'}`}></div>
                <p className="text-xs font-bold truncate max-w-[160px]">{conv.title}</p>
              </div>
            </button>
          )) : (
            <div className="px-4 py-8 text-center border-2 border-dashed border-slate-100/50 rounded-2xl">
              <p className="text-[11px] text-slate-300 font-medium italic">No recent history</p>
            </div>
          )}
        </div>

        <div className="mt-auto pt-6 border-t border-slate-50">
          {user ? (
            <div className="flex items-center gap-3">
              {user.photoURL ? (
                <img src={user.photoURL} alt="" className="w-9 h-9 rounded-full border border-slate-100 shadow-sm" />
              ) : (
                <div className="w-9 h-9 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold shadow-md">
                  {user.displayName?.charAt(0)}
                </div>
              )}
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-black truncate text-slate-800 leading-tight">{user.displayName}</p>
                <button onClick={onLogout} className="text-[10px] font-bold text-red-500 hover:text-red-600 uppercase tracking-widest">End Session</button>
              </div>
            </div>
          ) : (
            <button onClick={onLoginClick} className="w-full py-4 rounded-xl bg-slate-900 text-white text-xs font-black shadow-xl hover:bg-slate-800 transition-all uppercase tracking-widest">
              Sign In to Account
            </button>
          )}
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
