import React from 'react';
import './App.css';
import CommandSender from './components/CommandSender/CommandSender';
import KatanaStatus from './components/KatanaStatus/KatanaStatus';
import LogViewer from './components/LogViewer/LogViewer';
import { CommandProvider } from './context/CommandContext';

function App() {
  return (
    <div className="min-h-screen bg-gray-800 text-white p-4">
      <header className="mb-8">
        <h1 className="text-4xl font-bold text-center">Katana Dashboard</h1>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="md:col-span-1">
          <KatanaStatus />
        </div>
        <div className="md:col-span-1">
          <CommandProvider>
            <CommandSender />
          </CommandProvider>
        </div>
        <div className="md:col-span-2">
          <LogViewer />
        </div>
      </main>

      <footer className="text-center text-gray-500 mt-8">
        <p>&copy; 2025 Katana AI. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;