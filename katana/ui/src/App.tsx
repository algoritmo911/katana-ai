import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Layout/Navbar';
import DashboardPage from './pages/DashboardPage';
import ConnectionsPage from './pages/ConnectionsPage';
import MemoryPage from './pages/MemoryPage';
import SettingsPage from './pages/SettingsPage';
import OnboardingPage from './pages/OnboardingPage';

// MainLayout component is not used in this App.tsx structure,
// Navbar and footer are part of App's direct render.
// If MainLayout was intended to wrap <Routes>, it would need an <Outlet />.

function App() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <Navbar />
      <main className="flex-grow container mx-auto px-4 py-8"> {/* Added common main styling */}
        <Routes>
          <Route path="/" element={<Navigate replace to="/dashboard" />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/connections" element={<ConnectionsPage />} />
          <Route path="/memory" element={<MemoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="*" element={<Navigate replace to="/dashboard" />} />
        </Routes>
      </main>
      <footer className="text-center p-4 text-sm text-gray-500 border-t dark:border-gray-700 mt-auto">
        Katana UI - Interactive Core
      </footer>
    </div>
  );
}

export default App;
