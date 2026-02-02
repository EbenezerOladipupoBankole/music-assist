
import React, { useState, useRef, useEffect } from 'react';
import { Message, Sender } from './types.ts';
import { musicAssistApi } from './services/apiService.ts';
import { APP_NAME, SUGGESTED_PROMPTS, COLORS } from './constants.ts';
import ChatMessage from './components/ChatMessage.tsx';
import ChatInput from './components/ChatInput.tsx';
import LoginModal from './components/LoginModal.tsx';
import { auth, googleProvider } from './firebase.ts';
import { signInWithPopup, signOut, onAuthStateChanged } from 'firebase/auth';

import { API_BASE_URL } from './constants.ts';

interface UserProfile {
  displayName: string | null;
  email: string | null;
  photoURL: string | null;
  uid: string;
}

interface SavedConversation {
  id: string;
  title: string;
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState('System Standby');
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [history, setHistory] = useState<SavedConversation[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [queryCount, setQueryCount] = useState<number>(() => {
    return parseInt(localStorage.getItem('music_assist_query_count') || '0');
  });

  // Fetch Side History
  const fetchHistory = async (uid: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${uid}`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (err) {
      console.error("Failed to fetch history", err);
    }
  };

  // Load Specific Conversation
  const loadConversation = async (convId: string) => {
    setIsLoading(true);
    setIsSidebarOpen(false);
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${convId}/history`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data);
        setCurrentConversationId(convId);
      }
    } catch (err) {
      console.error("Failed to load conversation", err);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setCurrentConversationId(null);
    setIsSidebarOpen(false);
  };

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
        const profile = {
          displayName: currentUser.displayName,
          email: currentUser.email,
          photoURL: currentUser.photoURL,
          uid: currentUser.uid
        };
        setUser(profile);
        fetchHistory(currentUser.uid);
      } else {
        setUser(null);
        setHistory([]);
      }
    });
    return () => unsubscribe();
  }, []);

  const handleGoogleLogin = async () => {
    try {
      console.log("Music-Assist: Attempting Google Login...");
      await signInWithPopup(auth, googleProvider);
      console.log("Music-Assist: Login successful");
      setIsLoginModalOpen(false);
    } catch (error: any) {
      console.error("Music-Assist: Login failed", error);
      alert(`Authentication failed: ${error.message || 'Unknown error'}`);
    }
  };

  const handleLogout = async () => {
    try {
      await signOut(auth);
      setUser(null);
      startNewChat();
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

    // Placeholder AI message that we'll update as chunks arrive
    const aiMsgId = (Date.now() + 1).toString();
    const initialAiMsg: Message = {
      id: aiMsgId,
      sender: Sender.AI,
      text: '',
      timestamp: Date.now(),
      sources: []
    };

    setMessages(prev => [...prev, initialAiMsg]);

    try {
      if (!user) {
        const newCount = queryCount + 1;
        setQueryCount(newCount);
        localStorage.setItem('music_assist_query_count', newCount.toString());
      }

      let accumulatedText = '';

      await musicAssistApi.streamMessage(
        text,
        messages,
        currentConversationId,
        user?.uid || null,
        user?.displayName || null,
        (chunk) => {
          accumulatedText += chunk;
          setMessages(prev => prev.map(m =>
            m.id === aiMsgId ? { ...m, text: accumulatedText } : m
          ));
        },
        (metadata) => {
          if (metadata.conversation_id && !currentConversationId) {
            setCurrentConversationId(metadata.conversation_id);
            if (user) fetchHistory(user.uid);
          }
          if (metadata.sources || metadata.audio_url) {
            setMessages(prev => prev.map(m =>
              m.id === aiMsgId ? {
                ...m,
                sources: metadata.sources || m.sources,
                audioUrl: metadata.audio_url || m.audioUrl,
                audioTitle: metadata.audio_title || m.audioTitle
              } : m
            ));
          }
        }
      );

      setStatusText('Consultation complete');
      if (user) fetchHistory(user.uid);
    } catch (error) {
      console.error("App: Service Error", error);

      let errorMessage = "I was unable to retrieve guidance at this moment. Please ensure the sacred music archive is accessible.";
      if (error instanceof Error) {
        errorMessage += `\n\n[System Diagnostic: ${error.message}]`;
      }

      setMessages(prev => prev.map(m =>
        m.id === aiMsgId ? { ...m, text: errorMessage } : m
      ));
      setStatusText('Service unavailable');
    } finally {
      setIsLoading(false);
      setTimeout(() => setStatusText('System Standby'), 3000);
    }
  };

  return (
    <div className="flex h-[100dvh] bg-[#F8FAFC] overflow-hidden font-sans text-slate-900 selection:bg-teal-100 relative">

      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 mobile-sidebar-overlay"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar - Desktop + Mobile Drawer */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50 w-72 bg-white border-r border-slate-200/60 p-6 
        transition-transform duration-300 ease-in-out lg:translate-x-0
        ${isSidebarOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full lg:flex'}
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
          <button className="lg:hidden p-2 text-slate-400" onClick={() => setIsSidebarOpen(false)}>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <button
          onClick={startNewChat}
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
              onClick={() => loadConversation(conv.id)}
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
                <img src={user.photoURL} className="w-9 h-9 rounded-full border border-slate-100 shadow-sm" />
              ) : (
                <div className="w-9 h-9 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold shadow-md">
                  {user.displayName?.charAt(0)}
                </div>
              )}
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-black truncate text-slate-800 leading-tight">{user.displayName}</p>
                <button onClick={handleLogout} className="text-[10px] font-bold text-red-500 hover:text-red-600 uppercase tracking-widest">End Session</button>
              </div>
            </div>
          ) : (
            <button onClick={() => setIsLoginModalOpen(true)} className="w-full py-4 rounded-xl bg-slate-900 text-white text-xs font-black shadow-xl hover:bg-slate-800 transition-all uppercase tracking-widest">
              Sign In to Account
            </button>
          )}
        </div>
      </aside>

      <main className="flex-1 flex flex-col h-full relative bg-white lg:rounded-l-[2.5rem] lg:my-2 lg:mr-2 lg:shadow-[0_0_50px_rgba(15,23,42,0.05)] overflow-hidden border-l border-slate-100/50">
        <header className="lg:hidden h-16 border-b border-slate-100 flex items-center justify-between px-6 bg-white/80 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <button className="p-2 -ml-2 text-slate-600 active:bg-slate-50 rounded-lg" onClick={() => setIsSidebarOpen(true)}>
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" /></svg>
            </button>
            <h2 className="font-serif font-black text-base tracking-tight text-slate-900 italic">Music Assist</h2>
          </div>
          {!user ? (
            <button onClick={() => setIsLoginModalOpen(true)} className="text-[10px] font-black uppercase tracking-widest text-slate-900 border-2 border-slate-900 px-4 py-1.5 rounded-lg active:bg-slate-50">Login</button>
          ) : (
            <button onClick={startNewChat} title="New Consultation" className="w-9 h-9 rounded-xl bg-slate-900 shadow-md flex items-center justify-center text-white active:scale-95 transition-transform">
              <svg className="w-4 h-4" fill="none" stroke="white" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M12 4v16m8-8H4" /></svg>
            </button>
          )}
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto pt-4 lg:pt-10 pb-4 scroll-smooth bg-slate-50/50">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto px-6">
              <div className="text-center mb-10 lg:mb-16">
                <div className="w-24 h-24 lg:w-32 lg:h-32 bg-white rounded-[2.5rem] lg:rounded-[3rem] flex items-center justify-center mx-auto mb-8 lg:mb-10 shadow-[0_10px_40px_rgba(0,0,0,0.04)] border border-slate-100/80 relative overflow-hidden">
                  <img src="/logo.png" alt="Music Assist Logo" className="w-4/5 h-4/5 object-contain" />
                </div>
                <h3 className="text-3xl lg:text-5xl font-serif font-black text-slate-900 mb-4 lg:mb-6 tracking-tight leading-tight lg:leading-[1.1]">
                  Sacred Guidance for <br /><span className="text-teal-600 italic">Sacred Music</span>
                </h3>
                <p className="text-slate-400 text-xs lg:text-sm max-w-md mx-auto leading-relaxed font-medium">
                  Welcome to Music Assist. I am your specialized RAG-powered assistant for hymns, conducting, and official music policy.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 lg:gap-4 w-full">
                {SUGGESTED_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(prompt)}
                    className="p-5 lg:p-6 bg-white border border-slate-200/60 hover:border-teal-500/30 rounded-2xl lg:rounded-[1.8rem] text-left hover:shadow-[0_20px_40px_rgba(15,23,42,0.06)] transition-all duration-500 group relative overflow-hidden"
                  >
                    <div className="absolute top-0 right-0 w-24 h-24 bg-teal-50/20 rounded-full -mr-12 -mt-12 transition-transform group-hover:scale-150 duration-700"></div>
                    <span className="text-[10px] lg:text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 group-hover:text-emerald-600 block mb-1 lg:mb-2 transition-colors">Consultation</span>
                    <span className="text-[14px] lg:text-[15px] text-slate-600 group-hover:text-slate-900 leading-snug font-bold transition-colors">{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto w-full px-4 lg:px-12">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {isLoading && (
                <div className="flex justify-start px-4 mb-12">
                  <div className="bg-white/50 backdrop-blur-sm border border-slate-100/50 rounded-2xl rounded-tl-none p-4 shadow-sm flex items-center gap-4 animate-pulse-subtle">
                    <div className="flex gap-1">
                      <div className="w-1.5 h-4 bg-teal-200 rounded-full"></div>
                      <div className="w-1.5 h-6 bg-teal-400 rounded-full"></div>
                      <div className="w-1.5 h-4 bg-teal-600 rounded-full"></div>
                    </div>
                    <span className="text-[10px] font-black text-teal-600 uppercase tracking-[0.2em]">Processing Guidance</span>
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
