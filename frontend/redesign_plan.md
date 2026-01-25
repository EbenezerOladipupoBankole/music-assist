# Music-Assist UI Redesign Plan

## Aesthetic Goal: "Sacred Sophistication"
Creating a high-end, modern interface that stays respectful to the sacred music context while feeling like a premium 2026 AI application.

### 1. Design System & Tokens
*   **Typography**: Transition to a hybrid of 'Inter' (San-serif for UI elements) and 'Merriweather' (Serif for AI response content for a "handbook" feel).
*   **Color Palette**:
    *   **Background**: `slate-50` (soft light gray) with linen-pattern overlay.
    *   **Primary Elements**: Deep Navy (`#0f172a`) for stable structural components.
    *   **Accents**: Amber Gold (`#b45309`) for highlights and Sage Teal (`#0d9488`) for positive actions.
*   **Glassmorphism**: Use `backdrop-blur-md` on headers and message bubbles.

### 2. Layout Enhancements
*   **Sidebar/Navigation**: Introduce a sleek sidebar for history (desktop) or a floating action menu.
*   **Chat Container**: Maximize vertical space with a "bottom-up" message stream that feels infinite.
*   **Input Dock**: A floating pill-shaped input with glowing focus states.

### 3. Component Updates
*   **Message Bubbles**:
    *   User: Sharp asymmetric corners, deep gradient fill.
    *   AI: Minimalist border-less design with subtle shadow and Serif typography.
*   **Thinking State**: Pulsing skeleton loaders instead of simple bouncing dots.
*   **Transitions**: Use Framer Motion (or simple CSS transitions) for smooth message entry.

### 4. Step-by-Step Implementation
1.  **Phase 1**: Update `index.css` with a global design system and Google Fonts.
2.  **Phase 2**: Redesign `ChatMessage.tsx` for the new bubble aesthetic.
3.  **Phase 3**: Revamp `ChatInput.tsx` with high-fidelity input styling.
4.  **Phase 4**: Polish `App.tsx` layout structure (Sidebar + Main View).
