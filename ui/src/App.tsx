import './App.css';
import CommandSender from './components/CommandSender/CommandSender';
import KatanaStatus from './components/KatanaStatus/KatanaStatus';
import LogViewer from './components/LogViewer/LogViewer';

// Placeholder components - these will be created in later steps
// For now, create dummy functional components here or import them if they exist with basic placeholders.

function App() {
  return (
    <div className="min-h-screen bg-gray-800 text-white p-4">
      <header className="mb-8">
        <h1 className="text-4xl font-bold text-center">Katana Dashboard</h1>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <CommandSender />
        <KatanaStatus />
        <LogViewer /> {/* This will span 2 columns on medium screens and up if it's the only item in its row, or take full width on small screens */}
      </div>

      <footer className="mt-12 text-center text-sm text-gray-400">
        <p>Katana Control Interface</p>
      </footer>
    </div>
  );
}

export default App;
