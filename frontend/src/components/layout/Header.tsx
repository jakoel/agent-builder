"use client";

import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/agents/new": "Create New Agent",
  "/runs": "Run History",
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
    <header className="h-14 border-b border-gray-800 bg-gray-900/50 backdrop-blur flex items-center px-6">
      <h2 className="text-sm font-semibold text-gray-100">{title}</h2>
    </header>
  );
}
