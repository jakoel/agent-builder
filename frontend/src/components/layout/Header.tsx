"use client";

import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/agents/new": "Create New Agent",
  "/runs": "Run History",
  "/settings": "Settings",
  "/tool-runner": "Tool Runner",
};

export default function Header() {
  const pathname = usePathname();

  let title = titles[pathname];
  if (!title) {
    if (pathname.startsWith("/agents/") && pathname.endsWith("/runs")) {
      title = "Agent Run History";
    } else if (pathname.startsWith("/agents/")) {
      title = "Agent Detail";
    } else {
      title = "Agent Builder";
    }
  }

  return (
    <header className="h-12 border-b border-slate-800/60 bg-slate-900/40 backdrop-blur-sm flex items-center px-6 shrink-0">
      <h2 className="text-sm font-semibold text-slate-200 tracking-tight">{title}</h2>
    </header>
  );
}
