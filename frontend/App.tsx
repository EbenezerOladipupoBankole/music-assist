
import React, { useState, useRef, useEffect } from 'react';
import { Message, Sender } from './types.ts';
import { musicAssistApi } from './services/apiService.ts';
import { APP_NAME, SUGGESTED_PROMPTS, COLORS } from './constants.ts';
import ChatMessage from './components/ChatMessage.tsx';
import ChatInput from './components/ChatInput.tsx';
import LoginModal from './components/LoginModal.tsx';
import { auth, googleProvider } from './firebase.ts';
import { signInWithPopup, signOut, onAuthStateChanged } from 'firebase/auth';

interface UserProfile {
  displayName: string | null;
  email: string | null;
  photoURL: string | null;
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState('System Standby');
  const scrollRef = useRef<HTMLDivElement>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [queryCount, setQueryCount] = useState<number>(() => {
    return parseInt(localStorage.getItem('music_assist_query_count') || '0');
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, isLoading]);

  // Monitor Firebase Auth State
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      if (currentUser) {
        setUser({
          displayName: currentUser.displayName,
          email: currentUser.email,
          photoURL: currentUser.photoURL,
        });
      } else {
        setUser(null);
      }
    });
    return () => unsubscribe();
  }, []);

  const handleGoogleLogin = async () => {
    try {
      await signInWithPopup(auth, googleProvider);
      setIsLoginModalOpen(false);
    } catch (error) {
      console.error("Login failed", error);
      alert("Authentication failed. Please try again.");
    }
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      setUser(null);
    } catch (error) {
      console.error("Logout failed", error);
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    // Check query limit for unauthenticated users
    if (!user && queryCount >= 5) {
      setIsLoginModalOpen(true);
      return;
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: Sender.USER,
      text,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setStatusText('Reviewing handbook...');

    try {
      // Increment query count if not logged in
      if (!user) {
        const newCount = queryCount + 1;
        setQueryCount(newCount);
        localStorage.setItem('music_assist_query_count', newCount.toString());
      }

      // Consultation with the Music-Assist RAG backend
      const response = await musicAssistApi.sendMessage(text, messages);

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: Sender.AI,
        text: response.response,
        timestamp: Date.now(),
        sources: response.sources
      };

      setMessages(prev => [...prev, aiMsg]);
      setStatusText('Consultation complete');
    } catch (error) {
      console.error("App: Service Error", error);

      let errorMessage = "I was unable to retrieve guidance at this moment. Please ensure the sacred music archive is accessible.";
      if (error instanceof Error) {
        errorMessage += `\n\n[System Diagnostic: ${error.message}]`;
      }

      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: Sender.AI,
        text: errorMessage,
        timestamp: Date.now()
      }]);
      setStatusText('Service unavailable');
    } finally {
      setIsLoading(false);
      setTimeout(() => setStatusText('System Standby'), 3000);
    }
  };

  return (
    <div className="flex h-screen bg-[#f8fafc] overflow-hidden font-sans text-slate-900 selection:bg-teal-100">

      {/* Sidebar - Desktop Only */}
      <aside className="hidden lg:flex flex-col w-72 bg-white border-r border-slate-100 p-6">
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center shadow-lg">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
          </div>
          <div>
            <h1 className="font-serif font-black text-lg tracking-tight leading-none text-slate-900">Music Assist</h1>
            <span className="text-[10px] font-bold text-teal-600 uppercase tracking-widest">Ecclesiastical AI</span>
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-50 text-slate-900 font-bold text-sm transition-all border border-slate-200/50">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>
            New Consultation
          </button>
        </nav>

        <div className="mt-auto pt-6 border-t border-slate-50">
          {user ? (
            <div className="flex items-center gap-3">
              {user.photoURL ? (
                <img src={user.photoURL} className="w-8 h-8 rounded-full border border-slate-100" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold">
                  {user.displayName?.charAt(0)}
                </div>
              )}
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-bold truncate text-slate-700">{user.displayName}</p>
                <button onClick={handleLogout} className="text-[10px] font-bold text-red-500 hover:text-red-600 uppercase tracking-wider">Sign Out</button>
              </div>
            </div>
          ) : (
            <button onClick={() => setIsLoginModalOpen(true)} className="w-full py-3 rounded-xl bg-slate-900 text-white text-xs font-bold shadow-sm hover:shadow-md transition-all">
              Sign In to Account
            </button>
          )}
        </div>
      </aside>

      <main className="flex-1 flex flex-col h-full relative bg-white lg:rounded-l-[2rem] lg:my-2 lg:mr-2 lg:shadow-2xl lg:shadow-slate-200/50 overflow-hidden border-l border-slate-100">
        {/* Mobile Header */}
        <header className="lg:hidden h-16 border-b border-slate-100 flex items-center justify-between px-6 bg-white/80 backdrop-blur-md sticky top-0 z-20">
          <h2 className="font-serif font-black text-base tracking-tight text-slate-900">Music Assist</h2>
          {!user && (
            <button onClick={() => setIsLoginModalOpen(true)} className="text-xs font-bold text-slate-900 border border-slate-200 px-3 py-1.5 rounded-lg active:bg-slate-50">Sign In</button>
          )}
        </header>

        {/* Chat Stream */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto pt-8 pb-4 scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto px-6">
              <div className="text-center mb-10">
                <div className="w-20 h-20 bg-slate-50 rounded-[2.5rem] flex items-center justify-center mx-auto mb-8 shadow-inner border border-slate-100">
                  <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#0f172a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
                </div>
                <h3 className="text-4xl font-serif font-black text-slate-900 mb-4 tracking-tight leading-tight">
                  Sacred Guidance for <br /><span className="text-teal-600">Sacred Music</span>
                </h3>
                <p className="text-slate-400 text-sm max-w-sm mx-auto leading-[1.6]">
                  Your specialized assistant for hymns, conducting, and Church music theory.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                {SUGGESTED_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(prompt)}
                    className="p-5 bg-white border border-slate-100 hover:border-teal-500/30 rounded-2xl text-left hover:shadow-xl hover:shadow-slate-200/50 transition-all duration-300 group"
                  >
                    <span className="text-[13px] font-bold text-slate-600 group-hover:text-slate-900 block mb-1">Inquiry</span>
                    <span className="text-sm text-slate-400 group-hover:text-teal-700 leading-snug">{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto w-full px-4 md:px-10">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {isLoading && (
                <div className="flex justify-start px-4 mb-10">
                  <div className="bg-slate-50 border border-slate-100 rounded-2xl rounded-tl-none p-5 shadow-sm flex items-center gap-4">
                    <div className="flex space-x-1.5">
                      <div className="w-1 h-1 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-1 h-1 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-1 h-1 bg-teal-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest text-shadow-glow">Consulting Handbook</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Dock */}
        <div className="shrink-0 p-6 bg-white lg:bg-transparent">
          <ChatInput onSend={handleSendMessage} disabled={isLoading} />
          <div className="text-center mt-3">
            <p className="text-[9px] text-slate-300 font-bold uppercase tracking-[0.2em]">
              Authorized Use Only • v1.2
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
