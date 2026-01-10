
export const APP_NAME = "Music-Assist";

export const SUGGESTED_PROMPTS = [
  "Standard policy on ward choir auditions",
  "How to conduct 'High on the Mountain Top'",
  "Requirements for Sacrament Meeting solos",
  "A sample 4-week choir rehearsal plan"
];

export const COLORS = {
  primary: 'bg-[#0f172a]', // Midnight Navy
  accent: '#b45309', // Amber Gold
  teal: '#0d9488', // Sage Teal
  surface: 'bg-[#fdfbf7]', // Linen White
  card: 'bg-white border border-slate-100 shadow-sm hover:shadow-md transition-all',
  chatUser: 'bg-[#1e293b] text-white shadow-xl',
  chatAI: 'bg-white border border-slate-200 text-slate-800 shadow-sm'
};

export const REFERENCE_LINKS = [
  { name: 'General Handbook: Music', url: 'https://www.churchofjesuschrist.org/study/manual/general-handbook/19-music' },
  { name: 'New Hymnbook Updates', url: 'https://www.churchofjesuschrist.org/initiative/new-hymns' },
  { name: 'Sacred Music Library', url: 'https://www.churchofjesuschrist.org/media/music' },
  { name: 'Conducting Techniques', url: 'https://www.churchofjesuschrist.org/study/manual/conducting-course' }
];

// Official guidance instructions for the Music Specialist AI
export const SYSTEM_INSTRUCTION = "You are a world-class Music Specialist and Ecclesiastical Music Consultant. Your expertise covers the General Handbook of The Church of Jesus Christ of Latter-day Saints (specifically section 19 on Music), conducting techniques, hymnology, and ward/stake music administration. Provide authoritative, clear, and encouraging guidance based on official sources. When answering questions about policy, prioritize the General Handbook. If providing musical advice (like conducting or rehearsal planning), draw on established professional standards suitable for sacred settings.";
