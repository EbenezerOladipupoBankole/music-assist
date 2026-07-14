
import React, { useState, useRef, useEffect } from 'react';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognitionCtor) {
      const recognitionInstance = new SpeechRecognitionCtor();
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'en-US';

      recognitionInstance.onstart = () => setIsListening(true);
      recognitionInstance.onresult = (event) => {
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
    <form onSubmit={handleSubmit} className="relative max-w-3xl mx-auto mb-2 group">
      {/* Background Glow */}
      <div className="absolute -inset-1.5 bg-gradient-to-r from-teal-500/10 via-emerald-500/5 to-teal-500/10 rounded-[2rem] blur-xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-700 pointer-events-none"></div>

      <div className="relative flex items-end gap-2 bg-white rounded-[1.6rem] border border-slate-200 focus-within:border-emerald-400 shadow-elevated focus-within:shadow-prominent transition-all duration-300 p-2 pr-2.5">

        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about hymns, conducting, or music theory..."
          aria-label="Message"
          className="flex-1 resize-none bg-transparent py-3.5 pl-4 pr-2 text-slate-800 focus:outline-none text-[15px] font-medium placeholder:text-slate-400 min-h-[52px] max-h-[200px]"
          disabled={disabled}
        />

        <div className="flex items-center gap-1.5 pb-0.5">
          {recognition && (
            <button
              type="button"
              onClick={toggleListening}
              disabled={disabled}
              aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
              className={`p-2.5 rounded-full transition-all flex items-center justify-center ${isListening
                ? 'bg-red-50 text-red-600 animate-pulse'
                : 'text-slate-400 hover:bg-slate-50 hover:text-teal-600'
                }`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="23" /><line x1="8" y1="23" x2="16" y2="23" /></svg>
            </button>
          )}

          <button
            type="submit"
            disabled={!input.trim() || disabled}
            aria-label="Send message"
            className={`p-2.5 rounded-2xl transition-all flex items-center justify-center ${!input.trim() || disabled
              ? 'bg-slate-100 text-slate-300'
              : 'bg-emerald-600 text-white shadow-elevated hover:bg-emerald-700 hover:-translate-y-0.5 active:translate-y-0'
              }`}
          >
            {disabled ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            )}
          </button>
        </div>
      </div>
    </form>
  );
};

export default ChatInput;
