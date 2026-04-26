"use client";
import { motion } from "framer-motion";
import { Copy, Check } from "lucide-react";
import { useState } from "react";
import { fadeUp, slideInLeft, viewportOnce } from "@/lib/motion";
import type { Components } from "react-markdown";
import React from "react";

function AnimatedH2({ children }: { children?: React.ReactNode }) {
  return (
    <motion.h2
      variants={slideInLeft}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="mt-14 mb-4 flex items-center gap-3 text-2xl font-bold text-slate-900"
      style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
    >
      <span className="h-5 w-1 shrink-0 rounded-full bg-gradient-to-b from-indigo-500 to-violet-500" />
      {children}
    </motion.h2>
  );
}

function AnimatedH3({ children }: { children?: React.ReactNode }) {
  return (
    <motion.h3
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="mt-8 mb-2 text-lg font-semibold text-indigo-600"
    >
      {children}
    </motion.h3>
  );
}

function AnimatedP({ children }: { children?: React.ReactNode }) {
  return (
    <motion.p
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="mb-4 text-base leading-relaxed text-slate-600"
    >
      {children}
    </motion.p>
  );
}

function CodeBlock({ children }: { children?: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const code = String(children ?? "").replace(/\n$/, "");
  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="my-5 overflow-hidden rounded-xl border border-slate-200 bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-700 px-4 py-2">
        <div className="flex gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-rose-400/80" />
          <div className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
          <div className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
        </div>
        <button onClick={handleCopy} className="flex items-center gap-1.5 rounded px-2 py-1 text-xs text-slate-400 hover:text-slate-200 transition-colors">
          {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 text-sm leading-relaxed">
        <code className="font-mono text-slate-300">{code}</code>
      </pre>
    </div>
  );
}

function AnimatedBlockquote({ children }: { children?: React.ReactNode }) {
  return (
    <blockquote className="my-5 rounded-xl border border-indigo-200 bg-indigo-50 px-5 py-4">
      <div className="text-sm italic leading-relaxed text-indigo-800">{children}</div>
    </blockquote>
  );
}

/* ── Table: force horizontal scroll so no column clips ── */
function AnimatedTable({ children }: { children?: React.ReactNode }) {
  return (
    <div className="my-6 w-full overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
      <table className="min-w-full text-sm">{children}</table>
    </div>
  );
}

export const mdxComponents: Components = {
  h1: ({ children }) => (
    <h1 className="mt-0 mb-5 text-3xl font-bold text-slate-900" style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}>
      {children}
    </h1>
  ),
  h2: ({ children }) => <AnimatedH2>{children}</AnimatedH2>,
  h3: ({ children }) => <AnimatedH3>{children}</AnimatedH3>,
  h4: ({ children }) => (
    <h4 className="mt-5 mb-1.5 text-sm font-bold uppercase tracking-wide text-slate-700">{children}</h4>
  ),
  p: ({ children }) => <AnimatedP>{children}</AnimatedP>,
  a: ({ href, children }) => (
    <a href={href} className="text-indigo-600 underline underline-offset-2 hover:text-indigo-800 transition-colors"
      target={href?.startsWith("http") ? "_blank" : undefined}
      rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}>
      {children}
    </a>
  ),
  code: ({ children, ...props }) => {
    const isBlock = !props.hasOwnProperty("inline") && String(children).includes("\n");
    if (isBlock) return <CodeBlock>{children}</CodeBlock>;
    return (
      <code className="rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-indigo-700">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <>{children}</>,
  blockquote: ({ children }) => <AnimatedBlockquote>{children}</AnimatedBlockquote>,
  ul: ({ children }) => <ul className="my-3 ml-4 space-y-1.5 text-slate-600">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 ml-4 list-decimal space-y-1.5 text-slate-600">{children}</ol>,
  li: ({ children }) => (
    <li className="flex gap-2 text-sm leading-relaxed">
      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
      <span>{children}</span>
    </li>
  ),
  table: ({ children }) => <AnimatedTable>{children}</AnimatedTable>,
  thead: ({ children }) => (
    <thead className="bg-slate-50 border-b border-slate-200">
      <tr>{children}</tr>
    </thead>
  ),
  th: ({ children }) => (
    <th className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-slate-100 px-4 py-3 text-sm text-slate-700">
      {children}
    </td>
  ),
  tr: ({ children }) => <tr className="transition-colors hover:bg-slate-50">{children}</tr>,
  hr: () => (
    <div className="my-10 h-px w-full bg-gradient-to-r from-transparent via-slate-300 to-transparent" />
  ),
  strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
  em: ({ children }) => <em className="italic text-slate-700">{children}</em>,
  img: ({ src, alt }) => (
    <span className="my-6 block overflow-hidden rounded-xl border border-slate-200 shadow-sm">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt ?? ""} className="w-full object-contain" />
    </span>
  ),
};
