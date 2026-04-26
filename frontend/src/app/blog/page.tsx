"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";

export default function BlogPage() {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/blog.md")
      .then((r) => r.text())
      .then((text) => {
        const lines = text.split("\n");
        const firstHrIdx = lines.findIndex((l, i) => i > 0 && l.trim() === "---");
        const cleaned = firstHrIdx > 0 ? lines.slice(firstHrIdx + 1).join("\n").trimStart() : text;
        setContent(cleaned);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: "'Times New Roman', Times, Georgia, serif" }}>
      {/* ── Nav ───────────────────────────────────────────────── */}
      <header className="border-b border-gray-200 bg-white sticky top-0 z-50">
        <div className="max-w-[820px] mx-auto px-6 py-3.5 flex items-center justify-between">
          <Link href="/blog" className="text-[15px] font-bold text-gray-900 tracking-tight">
            AgentOS
          </Link>
          <nav className="flex items-center gap-6">
            <Link href="/demo" className="text-[14px] text-gray-400 hover:text-gray-800 transition-colors">Demo</Link>
            <Link href="/dashboard" className="text-[14px] text-gray-400 hover:text-gray-800 transition-colors">Dashboard</Link>
            <a href="https://github.com/lebiraja/meta_hack" target="_blank" rel="noopener noreferrer"
              className="text-[14px] text-gray-400 hover:text-gray-800 transition-colors">GitHub</a>
          </nav>
        </div>
      </header>

      {/* ── Hero ──────────────────────────────────────────────── */}
      <div className="bg-gradient-to-b from-slate-50 to-white border-b border-gray-100">
        <div className="max-w-[820px] mx-auto px-6 pt-14 pb-10">
          <div className="flex items-center gap-2 mb-5">
            <span className="px-2 py-0.5 text-[11px] font-bold uppercase tracking-[0.12em] text-indigo-700 bg-indigo-50 rounded">
              Technical Report
            </span>
            <span className="text-[12px] text-gray-400">·</span>
            <span className="text-[12px] text-gray-400">April 2026</span>
          </div>

          <h1 className="text-[28px] sm:text-[32px] font-bold text-gray-900 leading-[1.25] tracking-tight max-w-[680px]">
            Training AI Agents to Navigate Indian Enterprise Customer&nbsp;Support
          </h1>
          <p className="mt-3 text-[17px] text-gray-500 leading-[1.6] italic max-w-[600px]">
            A 3-Level Hierarchy with Policy Drift, Hinglish, and DB-Grounded Responses
          </p>

          <div className="mt-5 text-[14px]">
            <span className="font-bold text-gray-800">Team X-Force</span>
            <span className="text-gray-300 mx-2">·</span>
            <span className="text-gray-400">Meta × PyTorch × Scaler OpenEnv Hackathon</span>
          </div>

          {/* ── Key results strip ─────────────────────────────── */}
          <div className="mt-7 grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { num: "+15–19pp", label: "Improvement over 70B baseline" },
              { num: "8.75×", label: "Smaller model, better results" },
              { num: "3-Level", label: "Agent hierarchy" },
              { num: "5 Stages", label: "Curriculum training" },
            ].map(({ num, label }) => (
              <div key={num} className="bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm">
                <div className="text-[18px] font-bold text-indigo-700">{num}</div>
                <div className="text-[11px] text-gray-400 mt-0.5 leading-tight">{label}</div>
              </div>
            ))}
          </div>

          {/* ── Links ──────────────────────────────────────────── */}
          <div className="mt-6 flex flex-wrap gap-2.5 text-[13px]">
            <Link href="/demo"
              className="px-4 py-2 bg-indigo-700 text-white rounded-lg hover:bg-indigo-800 transition-colors font-bold">
              Try the Demo →
            </Link>
            <a href="https://github.com/lebiraja/meta_hack" target="_blank" rel="noopener noreferrer"
              className="px-4 py-2 text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-all">
              Source Code ↗
            </a>
            <a href="https://colab.research.google.com/drive/1OSPzLQD6H9jlxUY8p_jUyx_T_xrj31Ph?usp=sharing"
              target="_blank" rel="noopener noreferrer"
              className="px-4 py-2 text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-all">
              Training Notebook ↗
            </a>
          </div>
        </div>
      </div>

      {/* ── Article body ─────────────────────────────────────── */}
      <main className="max-w-[820px] mx-auto px-6 py-12">
        {loading ? (
          <div className="flex items-center justify-center py-32">
            <span className="text-gray-400 text-[15px] italic">Loading…</span>
          </div>
        ) : (
          <article>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => (
                  <h1 className="text-[24px] font-bold text-gray-900 mb-3 mt-14 first:mt-0 leading-[1.3]">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-[20px] font-bold text-gray-900 mb-3 mt-12 relative pl-4">
                    <span className="absolute left-0 top-[3px] bottom-[3px] w-[3px] bg-indigo-600 rounded-full" />
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-[16px] font-bold text-gray-800 mb-2 mt-8">
                    {children}
                  </h3>
                ),
                p: ({ children }) => (
                  <p className="text-[15.5px] text-gray-600 leading-[1.85] mb-4">
                    {children}
                  </p>
                ),
                em: ({ children }) => (
                  <em className="italic text-gray-500">{children}</em>
                ),
                strong: ({ children }) => (
                  <strong className="font-bold text-gray-900">{children}</strong>
                ),
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer"
                    className="text-indigo-700 underline decoration-indigo-200 underline-offset-[3px] hover:decoration-indigo-500 transition-colors">
                    {children}
                  </a>
                ),
                code: ({ children, className }) => {
                  const isBlock = className?.includes("language-");
                  if (isBlock) {
                    return (
                      <code className="block bg-slate-50 rounded-lg px-5 py-4 text-[12.5px] text-gray-700 overflow-x-auto whitespace-pre leading-[1.7] border border-slate-100"
                        style={{ fontFamily: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace" }}>
                        {children}
                      </code>
                    );
                  }
                  return (
                    <code className="bg-slate-100 text-indigo-800 rounded px-1 py-0.5 text-[13px]"
                      style={{ fontFamily: "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace" }}>
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => (
                  <pre className="mb-5 overflow-x-auto">{children}</pre>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="border-l-[3px] border-indigo-300 pl-5 my-5 text-[15px] text-gray-500 italic bg-indigo-50/30 py-3 pr-4 rounded-r-lg">
                    {children}
                  </blockquote>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc list-outside pl-5 mb-4 space-y-1.5 text-[15.5px] text-gray-600">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-outside pl-5 mb-4 space-y-1.5 text-[15.5px] text-gray-600">
                    {children}
                  </ol>
                ),
                li: ({ children }) => (
                  <li className="leading-[1.8]">{children}</li>
                ),
                hr: () => (
                  <hr className="border-gray-100 my-10" />
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto mb-6 rounded-lg border border-gray-200 shadow-sm">
                    <table className="w-full text-[14px]">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-slate-50 border-b border-gray-200">{children}</thead>
                ),
                th: ({ children }) => (
                  <th className="text-left text-[12px] font-bold text-gray-600 uppercase tracking-wider px-4 py-2.5">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-4 py-2.5 text-gray-700 border-b border-gray-50 text-[14px]">
                    {children}
                  </td>
                ),
                tr: ({ children }) => (
                  <tr className="hover:bg-slate-50/60 transition-colors">{children}</tr>
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </article>
        )}

        {/* ── Bottom CTA ──────────────────────────────────────── */}
        {!loading && content && (
          <div className="mt-16 pt-8 border-t border-gray-200">
            <div className="bg-slate-50 rounded-xl p-8 text-center border border-gray-100">
              <h3 className="text-[18px] font-bold text-gray-900 mb-2">
                See it in action
              </h3>
              <p className="text-[14px] text-gray-500 mb-5 max-w-md mx-auto">
                Watch the trained 8B model handle support tickets autonomously, or play as the customer yourself.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Link href="/demo"
                  className="px-6 py-2.5 bg-indigo-700 text-white text-[14px] font-bold rounded-lg hover:bg-indigo-800 transition-colors">
                  Try the Demo →
                </Link>
                <Link href="/dashboard"
                  className="px-6 py-2.5 text-gray-700 text-[14px] border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  View Dashboard →
                </Link>
              </div>
            </div>
            <p className="text-center text-[12px] text-gray-400 mt-6 pb-4 italic">
              Built by Team X-Force · Meta × PyTorch × Scaler OpenEnv Hackathon, April 2026
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
