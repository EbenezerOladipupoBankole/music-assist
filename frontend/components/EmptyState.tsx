import React from 'react';
import { SUGGESTED_PROMPTS } from '../constants.ts';

interface EmptyStateProps {
  onPromptClick: (prompt: string) => void;
}

const EmptyState: React.FC<EmptyStateProps> = ({ onPromptClick }) => {
  return (
    <div className="min-h-full flex flex-col items-center justify-center max-w-2xl mx-auto px-6 py-6">
      <div className="text-center mb-10 lg:mb-14">
        <div className="w-20 h-20 lg:w-24 lg:h-24 bg-white rounded-[2rem] flex items-center justify-center mx-auto mb-7 lg:mb-8 shadow-elevated border border-slate-100 relative overflow-hidden">
          <img src="/logo.png" alt="Music Assist Logo" className="w-4/5 h-4/5 object-contain" />
        </div>
        <h3 className="text-3xl lg:text-5xl font-serif font-bold text-slate-900 mb-4 lg:mb-5 tracking-tight leading-[1.15]">
          Sacred Guidance for <br /><span className="text-teal-600 italic">Sacred Music</span>
        </h3>
        <p className="text-slate-500 text-sm max-w-md mx-auto leading-relaxed">
          Welcome to Music Assist. I am your specialized RAG-powered assistant for hymns, conducting, and official music policy.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
        {SUGGESTED_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => onPromptClick(prompt)}
            className="p-5 bg-white border border-slate-200 hover:border-teal-300 rounded-2xl text-left shadow-subtle hover:shadow-elevated transition-all duration-300 group relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-20 h-20 bg-teal-50 rounded-full -mr-10 -mt-10 transition-transform duration-500 group-hover:scale-125"></div>
            <span className="relative text-2xs font-bold uppercase text-slate-400 group-hover:text-teal-600 block mb-1.5 transition-colors">Consultation</span>
            <span className="relative text-sm text-slate-700 group-hover:text-slate-900 leading-snug font-semibold transition-colors">{prompt}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default EmptyState;
