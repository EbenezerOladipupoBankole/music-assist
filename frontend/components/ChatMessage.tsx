
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
    <div className={`flex w-full mb-6 px-4 md:px-0 ${isAI ? 'justify-start' : 'justify-end'}`}>
      <div className={`relative max-w-[90%] md:max-w-[80%] overflow-hidden transition-all duration-300 ${isAI
        ? 'bg-white border border-slate-200 shadow-subtle rounded-2xl rounded-tl-md p-5 md:p-6'
        : 'bg-slate-900 text-white shadow-elevated rounded-2xl rounded-tr-md p-5 ring-1 ring-slate-800'
        }`}>

        {/* Header/Info Bar */}
        <div className="flex items-center justify-between mb-3.5 border-b border-black/5 pb-2.5">
          <span className={`text-2xs font-bold uppercase px-2 py-0.5 rounded-full ${isAI ? 'bg-teal-50 text-teal-700' : 'bg-white/10 text-white/80'
            }`}>
            {isAI ? 'Official Guidance' : 'Inquirer'}
          </span>
          <span className={`text-[10px] font-mono ${isAI ? 'text-slate-400' : 'text-white/40'}`}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Message Content */}
        <div
          className={`text-[15px] leading-relaxed transition-colors prose prose-sm max-w-none ${isAI
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
          <div className="mt-5 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-1 h-1 rounded-full bg-teal-500"></div>
              <p className="text-2xs font-bold text-slate-400 uppercase">Citations</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source, idx) => (
                <a
                  key={idx}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 py-1.5 px-3 rounded-lg bg-slate-50 border border-slate-200 hover:border-teal-300 hover:bg-teal-50/60 transition-all text-xs font-semibold text-slate-600 hover:text-teal-800 group"
                >
                  <svg className="w-3 h-3 text-slate-400 group-hover:text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
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
