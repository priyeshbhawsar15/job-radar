import { useState } from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { RunModal } from './components/RunModal';

import { Runs } from './pages/Runs';
import { RunDetail } from './pages/RunDetail';
import { Boards } from './pages/Boards';
import { BoardDetail } from './pages/BoardDetail';
import { BoardConfig } from './pages/BoardConfig';
import { BoardRunLog } from './pages/BoardRunLog';
import { Jobs } from './pages/Jobs';
import { JobDetail } from './pages/JobDetail';
import { Dashboard } from './pages/Dashboard';
import { useSSE } from './hooks/useSSE';

export function App() {
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('jr-sidebar') === '1';
  });
  const [runModalOpen, setRunModalOpen] = useState<boolean>(false);
  const { connected } = useSSE('/api/v1/stream');

  const toggleSidebarCollapse = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('jr-sidebar', next ? '1' : '0');
      return next;
    });
  };

  return (
    <Router>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex font-sans antialiased selection:bg-teal-500 selection:text-white">
        {/* Navigation Sidebar */}
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          collapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapse}
        />

        {/* Main Content Area */}
        <div
          className={`flex-1 flex flex-col min-w-0 transition-all duration-200 ${
            sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-64'
          }`}
        >
          <Header
            onMenuClick={() => setSidebarOpen(true)}
            onRunClick={() => setRunModalOpen(true)}
            connected={connected}
          />

          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard onRunClick={() => setRunModalOpen(true)} />} />
              <Route path="/runs" element={<Runs />} />
              <Route path="/runs/:id" element={<RunDetail />} />
              <Route path="/boards" element={<Boards />} />
              <Route path="/boards/:id" element={<BoardDetail />} />
              <Route path="/boards/:id/config" element={<BoardConfig />} />
              <Route path="/board-runs/:id" element={<BoardRunLog />} />
              <Route path="/jobs" element={<Jobs />} />
              <Route path="/jobs/:id" element={<JobDetail />} />
              <Route path="*" element={<Navigate to="/runs" replace />} />
            </Routes>
          </main>
        </div>

        {/* Manual Trigger Modal */}
        <RunModal isOpen={runModalOpen} onClose={() => setRunModalOpen(false)} />
      </div>
    </Router>
  );
}

export default App;
