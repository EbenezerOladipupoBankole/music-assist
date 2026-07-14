import React, { useState, useRef } from 'react';
import { API_BASE_URL } from '../constants.ts';

interface AudioPlayerProps {
  url: string;
  title?: string;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({ url, title }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [playbackError, setPlaybackError] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  const fullUrl = url.startsWith('/') ? `${API_BASE_URL}${url}` : url;

  const togglePlay = async () => {
    if (audioRef.current) {
      try {
        if (isPlaying) {
          audioRef.current.pause();
          setIsPlaying(false);
        } else {
          setPlaybackError(false);
          await audioRef.current.play();
          setIsPlaying(true);
        }
      } catch (err) {
        console.error("Audio playback failed:", err);
        setIsPlaying(false);
        setPlaybackError(true);
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
    <div className="mt-4 p-4 bg-teal-50/50 border-l-[3px] border-emerald-500 rounded-r-xl relative overflow-hidden group select-none">
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
          className="w-12 h-12 flex-shrink-0 bg-emerald-600 text-white rounded-xl flex items-center justify-center hover:bg-emerald-700 active:bg-emerald-800 active:scale-95 transition-all shadow-elevated cursor-pointer relative z-30"
          aria-label={isPlaying ? 'Pause hymn recording' : 'Play hymn recording'}
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
            <span className="text-2xs font-bold uppercase text-teal-800">Direct Recording</span>
          </div>
          <p className="text-sm font-bold text-slate-900 truncate pr-4 italic">
            {title || "Official Hymn Recording"}
          </p>

          {playbackError ? (
            <p className="mt-2 text-xs font-semibold text-red-600" role="alert">
              Playback failed. Please try again in a moment.
            </p>
          ) : (
            <div className="mt-3 relative h-1.5 w-full bg-slate-200/80 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 bg-teal-500 transition-all duration-300 rounded-full"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          )}
        </div>

        {isPlaying && (
          <div className="hidden md:flex gap-0.5 items-end h-6 pb-1">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="w-1 bg-teal-400 rounded-full animate-audio-bar" style={{ height: '40%', animationDelay: `${i * 150}ms` }}></div>
            ))}
          </div>
        )}
      </div>

      {/* Decorative BG – explicitly non-interactive */}
      <div className="absolute -right-4 -bottom-4 opacity-5 pointer-events-none select-none z-0">
        <svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className={isPlaying ? 'animate-spin-slow' : ''}><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
      </div>
    </div>
  );
};

export default AudioPlayer;
