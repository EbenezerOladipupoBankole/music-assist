
import React, { useEffect, useRef, useState } from 'react';
import ChatMessage from './components/ChatMessage.tsx';
import ChatInput from './components/ChatInput.tsx';
import LoginModal from './components/LoginModal.tsx';
import Sidebar from './components/Sidebar.tsx';
import ChatHeader from './components/ChatHeader.tsx';
import EmptyState from './components/EmptyState.tsx';
import { useAuth } from './hooks/useAuth.ts';
import { useConversationHistory } from './hooks/useConversationHistory.ts';
import { useChat } from './hooks/useChat.ts';

const App: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { user, isLoginModalOpen, setIsLoginModalOpen, handleGoogleLogin, handleLogout } = useAuth();
  const { history, refreshHistory } = useConversationHistory(user?.uid ?? null);

  const {
    messages,
    isLoading,
    statusText,
    currentConversationId,
    loadConversation,
    startNewChat,
    handleSendMessage,
  } = useChat({
    isAuthenticated: !!user,
    userId: user?.uid ?? null,
    userName: user?.displayName ?? null,
    onQuotaExceeded: () => setIsLoginModalOpen(true),
    onConversationPersisted: () => {
      if (user) refreshHistory(user.uid);
    },
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, isLoading]);

  const handleSelectConversation = (convId: string) => {
    setIsSidebarOpen(false);
    loadConversation(convId);
  };

  const handleStartNewChat = () => {
    startNewChat();
    setIsSidebarOpen(false);
  };

  const handleLogoutAndReset = async () => {
    await handleLogout();
    startNewChat();
  };

  return (
    <div className="flex h-[100dvh] bg-[#F8FAFC] overflow-hidden font-sans text-slate-900 selection:bg-teal-100 relative">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onNewChat={handleStartNewChat}
        history={history}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        user={user}
        onLogout={handleLogoutAndReset}
        onLoginClick={() => setIsLoginModalOpen(true)}
      />

      <main className="flex-1 flex flex-col h-full relative bg-white lg:rounded-l-[2.5rem] lg:my-2 lg:mr-2 lg:shadow-[0_0_50px_rgba(15,23,42,0.05)] overflow-hidden border-l border-slate-100/50">
        <ChatHeader
          user={user}
          onMenuClick={() => setIsSidebarOpen(true)}
          onNewChat={handleStartNewChat}
          onLoginClick={() => setIsLoginModalOpen(true)}
        />

        <div ref={scrollRef} className="flex-1 overflow-y-auto pt-4 lg:pt-10 pb-4 scroll-smooth bg-slate-50/50">
          {messages.length === 0 ? (
            <EmptyState onPromptClick={handleSendMessage} />
          ) : (
            <div className="max-w-4xl mx-auto w-full px-4 lg:px-12">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {isLoading && (
                <div className="flex justify-start px-4 mb-12" aria-live="polite">
                  <div className="bg-white/50 backdrop-blur-sm border border-slate-100/50 rounded-2xl rounded-tl-none p-4 shadow-sm flex items-center gap-4 animate-pulse-subtle">
                    <div className="flex gap-1">
                      <div className="w-1.5 h-4 bg-teal-200 rounded-full"></div>
                      <div className="w-1.5 h-6 bg-teal-400 rounded-full"></div>
                      <div className="w-1.5 h-4 bg-teal-600 rounded-full"></div>
                    </div>
                    <span className="text-[10px] font-black text-teal-600 uppercase tracking-[0.2em]">{statusText}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="shrink-0 p-4 lg:p-8 pt-2 lg:pt-0 bg-white lg:bg-transparent border-t lg:border-t-0 border-slate-100 pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <ChatInput onSend={handleSendMessage} disabled={isLoading} />
          <div className="text-center mt-3 lg:mt-5">
            <p className="text-[8px] lg:text-[9px] text-slate-300 font-black uppercase tracking-[0.3em]">
              Music Management System • Authorized Use Only
            </p>
          </div>
        </div>
      </main>

      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLogin={handleGoogleLogin}
      />
    </div>
  );
};

export default App;
