
import React, { useState, useRef, useEffect } from 'react';
import { Message, Sender } from './types.ts';
import { musicAssistApi } from './services/apiService.ts';
import { APP_NAME, SUGGESTED_PROMPTS, COLORS, REFERENCE_LINKS } from './constants.ts';
import ChatMessage from './components/ChatMessage.tsx';
import ChatInput from './components/ChatInput.tsx';

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [statusText, setStatusText] = useState('System Standby');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, isLoading]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

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
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: Sender.AI,
        text: "I was unable to retrieve guidance at this moment. Please ensure the sacred music archive is accessible.",
        timestamp: Date.now()
      }]);
      setStatusText('Service unavailable');
    } finally {
      setIsLoading(false);
      setTimeout(() => setStatusText('System Standby'), 3000);
    }
  };

  return (
    <div className="flex h-screen bg-[#fdfbf7] overflow-hidden font-sans selection:bg-teal-100 selection:text-teal-900">
      
      {/* Sidebar: The Library Cabinet */}
      <aside className={`${isSidebarOpen ? 'w-80' : 'w-0'} bg-[#0f172a] text-slate-300 transition-all duration-500 overflow-hidden flex flex-col hidden lg:flex shrink-0 shadow-2xl z-30`}>
        <div className="p-10 border-b border-white/5">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-amber-600 p-2.5 rounded-xl shadow-lg shadow-amber-900/20">
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight font-serif">{APP_NAME}</h1>
          </div>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-[0.25em]">Ecclesiastical Intelligence</p>
        </div>

        <div className="flex-1 px-8 py-10 overflow-y-auto scrollbar-hide">
          <h2 className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-8 px-2 flex items-center gap-3">
             <span className="w-1 h-1 bg-amber-500 rounded-full"></span>
             Canonical Reference
          </h2>
          <nav className="space-y-2">
            {REFERENCE_LINKS.map((link, i) => (
              <a 
                key={i} 
                href={link.url} 
                target="_blank" 
                rel="noreferrer"
                className="group flex items-center justify-between p-4 text-xs font-semibold text-slate-400 hover:text-white hover:bg-white/5 rounded-2xl transition-all border border-transparent hover:border-white/5"
              >
                <span className="truncate max-w-[180px]">{link.name}</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-0 group-hover:opacity-100 transition-opacity"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
              </a>
            ))}
          </nav>
        </div>

        <div className="p-10 border-t border-white/5 mt-auto bg-slate-900/50">
           <div className="flex items-center gap-3 mb-4">
              <div className={`w-2 h-2 rounded-full animate-pulse ${isLoading ? 'bg-amber-500' : 'bg-teal-500'}`}></div>
              <p className="text-[10px] font-bold text-white uppercase tracking-widest">{statusText}</p>
           </div>
           <p className="text-[11px] text-slate-500 leading-relaxed font-serif italic">"Wherefore, the spirit and the body are the soul of man."</p>
        </div>
      </aside>

      {/* Main Interface */}
      <main className="flex-1 flex flex-col relative h-full">
        {/* Header: The Altar */}
        <header className="h-24 glass-header border-b border-slate-200/50 flex items-center justify-between px-10 sticky top-0 z-20 shrink-0">
          <div className="flex items-center gap-6">
             <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-3 hover:bg-slate-50 rounded-2xl text-slate-400 hover:text-slate-900 transition-all hidden lg:block border border-transparent hover:border-slate-100">
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
             </button>
             <div className="flex flex-col">
                <h2 className="text-lg font-bold text-slate-900 tracking-tight font-serif">Music Assists</h2>
                <span className="text-[10px] text-teal-600 font-bold uppercase tracking-widest flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-500"></span>
                  Your music friend
                </span>
             </div>
          </div>
          <div className="flex items-center gap-4">
             <button onClick={() => setMessages([])} className="px-6 py-2.5 text-[11px] font-bold text-slate-600 hover:text-red-700 bg-white hover:bg-red-50 border border-slate-200 hover:border-red-100 rounded-full transition-all shadow-sm">
               Log in
             </button>
          </div>
        </header>

        {/* Chat Stream */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 md:px-20 py-12 space-y-4 scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-4xl mx-auto">
              <div className="text-center space-y-8 mb-16 animate-in fade-in zoom-in duration-1000">
                <div className="w-20 h-20 bg-white rounded-3xl shadow-xl border border-slate-50 flex items-center justify-center mx-auto mb-10 animate-float">
                  <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#b45309" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M8 7h6"/><path d="M8 11h8"/></svg>
                </div>
                <h3 className="text-5xl font-black text-slate-900 tracking-tighter leading-tight font-serif">
                  Worship through <br/><span className="text-teal-700 italic">Musical Excellence</span>
                </h3>
                <p className="text-slate-500 text-lg leading-relaxed max-w-xl mx-auto font-medium">
                  Professional guidance for LDS music leaders, grounded in official doctrine and the art of sacred music.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5 w-full max-w-3xl">
                {SUGGESTED_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(prompt)}
                    className="group p-7 bg-white border border-slate-100 rounded-[2rem] text-left hover:border-teal-500 hover:shadow-2xl transition-all relative overflow-hidden"
                  >
                    <div className="absolute top-0 right-0 w-24 h-24 bg-teal-50/30 rounded-full -mr-10 -mt-10 group-hover:scale-150 transition-transform duration-700"></div>
                    <p className="text-sm font-bold text-slate-800 leading-relaxed group-hover:text-teal-950 relative z-10">{prompt}</p>
                    <div className="mt-5 flex items-center gap-2 text-[10px] font-bold text-teal-600 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all translate-x-[-10px] group-hover:translate-x-0 relative z-10">
                      <span>Begin Inquiry</span>
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto w-full pb-32">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {isLoading && (
                <div className="flex justify-start mb-12 animate-pulse">
                  <div className="bg-white border border-slate-100 rounded-[2rem] p-8 shadow-sm flex flex-col gap-5 min-w-[340px]">
                    <div className="flex items-center gap-4">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 bg-teal-200 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '200ms' }}></div>
                        <div className="w-2 h-2 bg-teal-600 rounded-full animate-bounce" style={{ animationDelay: '400ms' }}></div>
                      </div>
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em]">Analyzing Repository</span>
                    </div>
                    <div className="space-y-3">
                       <div className="h-2 bg-slate-50 rounded-full w-full"></div>
                       <div className="h-2 bg-slate-50 rounded-full w-3/4"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Dock */}
        <div className="shrink-0 p-10 pt-4 bg-gradient-to-t from-[#fdfbf7] via-[#fdfbf7] to-transparent">
          <div className="max-w-4xl mx-auto">
            <ChatInput onSend={handleSendMessage} disabled={isLoading} />
            <div className="flex items-center justify-center gap-6 mt-6">
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.3em]">
                Sacred Music Guidance System
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
