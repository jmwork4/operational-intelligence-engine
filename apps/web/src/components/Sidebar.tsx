"use client";

import {
  LayoutDashboard,
  Activity,
  GitBranch,
  Bell,
  FileText,
  Sparkles,
  Settings,
} from "lucide-react";
import clsx from "clsx";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, active: true },
  { label: "Events", icon: Activity, active: false },
  { label: "Rules", icon: GitBranch, active: false },
  { label: "Alerts", icon: Bell, active: false },
  { label: "Documents", icon: FileText, active: false },
  { label: "AI Copilot", icon: Sparkles, active: false },
  { label: "Settings", icon: Settings, active: false },
];

export function Sidebar() {
  return (
    <aside className="w-64 bg-navy-900 flex flex-col flex-shrink-0">
      {/* Brand */}
      <div className="h-16 flex items-center px-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">OI</span>
          </div>
          <span className="text-white font-semibold text-base tracking-tight">
            OIE
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <a
              key={item.label}
              href="#"
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150",
                item.active
                  ? "bg-teal-600/15 text-teal-400"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              )}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span>{item.label}</span>
            </a>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-full bg-navy-700 flex items-center justify-center">
            <span className="text-xs text-gray-300 font-medium">JM</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white font-medium truncate">J. Moore</p>
            <p className="text-xs text-gray-500 truncate">Admin</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
