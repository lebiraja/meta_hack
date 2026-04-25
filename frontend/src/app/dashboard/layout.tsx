"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard/overview", label: "Overview", icon: "◈" },
  { href: "/dashboard/benchmark", label: "Benchmark", icon: "◆" },
  { href: "/dashboard/sessions", label: "Session Logs", icon: "◇" },
  { href: "/dashboard/leaderboard", label: "Leaderboard", icon: "★" },
  { href: "/dashboard/test-panel", label: "Test Panel", icon: "▶" },
  { href: "/dashboard/api-inspector", label: "API Inspector", icon: "{ }" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="h-screen flex overflow-hidden bg-neutral-950">
      {/* Sidebar */}
      <aside className="w-52 flex-shrink-0 border-r border-neutral-800 flex flex-col">
        {/* Logo area */}
        <div className="px-5 py-4 border-b border-neutral-800 space-y-2">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold text-neutral-100">
              Agent<span className="text-indigo-400">OS</span>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/blog" className="text-[10px] text-neutral-600 hover:text-neutral-400 transition-colors">
              ← Paper
            </Link>
            <Link href="/demo" className="text-[10px] text-neutral-600 hover:text-neutral-400 transition-colors">
              Demo →
            </Link>
          </div>
        </div>

        {/* Nav section */}
        <div className="px-4 pt-5 pb-2">
          <span className="text-[9px] text-neutral-600 uppercase tracking-widest font-medium">
            Dashboard
          </span>
        </div>
        <nav className="flex flex-col gap-0.5 px-3 flex-1">
          {NAV.map(({ href, label, icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "px-3 py-2.5 rounded-lg text-xs transition-all duration-200 flex items-center gap-2.5",
                pathname === href
                  ? "bg-indigo-500/15 text-indigo-400 font-medium"
                  : "text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800/60"
              )}
            >
              <span className="text-[10px] w-4 text-center opacity-60">{icon}</span>
              {label}
            </Link>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-neutral-800">
          <p className="text-[9px] text-neutral-700">AgentOS v2.1.0</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}
