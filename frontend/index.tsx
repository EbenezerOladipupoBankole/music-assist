
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';

console.log("Music-Assist: Initializing application...");

const container = document.getElementById('root');
if (container) {
  try {
    const root = createRoot(container);
    root.render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
    console.log("Music-Assist: Application mounted successfully.");
  } catch (error) {
    console.error("Music-Assist: Rendering error:", error);
  }
} else {
  console.error("Music-Assist: Could not find root element.");
}
