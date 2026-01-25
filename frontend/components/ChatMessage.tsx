
import React from 'react';
import { Message, Sender } from '../types.ts';
import { COLORS } from '../constants.ts';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isAI = message.sender === Sender.AI;

  return (
    <div className={`flex w-full mb-8 px-4 md:px-0 ${isAI ? 'justify-start' : 'justify-end'}`}>
      <div className={`relative max-w-[90%] md:max-w-[85%] overflow-hidden transition-all duration-300 ${isAI
          ? 'bg-white border border-slate-100 shadow-sm rounded-2xl rounded-tl-sm p-6'
          : 'bg-[#1e293b] text-white shadow-xl rounded-2xl rounded-tr-sm p-5'
        }`}>

        {/* Header/Info Bar */}
        <div className="flex items-center justify-between mb-4 border-b border-black/5 pb-2">
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-black uppercase tracking-[0.15em] px-2 py-0.5 rounded-full ${isAI ? 'bg-teal-50 text-teal-600' : 'bg-white/10 text-white/80'
              }`}>
              {isAI ? 'Official Guidance' : 'Inquirer'}
            </span>
          </div>
          <span className={`text-[9px] font-mono opacity-40 ${isAI ? 'text-slate-500' : 'text-white'}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Message Content */}
        <div
          className={`text-[15px] md:text-[16px] leading-[1.6] transition-colors ${isAI
              ? 'font-serif text-slate-800'
              : 'font-sans text-white/95'
            }`}
          dangerouslySetInnerHTML={{ __html: message.text || '<span class="text-slate-300 italic animate-pulse">Consulting the handbook...</span>' }}
        />

        {/* Sources Section */}
        {isAI && message.sources && message.sources.length > 0 && (
          <div className="mt-6 pt-5 border-t border-slate-50">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1 h-1 rounded-full bg-teal-500"></div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Citations</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source, idx) => (
                <a
                  key={idx}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 py-1.5 px-3 rounded-lg bg-slate-50 border border-slate-100 hover:border-teal-200 hover:bg-teal-50/50 transition-all text-[11px] font-medium text-slate-600 hover:text-teal-900 group"
                >
                  <svg className="w-3 h-3 text-slate-400 group-hover:text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                  <span>{source.title.split('–')[0].trim()}</span>
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
