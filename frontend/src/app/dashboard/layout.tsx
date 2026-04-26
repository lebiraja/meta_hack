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

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50">
      <aside className="w-52 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="px-5 py-4 border-b border-gray-100 space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-gray-900 rounded flex items-center justify-center">
              <span className="text-white text-[10px] font-bold">A</span>
            </div>
            <span className="text-[14px] font-bold text-gray-900">
              AgentOS
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/blog" className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors font-medium">← Paper</Link>
            <Link href="/demo" className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors font-medium">Demo →</Link>
          </div>
        </div>

        <div className="px-4 pt-5 pb-2">
          <span className="text-[9px] text-gray-400 uppercase tracking-widest font-bold">Dashboard</span>
        </div>
        <nav className="flex flex-col gap-0.5 px-3 flex-1">
          {NAV.map(({ href, label, icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "px-3 py-2.5 rounded-lg text-xs transition-all duration-200 flex items-center gap-2.5",
                pathname === href
                  ? "bg-indigo-50 text-indigo-700 font-semibold"
                  : "text-gray-500 hover:text-gray-800 hover:bg-gray-50"
              )}
            >
              <span className="text-[10px] w-4 text-center opacity-50">{icon}</span>
              {label}
            </Link>
          ))}
        </nav>

        <div className="px-5 py-4 border-t border-gray-100">
          <p className="text-[9px] text-gray-300">AgentOS v2.1.0</p>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}
