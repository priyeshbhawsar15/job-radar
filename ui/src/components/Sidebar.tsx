import React from 'react';
import { NavLink } from 'react-router-dom';
import { PlaySquare, Layers, Briefcase, ChevronLeft, ChevronRight, X, LayoutDashboard } from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  collapsed,
  onToggleCollapse,
}) => {
  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/runs', label: 'Run History', icon: PlaySquare },
    { to: '/boards', label: 'Boards', icon: Layers },
    { to: '/jobs', label: 'Extracted Jobs', icon: Briefcase },
  ];

  return (
    <>
      {/* Mobile backdrop overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-xs lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Main Sidebar */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 border-r border-slate-200 dark:border-slate-800/80 bg-white dark:bg-slate-900/95 backdrop-blur-md transition-all duration-200 ease-in-out flex flex-col justify-between ${
          collapsed ? 'lg:w-20' : 'lg:w-64'
        } w-64 ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Brand Header */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-slate-200 dark:border-slate-800/80">
            <NavLink to="/runs" className="flex items-center gap-3 font-extrabold text-base tracking-tight text-slate-900 dark:text-white no-underline overflow-hidden">
              <div className="relative flex items-center justify-center w-8 h-8 rounded-lg border-2 border-teal-500 dark:border-teal-400 bg-teal-500/10 text-teal-600 dark:text-teal-400 shrink-0 shadow-[0_0_15px_rgba(20,184,166,0.25)]">
                <span className="text-base font-bold">⌁</span>
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-teal-400 animate-ping opacity-75" />
                <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-teal-500" />
              </div>
              {!collapsed && (
                <span className="font-bold text-slate-900 dark:text-white whitespace-nowrap">
                  Job Radar
                </span>
              )}
            </NavLink>

            {/* Desktop Collapse Toggle */}
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex items-center justify-center p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>

            {/* Mobile Close Button */}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 lg:hidden"
              aria-label="Close menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Items */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                end={item.to === '/'}
                className={({ isActive }: { isActive: boolean }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-teal-500/10 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 font-semibold shadow-xs border-l-2 border-teal-500'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
                  } ${collapsed ? 'justify-center px-0' : ''}`
                }
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="w-4 h-4 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </nav>

          {/* Footer Note */}
          {!collapsed && (
            <div className="p-4 border-t border-slate-200 dark:border-slate-800/80">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 text-[11px] text-slate-500 dark:text-slate-400 border border-slate-200/60 dark:border-slate-800 leading-tight">
                <div className="font-semibold text-slate-800 dark:text-slate-200 mb-1">Operator Workspace</div>
                <div>Detailed run data retained for 7 days</div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
