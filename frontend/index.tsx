
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import ErrorBoundary from './components/ErrorBoundary.tsx';
import './index.css';

console.log("Music-Assist: Initializing application...");

const container = document.getElementById('root');
if (container) {
  try {
    const root = createRoot(container);
    root.render(
      <React.StrictMode>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </React.StrictMode>
    );
    console.log("Music-Assist: Application mounted successfully.");
  } catch (error) {
    console.error("Music-Assist: Rendering error:", error);
  }
} else {
  console.error("Music-Assist: Could not find root element.");
}
