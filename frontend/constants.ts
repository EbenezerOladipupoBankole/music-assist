
export const APP_NAME = "Music-Assist";

export const SUGGESTED_PROMPTS = [
  "Standard policy on ward choir auditions",
  "How to conduct 'High on the Mountain Top'",
  "Requirements for Sacrament Meeting solos",
  "A sample 4-week choir rehearsal plan"
];

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
