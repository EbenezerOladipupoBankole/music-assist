
import React from 'react';
import { Message, Sender } from '../types.ts';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import AudioPlayer from './AudioPlayer.tsx';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = React.memo(({ message }) => {
  const isAI = message.sender === Sender.AI;

  return (
    <div className={`flex w-full mb-8 px-4 md:px-0 ${isAI ? 'justify-start' : 'justify-end'}`}>
      <div className={`relative max-w-[90%] md:max-w-[85%] overflow-hidden transition-all duration-300 ${isAI
        ? 'bg-white border border-slate-200/80 shadow-sm rounded-2xl rounded-tl-sm p-6'
        : 'bg-[#1E293B] text-white shadow-xl rounded-2xl rounded-tr-sm p-5 ring-1 ring-slate-800'
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
          className={`text-[15px] md:text-[16px] leading-[1.6] transition-colors prose max-w-none ${isAI
            ? 'font-serif text-slate-800'
            : 'font-sans text-white/95'
            }`}
        >
          {message.text ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.text}
            </ReactMarkdown>
          ) : (
            <div className="space-y-3 animate-pulse-subtle">
              <div className="h-4 bg-slate-100 rounded w-3/4 shimmer"></div>
              <div className="h-4 bg-slate-100 rounded w-full shimmer"></div>
              <div className="h-4 bg-slate-100 rounded w-5/6 shimmer"></div>
            </div>
          )}
        </div>

        {/* Custom Audio Player */}
        {message.audioUrl && (
          <AudioPlayer url={message.audioUrl} title={message.audioTitle} />
        )}

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
                  className="flex items-center gap-2 py-1.5 px-3 rounded-lg bg-white border border-slate-200 hover:border-emerald-500/50 hover:bg-emerald-50/30 transition-all text-[11px] font-bold text-slate-600 hover:text-emerald-900 group shadow-sm"
                >
                  <svg className="w-3 h-3 text-slate-400 group-hover:text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                  <span>{source.title === 'Unknown' ? 'Official Recording' : source.title.split('–')[0].trim()}</span>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

ChatMessage.displayName = 'ChatMessage';

export default ChatMessage;
