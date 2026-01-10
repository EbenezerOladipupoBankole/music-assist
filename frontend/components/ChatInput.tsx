
import React, { useState, useRef, useEffect } from 'react';
import { COLORS } from '../constants.ts';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognitionInstance = new SpeechRecognition();
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'en-US';

      recognitionInstance.onstart = () => setIsListening(true);
      recognitionInstance.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInput((prev) => (prev ? `${prev.trim()} ${transcript}` : transcript));
        setIsListening(false);
      };
      recognitionInstance.onerror = () => setIsListening(false);
      recognitionInstance.onend = () => setIsListening(false);
      setRecognition(recognitionInstance);
    }
  }, []);

  const toggleListening = () => {
    if (isListening) recognition?.stop();
    else recognition?.start();
  };

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <form onSubmit={handleSubmit} className="relative group">
      <div className="absolute -inset-1 bg-gradient-to-r from-teal-600/20 to-amber-600/20 rounded-[2.5rem] blur opacity-25 group-focus-within:opacity-100 transition duration-1000"></div>
      
      <div className="relative flex flex-col bg-white rounded-[2rem] border border-slate-200 shadow-xl overflow-hidden ring-1 ring-slate-900/5">
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your inquiry here or speak..."
          className="w-full resize-none bg-transparent py-5 pl-7 pr-32 text-slate-700 focus:outline-none scrollbar-hide text-lg font-medium placeholder:text-slate-300"
          disabled={disabled}
        />
        
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
          {recognition && (
            <button
              type="button"
              onClick={toggleListening}
              disabled={disabled}
              className={`p-3.5 rounded-full transition-all flex items-center justify-center ${
                isListening 
                  ? 'bg-red-50 text-red-600 animate-pulse' 
                  : 'text-slate-400 hover:bg-slate-50 hover:text-teal-600'
              }`}
              title={isListening ? "Listening..." : "Voice input"}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" viewBox="0 0 16 16">
                <path d="M3.5 6.5A.5.5 0 0 1 4 7v1a4 4 0 0 0 8 0V7a.5.5 0 0 1 1 0v1a5 5 0 0 1-4.5 4.975V15h3a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1h3v-2.025A5 5 0 0 1 3 8V7a.5.5 0 0 1 .5-.5z"/>
                <path d="M10 8a2 2 0 1 1-4 0V3a2 2 0 1 1 4 0v5zM8 0a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V3a3 3 0 0 0-3-3z"/>
              </svg>
            </button>
          )}
          
          <button
            type="submit"
            disabled={!input.trim() || disabled}
            className="bg-slate-900 hover:bg-slate-800 text-white p-3.5 rounded-full shadow-lg shadow-slate-200 disabled:opacity-30 disabled:shadow-none transition-all"
          >
            {disabled ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path d="m22 2-7 20-4-9-9-4Z"></path><path d="M22 2 11 13"></path></svg>
            )}
          </button>
        </div>
      </div>
    </form>
  );
};

export default ChatInput;
