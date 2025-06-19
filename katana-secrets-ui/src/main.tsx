import { KatanaProvider } from './context/KatanaContext';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.tsx';
import './index.css'; // Ensure Tailwind CSS is imported

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <KatanaProvider>
        <App />
      </KatanaProvider>
    </BrowserRouter>
  </React.StrictMode>,
);