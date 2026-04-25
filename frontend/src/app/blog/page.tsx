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
        setContent(text);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      {/* Top nav */}
      <header className="sticky top-0 z-10 border-b border-neutral-800 bg-neutral-950/90 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between">
          <span className="text-sm font-semibold text-neutral-100">
            Agent<span className="text-indigo-400">OS</span>
          </span>
          <nav className="flex items-center gap-1">
            <Link
              href="/blog"
              className="px-3 py-1.5 rounded-md text-xs font-medium bg-indigo-600 text-white"
            >
              Paper
            </Link>
            <Link
              href="/demo"
              className="px-3 py-1.5 rounded-md text-xs font-medium text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800 transition-colors"
            >
              Live Demo
            </Link>
            <Link
              href="/dashboard"
              className="px-3 py-1.5 rounded-md text-xs font-medium text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800 transition-colors"
            >
              Dashboard
            </Link>
          </nav>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-6 py-12">
        {loading ? (
          <div className="flex items-center justify-center py-32">
            <span className="text-neutral-600 animate-pulse text-sm">Loading…</span>
          </div>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => (
                <h1 className="text-2xl font-bold text-neutral-100 mb-2 mt-10 first:mt-0 leading-tight">
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-xl font-semibold text-neutral-100 mb-3 mt-10 pb-2 border-b border-neutral-800">
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-base font-semibold text-indigo-300 mb-2 mt-6">
                  {children}
                </h3>
              ),
              p: ({ children }) => (
                <p className="text-neutral-300 leading-relaxed mb-4 text-sm">
                  {children}
                </p>
              ),
              em: ({ children }) => (
                <em className="text-neutral-400 not-italic">{children}</em>
              ),
              strong: ({ children }) => (
                <strong className="text-neutral-100 font-semibold">{children}</strong>
              ),
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors"
                >
                  {children}
                </a>
              ),
              code: ({ children, className }) => {
                const isBlock = className?.includes("language-");
                if (isBlock) {
                  return (
                    <code className="block bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-3 text-xs font-mono text-neutral-300 overflow-x-auto whitespace-pre leading-relaxed">
                      {children}
                    </code>
                  );
                }
                return (
                  <code className="bg-neutral-800 text-indigo-300 rounded px-1.5 py-0.5 text-xs font-mono">
                    {children}
                  </code>
                );
              },
              pre: ({ children }) => (
                <pre className="mb-4 overflow-x-auto">{children}</pre>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-indigo-500 pl-4 my-4 text-neutral-400 italic">
                  {children}
                </blockquote>
              ),
              ul: ({ children }) => (
                <ul className="list-disc list-outside pl-5 mb-4 space-y-1 text-sm text-neutral-300">
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-outside pl-5 mb-4 space-y-1 text-sm text-neutral-300">
                  {children}
                </ol>
              ),
              li: ({ children }) => (
                <li className="leading-relaxed">{children}</li>
              ),
              hr: () => (
                <hr className="border-neutral-800 my-8" />
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto mb-6">
                  <table className="w-full text-sm border-collapse">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead className="border-b border-neutral-700">{children}</thead>
              ),
              th: ({ children }) => (
                <th className="text-left text-xs font-semibold text-neutral-400 uppercase tracking-wider px-3 py-2">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="px-3 py-2 text-neutral-300 border-b border-neutral-800/60 text-sm">
                  {children}
                </td>
              ),
              tr: ({ children }) => (
                <tr className="hover:bg-neutral-900/50 transition-colors">{children}</tr>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}

        {/* CTA at bottom */}
        {!loading && content && (
          <div className="mt-16 pt-8 border-t border-neutral-800 flex flex-col sm:flex-row gap-3">
            <Link
              href="/demo"
              className="flex-1 text-center px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-colors"
            >
              Try the Live Demo →
            </Link>
            <Link
              href="/dashboard"
              className="flex-1 text-center px-6 py-3 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-sm font-medium rounded-xl transition-colors"
            >
              View Dashboard →
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
