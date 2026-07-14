import React from 'react';
import { SUGGESTED_PROMPTS } from '../constants.ts';

interface EmptyStateProps {
  onPromptClick: (prompt: string) => void;
}

const EmptyState: React.FC<EmptyStateProps> = ({ onPromptClick }) => {
  return (
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
            onClick={() => onPromptClick(prompt)}
            className="p-5 lg:p-6 bg-white border border-slate-200/60 hover:border-teal-500/30 rounded-2xl lg:rounded-[1.8rem] text-left hover:shadow-[0_20px_40px_rgba(15,23,42,0.06)] transition-all duration-500 group relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-24 h-24 bg-teal-50/20 rounded-full -mr-12 -mt-12 transition-transform group-hover:scale-150 duration-700"></div>
            <span className="text-[10px] lg:text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 group-hover:text-emerald-600 block mb-1 lg:mb-2 transition-colors">Consultation</span>
            <span className="text-[14px] lg:text-[15px] text-slate-600 group-hover:text-slate-900 leading-snug font-bold transition-colors">{prompt}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default EmptyState;
