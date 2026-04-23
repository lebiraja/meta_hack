"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard/overview", label: "Overview" },
  { href: "/dashboard/benchmark", label: "Benchmark" },
  { href: "/dashboard/sessions", label: "Session Logs" },
  { href: "/dashboard/leaderboard", label: "Leaderboard" },
  { href: "/dashboard/test-panel", label: "Test Panel" },
  { href: "/dashboard/api-inspector", label: "API Inspector" },
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
      <aside className="w-44 flex-shrink-0 border-r border-neutral-800 flex flex-col py-4">
        <div className="px-4 mb-5">
          <Link
            href="/demo"
            className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            ← Demo
          </Link>
        </div>
        <div className="px-4 mb-3">
          <span className="text-[9px] text-neutral-600 uppercase tracking-widest">
            Dashboard
          </span>
        </div>
        <nav className="flex flex-col gap-0.5 px-2 flex-1">
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "px-3 py-2 rounded text-xs transition-colors",
                pathname === href
                  ? "bg-indigo-500/15 text-indigo-400"
                  : "text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800"
              )}
            >
              {label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}
