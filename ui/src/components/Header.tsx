import React from 'react';
import { Menu, Moon, Sun, Play, Wifi, WifiOff } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

interface HeaderProps {
  onMenuClick: () => void;
  onRunClick: () => void;
  connected: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onMenuClick, onRunClick, connected }) => {
  const [dark, setDark] = React.useState<boolean>(
    document.documentElement.classList.contains('dark')
  );

  const toggleTheme = () => {
    if (dark) {
      document.documentElement.classList.remove('dark');
      setDark(false);
    } else {
      document.documentElement.classList.add('dark');
      setDark(true);
    }
  };

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 sm:px-6 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2">
          {connected ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/60">
              <Wifi className="w-3.5 h-3.5" />
              <span>SSE Connected</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
              <WifiOff className="w-3.5 h-3.5" />
              <span>Polling Standby</span>
            </div>
          )}
          <StatusBadge status="healthy" label="System Ready" size="sm" />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onRunClick}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs sm:text-sm font-medium shadow-xs transition-colors"
        >
          <Play className="w-4 h-4 fill-white" />
          <span>Trigger Run</span>
        </button>

        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          title="Toggle color theme"
        >
          {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
      </div>
    </header>
  );
};
