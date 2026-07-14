
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
    // Only auto-scroll once there's actual chat content - this used to fire
    // on initial mount too (messages=[]), which scrolled the empty-state
    // intro to the bottom of its own content on short viewports, hiding the
    // logo/heading behind the sticky header instead of showing them.
    if (messages.length === 0) return;
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
    <div className="flex h-[100dvh] bg-slate-50 overflow-hidden font-sans text-slate-900 selection:bg-teal-100 relative">
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

      <main className="flex-1 flex flex-col h-full relative bg-white lg:rounded-[2rem] lg:my-3 lg:mr-3 lg:shadow-prominent overflow-hidden border border-transparent lg:border-slate-100">
        <ChatHeader
          user={user}
          onMenuClick={() => setIsSidebarOpen(true)}
          onNewChat={handleStartNewChat}
          onLoginClick={() => setIsLoginModalOpen(true)}
        />

        <div ref={scrollRef} className="flex-1 overflow-y-auto pt-6 lg:pt-12 pb-4 scroll-smooth bg-gradient-to-b from-slate-50/60 to-white">
          {messages.length === 0 ? (
            <EmptyState onPromptClick={handleSendMessage} />
          ) : (
            <div className="max-w-3xl mx-auto w-full px-4 lg:px-8">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {isLoading && (
                <div className="flex justify-start px-4 mb-12" aria-live="polite">
                  <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-md px-5 py-4 shadow-subtle flex items-center gap-4">
                    <div className="flex gap-1 items-end h-4">
                      <div className="w-1 h-2 bg-teal-300 rounded-full animate-audio-bar" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-1 h-4 bg-teal-500 rounded-full animate-audio-bar" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-1 h-3 bg-teal-700 rounded-full animate-audio-bar" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span className="text-2xs font-bold text-teal-700 uppercase">{statusText}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="shrink-0 p-4 lg:p-6 pt-2 lg:pt-0 bg-white lg:bg-transparent border-t lg:border-t-0 border-slate-100 pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <ChatInput onSend={handleSendMessage} disabled={isLoading} />
          <div className="text-center mt-3 lg:mt-4">
            <p className="text-2xs text-slate-300 font-semibold uppercase">
              Music Management System · Authorized Use Only
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
