
export const APP_NAME = "Music-Assist";

export const SUGGESTED_PROMPTS = [
  "Standard policy on ward choir auditions",
  "How to conduct 'High on the Mountain Top'",
  "Requirements for Sacrament Meeting solos",
  "A sample 4-week choir rehearsal plan"
];

export const COLORS = {
  primary: 'bg-[#0F172A]', // Deep Slate Midnight
  accent: '#F59E0B', // Crisp Amber
  teal: '#0D9488', // Sharp Teal 600
  emerald: '#10B981', // Emerald 500
  surface: 'bg-[#F8FAFC]', // Cool Slate 50
  card: 'bg-white border border-slate-200/60 shadow-sm hover:shadow-md transition-all',
  chatUser: 'bg-[#1E293B] text-white shadow-xl ring-1 ring-slate-800',
  chatAI: 'bg-white border border-slate-200 text-slate-800 shadow-sm shadow-slate-200/50'
};

export const REFERENCE_LINKS = [
  { name: 'General Handbook: Music', url: 'https://www.churchofjesuschrist.org/study/manual/general-handbook/19-music' },
  { name: 'New Hymnbook Updates', url: 'https://www.churchofjesuschrist.org/initiative/new-hymns' },
  { name: 'Sacred Music Library', url: 'https://www.churchofjesuschrist.org/media/music' },
  { name: 'Conducting Techniques', url: 'https://www.churchofjesuschrist.org/study/manual/conducting-course' }
];

const isLocalHost = typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

// VITE_API_BASE_URL (frontend/.env.development, frontend/.env.production) wins when set;
// otherwise fall back to a hostname-based guess so the app still works without it configured.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  (isLocalHost ? 'http://127.0.0.1:8080' : 'https://music-assist-backend.onrender.com');
