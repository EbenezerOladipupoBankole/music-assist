
import React, { useState, useRef, useEffect } from 'react';
import { Message, Sender } from '../types.ts';
import { API_BASE_URL } from '../constants.ts';

interface ChatMessageProps {
  message: Message;
}

const AudioPlayer: React.FC<{ url: string; title?: string }> = ({ url, title }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  const fullUrl = url.startsWith('/') ? `${API_BASE_URL}${url}` : url;

  const togglePlay = async () => {
    if (audioRef.current) {
      try {
        if (isPlaying) {
          audioRef.current.pause();
          setIsPlaying(false);
        } else {
          await audioRef.current.play();
          setIsPlaying(true);
        }
      } catch (err) {
        console.error("Audio playback failed:", err);
        alert("Sorry, the audio couldn't play. Please try again in 5 seconds while the handbook refreshes.");
      }
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      const current = audioRef.current.currentTime;
      const duration = audioRef.current.duration;
      if (duration) {
        setProgress((current / duration) * 100);
      }
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setProgress(0);
  };

  return (
    <div className="mt-4 p-4 bg-teal-50 border-l-4 border-teal-500 rounded-r-xl shadow-inner relative overflow-hidden group select-none">
      <audio
        ref={audioRef}
        src={fullUrl}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="auto"
      />

      <div className="relative z-20 flex items-center gap-4">
        <button
          onClick={(e) => { e.stopPropagation(); togglePlay(); }}
          type="button"
          className="w-12 h-12 flex-shrink-0 bg-teal-600 text-white rounded-xl flex items-center justify-center hover:bg-teal-700 active:bg-teal-800 active:scale-95 transition-all shadow-lg hover:shadow-teal-200 cursor-pointer relative z-30"
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <svg className="w-6 h-6 animate-pulse" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" /></svg>
          ) : (
            <svg className="w-6 h-6 ml-1" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
          )}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <div className={`w-2 h-2 rounded-full bg-teal-500 ${isPlaying ? 'animate-ping' : ''}`}></div>
            <span className="text-[10px] font-black uppercase tracking-widest text-teal-800">Direct Recording</span>
          </div>
          <p className="text-sm font-bold text-slate-900 truncate pr-4 italic">
            {title || "Official Hymn Recording"}
          </p>

          <div className="mt-3 relative h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-teal-500 transition-all duration-300 rounded-full"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {isPlaying && (
          <div className="hidden md:flex gap-0.5 items-end h-6 pb-1">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="w-1 bg-teal-400 rounded-full animate-audio-bar" style={{ height: '40%', animationDelay: `${i * 150}ms` }}></div>
            ))}
          </div>
        )}
      </div>

      {/* Decorative BG - explicitly non-blocking */}
      <div className="absolute -right-4 -bottom-4 opacity-5 pointer-events-none select-none z-0">
        <svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className={isPlaying ? 'animate-spin-slow' : ''}><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
      </div>
    </div>
  );
};

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
