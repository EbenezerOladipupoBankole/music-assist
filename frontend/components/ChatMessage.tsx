
import React from 'react';
import { Message, Sender } from '../types.ts';
import { COLORS } from '../constants.ts';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isAI = message.sender === Sender.AI;

  return (
    <div className={`flex w-full mb-12 ${isAI ? 'justify-start' : 'justify-end'}`}>
      <div className={`relative max-w-[88%] md:max-w-[80%] rounded-3xl p-7 transition-all ${isAI ? 'bg-white border border-slate-100 shadow-sm' : COLORS.chatUser}`}>
        
        {/* Identity Badge */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isAI ? 'bg-teal-50 text-teal-600' : 'bg-white/10 text-white/80'}`}>
              {isAI ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
              )}
            </div>
            <span className={`text-[11px] font-bold uppercase tracking-[0.2em] ${isAI ? 'text-slate-400' : 'text-slate-300'}`}>
              {isAI ? 'Official Guidance' : 'Inquiry'}
            </span>
          </div>
          <span className={`text-[10px] font-mono opacity-40 ${isAI ? 'text-slate-500' : 'text-white'}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        
        {/* Content */}
        <div className={`text-[16px] leading-relaxed whitespace-pre-wrap ${isAI ? 'font-serif text-slate-800' : 'font-sans text-white/95'}`}>
          {message.text}
        </div>
        
        {/* Sources / Bibliographic section */}
        {isAI && message.sources && message.sources.length > 0 && (
          <div className="mt-8 pt-6 border-t border-slate-50">
            <p className="text-[10px] font-bold text-teal-600 uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-500"></span>
              Documentary Sources
            </p>
            <div className="flex flex-col gap-2">
              {message.sources.map((source, idx) => (
                <a 
                  key={idx}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between group p-3 rounded-xl bg-slate-50 border border-transparent hover:border-teal-100 hover:bg-teal-50/30 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-400 group-hover:text-teal-600"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M8 7h6"/><path d="M8 11h8"/></svg>
                    <span className="text-xs font-semibold text-slate-600 group-hover:text-teal-900">{source.title}</span>
                  </div>
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-0 group-hover:opacity-100 text-teal-600 transition-opacity"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
