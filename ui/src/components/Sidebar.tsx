import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, PlaySquare, Layers, Briefcase, Radar, X } from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/runs', label: 'Pipeline Runs', icon: PlaySquare },
    { to: '/boards', label: 'Board Registry', icon: Layers },
    { to: '/jobs', label: 'Candidate Jobs', icon: Briefcase },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Brand header */}
          <div className="flex items-center justify-between h-16 px-6 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-teal-500/10 text-teal-600 dark:text-teal-400">
                <Radar className="w-5 h-5" />
                <span className="absolute top-0 right-0 w-2 h-2 rounded-full bg-teal-500 animate-ping" />
              </div>
              <div>
                <span className="font-semibold text-slate-900 dark:text-white tracking-tight">Job Radar</span>
                <span className="block text-[10px] uppercase font-mono tracking-wider text-slate-400">v0.1.0-alpha</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 lg:hidden"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={({ isActive }: { isActive: boolean }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-teal-50 text-teal-700 dark:bg-teal-950/50 dark:text-teal-300'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
                  }`
                }
              >
                <item.icon className="w-4 h-4" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          {/* Footer note */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800">
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-xs text-slate-500 dark:text-slate-400 border border-slate-200/60 dark:border-slate-800">
              <div className="font-medium text-slate-700 dark:text-slate-300 mb-1">Local Mode Active</div>
              <div>Bound to static browser service domain. Automatic ingestion enabled.</div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
