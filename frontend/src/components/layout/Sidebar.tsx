"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { History, LayoutDashboard, PlusCircle, Settings, Wrench } from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/agents/new", label: "New Agent", icon: PlusCircle },
  { href: "/runs", label: "Run History", icon: History },
  { href: "/tool-runner", label: "Tool Runner", icon: Wrench },
];

export default function Sidebar() {
  const pathname = usePathname();

  function isActive(href: string) {
    return href === "/" ? pathname === "/" : pathname.startsWith(href);
  }

  return (
    <aside className="w-60 min-h-screen bg-slate-900 border-r border-slate-800/60 flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-slate-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20 shrink-0">
            <span className="text-white text-xs font-bold">A</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white tracking-tight leading-none">
              Agent Builder
            </h1>
            <p className="text-[10px] text-slate-500 mt-0.5 leading-none">Platform</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                active
                  ? "bg-violet-500/10 text-violet-300 shadow-sm"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
              }`}
            >
              <Icon
                size={16}
                className={active ? "text-violet-400" : "text-slate-500"}
              />
              <span>{label}</span>
              {active && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-violet-400" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Settings */}
      <div className="p-3 border-t border-slate-800/60">
        <Link
          href="/settings"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
            isActive("/settings")
              ? "bg-violet-500/10 text-violet-300"
              : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
          }`}
        >
          <Settings
            size={16}
            className={isActive("/settings") ? "text-violet-400" : "text-slate-500"}
          />
          <span>Settings</span>
        </Link>
      </div>
    </aside>
  );
}
