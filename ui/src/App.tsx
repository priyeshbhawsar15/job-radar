import { useState } from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { RunModal } from './components/RunModal';
import { Dashboard } from './pages/Dashboard';
import { Runs } from './pages/Runs';
import { Boards } from './pages/Boards';
import { BoardConfig } from './pages/BoardConfig';
import { Jobs } from './pages/Jobs';
import { useSSE } from './hooks/useSSE';

export function App() {
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [runModalOpen, setRunModalOpen] = useState<boolean>(false);
  const { connected } = useSSE('/api/v1/stream');

  return (
    <Router>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex">
        {/* Navigation Sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 lg:pl-64">
          <Header
            onMenuClick={() => setSidebarOpen(true)}
            onRunClick={() => setRunModalOpen(true)}
            connected={connected}
          />

          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard onRunClick={() => setRunModalOpen(true)} />} />
              <Route path="/runs" element={<Runs />} />
              <Route path="/boards" element={<Boards />} />
              <Route path="/boards/config/:id" element={<BoardConfig />} />
              <Route path="/jobs" element={<Jobs />} />
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
