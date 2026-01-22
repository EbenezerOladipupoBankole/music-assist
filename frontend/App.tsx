
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
        text: response.text,
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
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans text-slate-900 selection:bg-teal-100 selection:text-teal-900">
      
      {/* Main Interface */}
      <main className="flex-1 flex flex-col h-full relative w-full bg-white">
        {/* Header */}
        <header className="h-16 border-b border-slate-100 flex items-center justify-between px-4 md:px-6 bg-white/80 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-4">
             <div className="w-8 h-8 bg-gradient-to-br from-teal-500 to-emerald-600 rounded-lg flex items-center justify-center shadow-sm">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
             </div>
             <h2 className="text-sm font-semibold text-slate-700 hidden md:block">Music Assist</h2>
          </div>
          
          <div className="flex items-center gap-3">
             {user ? (
               <div className="flex items-center gap-3 pl-4">
                 <div className="text-right hidden sm:block">
                    <div className="text-xs font-bold text-slate-700">{user.displayName || user.email}</div>
                    <div className="text-[10px] text-slate-400">Authenticated</div>
                 </div>
                 {user.photoURL ? (
                   <img src={user.photoURL} alt={user.displayName || 'User'} className="w-8 h-8 rounded-full shadow-sm border border-slate-200" />
                 ) : (
                   <div className="w-8 h-8 rounded-full bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center text-white font-bold text-xs shadow-sm border border-white">
                     {user.displayName?.charAt(0).toUpperCase() || user.email?.charAt(0).toUpperCase()}
                   </div>
                 )}
                 <button onClick={handleLogout} className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-all" title="Sign Out">
                   <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
                 </button>
               </div>
             ) : (
               <button onClick={() => setIsLoginModalOpen(true)} className="px-5 py-2 text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 rounded-full transition-all shadow-sm flex items-center gap-2">
                 <span>Sign In</span>
               </button>
             )}
          </div>
        </header>

        {/* Chat Stream */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-0 scroll-smooth bg-slate-50/50">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-3xl mx-auto p-6">
              <div className="text-center mb-12 space-y-6 animate-in fade-in zoom-in duration-500">
                <div className="w-16 h-16 bg-white rounded-2xl shadow-sm border border-slate-100 flex items-center justify-center mx-auto mb-6">
                  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="url(#grad1)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <defs>
                        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style={{stopColor:'#0d9488', stopOpacity:1}} />
                        <stop offset="100%" style={{stopColor:'#0f766e', stopOpacity:1}} />
                        </linearGradient>
                    </defs>
                    <path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle>
                  </svg>
                </div>
                <h3 className="text-3xl font-bold text-slate-900 tracking-tight font-serif">
                  Welcome to <br/><span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-emerald-600">Music Assist</span>
                </h3>
                <p className="text-slate-500 text-sm max-w-md mx-auto leading-relaxed">
                  Ask about hymn selection, conducting techniques, or music theory grounded in resources from The Church of Jesus Christ of Latter-day Saints.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                {SUGGESTED_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(prompt)}
                    className="group p-4 bg-white border border-slate-200/60 hover:border-teal-500/50 rounded-xl text-left hover:shadow-md transition-all duration-200 flex items-center justify-between"
                  >
                    <span className="text-sm font-medium text-slate-700 group-hover:text-teal-700">{prompt}</span>
                    <svg className="opacity-0 group-hover:opacity-100 transition-opacity text-teal-500" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto w-full py-8 space-y-6">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {isLoading && (
                <div className="flex justify-start px-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-none p-4 shadow-sm flex items-center gap-3">
                      <div className="flex space-x-1">
                        <div className="w-1.5 h-1.5 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-1.5 h-1.5 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-1.5 h-1.5 bg-teal-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                      <span className="text-xs font-medium text-slate-400">Consulting handbook...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Dock */}
        <div className="shrink-0 p-4 bg-white border-t border-slate-100">
          <div className="max-w-3xl mx-auto">
            <ChatInput onSend={handleSendMessage} disabled={isLoading} />
            <div className="text-center mt-3">
              <p className="text-[10px] text-slate-400">
                AI can make mistakes. Please verify important information.
              </p>
            </div>
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
