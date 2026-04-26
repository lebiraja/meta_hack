"use client";
import Link from "next/link";
import { GitFork, ExternalLink } from "lucide-react";

const LINKS = {
  Project: [
    { label: "Live Demo", href: "/demo" },
    { label: "Dashboard", href: "/dashboard" },
    { label: "API Docs", href: "/dashboard/api-inspector" },
    { label: "Leaderboard", href: "/dashboard/leaderboard" },
  ],
  Research: [
    { label: "Training Notebook", href: "https://colab.research.google.com/drive/1RD3OUfixs7UWs9m7I0PLXPg-48OWYzKG?usp=sharing", external: true },
    { label: "HF Space", href: "https://huggingface.co/spaces/lebiraja/customer-support-env", external: true },
    { label: "Source Code", href: "https://github.com/lebiraja/meta_hack", external: true },
    { label: "Benchmark Suite", href: "/dashboard/benchmark" },
  ],
};

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-slate-900 py-16">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-8 md:grid-cols-[2fr_1fr_1fr]">
          {/* Brand */}
          <div>
            <div className="mb-4 text-xl font-bold text-white">AgentOS</div>
            <p className="max-w-xs text-sm text-slate-400 leading-relaxed">
              A hierarchical multi-agent RL system for customer support, built for the
              Meta × PyTorch × Scaler OpenEnv Hackathon 2026. Research, not production.
            </p>
            <div className="mt-6 flex gap-3">
              <a
                href="https://github.com/lebiraja/meta_hack"
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-800 text-slate-400 transition-all hover:border-slate-600 hover:text-white"
              >
                <GitFork className="h-4 w-4" />
              </a>
              <a
                href="https://huggingface.co/spaces/lebiraja/customer-support-env"
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-9 items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-3 text-xs text-slate-400 transition-all hover:border-slate-600 hover:text-white"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                HF Space
              </a>
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(LINKS).map(([heading, links]) => (
            <div key={heading}>
              <div className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-500">
                {heading}
              </div>
              <ul className="space-y-2.5">
                {links.map(({ label, href, ...rest }) => {
                  const external = "external" in rest ? rest.external : false;
                  return (
                    <li key={label}>
                      {external ? (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 text-sm text-slate-400 transition-colors hover:text-white"
                        >
                          {label}
                          <ExternalLink className="h-3 w-3 opacity-50" />
                        </a>
                      ) : (
                        <Link
                          href={href}
                          className="text-sm text-slate-400 transition-colors hover:text-white"
                        >
                          {label}
                        </Link>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-slate-800 pt-8 text-xs text-slate-600 md:flex-row">
          <span>© 2026 Team X-Force · Meta × PyTorch × Scaler OpenEnv Hackathon</span>
          <span>Built with Next.js · Framer Motion · Tailwind v4 · Unsloth · GRPO</span>
        </div>
      </div>
    </footer>
  );
}
