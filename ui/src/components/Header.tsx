import React, { useState, useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Menu, Moon, Sun, Play, Wifi, WifiOff, ChevronRight } from 'lucide-react';
import { getBoard, getJob, getRun, getBoardRun } from '../data/mockData';

interface HeaderProps {
  onMenuClick: () => void;
  onRunClick: () => void;
  connected: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onMenuClick, onRunClick, connected }) => {
  const location = useLocation();
  const [dark, setDark] = useState<boolean>(() => {
    return localStorage.getItem('jr-theme') === 'dark' || document.documentElement.classList.contains('dark');
  });

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('jr-theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.setAttribute('data-theme', 'light');
      localStorage.setItem('jr-theme', 'light');
    }
  }, [dark]);

  const toggleTheme = () => {
    setDark((prev) => !prev);
  };

  // Helper to generate dynamic breadcrumb path components
  const renderBreadcrumbs = () => {
    const parts = location.pathname.split('/').filter(Boolean);
    if (parts.length === 0) {
      return <span className="font-medium text-slate-900 dark:text-white">Overview</span>;
    }

    const breadcrumbList: { label: string; to?: string }[] = [];

    if (parts[0] === 'runs') {
      breadcrumbList.push({ label: 'Runs', to: '/runs' });
      if (parts[1]) {
        const r = getRun(parts[1]);
        breadcrumbList.push({ label: r ? r.id : parts[1] });
      }
    } else if (parts[0] === 'boards') {
      breadcrumbList.push({ label: 'Boards', to: '/boards' });
      if (parts[1]) {
        const b = getBoard(parts[1]);
        const boardName = b ? b.name : parts[1];
        if (parts[2] === 'config') {
          breadcrumbList.push({ label: boardName, to: `/boards/${parts[1]}` });
          breadcrumbList.push({ label: 'Configuration' });
        } else {
          breadcrumbList.push({ label: boardName });
        }
      }
    } else if (parts[0] === 'board-runs') {
      if (parts[1]) {
        const br = getBoardRun(parts[1]);
        if (br) {
          breadcrumbList.push({ label: 'Runs', to: '/runs' });
          breadcrumbList.push({ label: br.run.id, to: `/runs/${br.run.id}` });
          breadcrumbList.push({ label: br.board.name, to: `/boards/${br.board.id}` });
          breadcrumbList.push({ label: parts[1] });
        } else {
          breadcrumbList.push({ label: 'Board Runs', to: '/runs' });
          breadcrumbList.push({ label: parts[1] });
        }
      }
    } else if (parts[0] === 'jobs') {
      breadcrumbList.push({ label: 'Jobs', to: '/jobs' });
      if (parts[1]) {
        const j = getJob(parts[1]);
        breadcrumbList.push({ label: j ? j.title : parts[1] });
      }
    } else {
      breadcrumbList.push({ label: parts[0].charAt(0).toUpperCase() + parts[0].slice(1) });
    }

    return (
      <nav className="flex items-center space-x-1.5 text-xs text-slate-500 dark:text-slate-400">
        {breadcrumbList.map((item, index) => (
          <React.Fragment key={index}>
            {index > 0 && <ChevronRight className="w-3 h-3 text-slate-400 shrink-0" />}
            {item.to && index < breadcrumbList.length - 1 ? (
              <Link to={item.to} className="hover:text-teal-600 dark:hover:text-teal-400 font-medium transition-colors">
                {item.label}
              </Link>
            ) : (
              <span className="font-semibold text-slate-900 dark:text-slate-100 truncate max-w-[200px] sm:max-w-[300px]">
                {item.label}
              </span>
            )}
          </React.Fragment>
        ))}
      </nav>
    );
  };

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 sm:px-6 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800/80">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Dynamic Breadcrumb Bar */}
        <div className="min-w-0">{renderBreadcrumbs()}</div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {connected ? (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 border border-teal-200 dark:border-teal-800/60">
            <Wifi className="w-3.5 h-3.5" />
            <span>SSE Connected</span>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
            <WifiOff className="w-3.5 h-3.5" />
            <span>Standby</span>
          </div>
        )}

        <button
          onClick={onRunClick}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs sm:text-sm font-semibold shadow-xs transition-all"
        >
          <Play className="w-3.5 h-3.5 fill-white" />
          <span>Run pipeline</span>
        </button>

        <button
          onClick={toggleTheme}
          id="theme"
          className="p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          title={`Switch to ${dark ? 'light' : 'dark'} theme`}
          aria-label={`Switch to ${dark ? 'light' : 'dark'} theme`}
        >
          {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </header>
  );
};
