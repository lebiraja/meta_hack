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
      className="mt-14 mb-5 flex items-center gap-3 text-2xl font-bold text-slate-900"
      style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
    >
      <span className="h-6 w-1 shrink-0 rounded-full bg-gradient-to-b from-indigo-500 to-violet-500" />
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
      className="mt-10 mb-3 text-lg font-semibold text-indigo-600"
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
      className="mb-5 text-base leading-[1.9] text-slate-600"
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
    <motion.div
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="group relative my-6 overflow-hidden rounded-xl border border-slate-200 bg-slate-900"
    >
      <div className="flex items-center justify-between border-b border-slate-700 px-4 py-2">
        <div className="flex gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-rose-400/80" />
          <div className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
          <div className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-slate-400 transition-all hover:bg-white/5 hover:text-slate-200"
        >
          {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 text-sm leading-relaxed">
        <code className="font-mono text-slate-300">{code}</code>
      </pre>
    </motion.div>
  );
}

function AnimatedBlockquote({ children }: { children?: React.ReactNode }) {
  return (
    <motion.blockquote
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="my-6 overflow-hidden rounded-xl border border-indigo-200 bg-indigo-50 px-6 py-4"
    >
      <div className="text-sm italic leading-relaxed text-indigo-800">{children}</div>
    </motion.blockquote>
  );
}

function AnimatedTable({ children }: { children?: React.ReactNode }) {
  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="my-6 overflow-hidden rounded-xl border border-slate-200 shadow-sm"
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-full text-sm">{children}</table>
      </div>
    </motion.div>
  );
}

export const mdxComponents: Components = {
  h1: ({ children }) => (
    <motion.h1
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="mt-0 mb-6 text-3xl font-bold text-slate-900"
      style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
    >
      {children}
    </motion.h1>
  ),
  h2: ({ children }) => <AnimatedH2>{children}</AnimatedH2>,
  h3: ({ children }) => <AnimatedH3>{children}</AnimatedH3>,
  h4: ({ children }) => (
    <h4 className="mt-6 mb-2 text-base font-semibold text-slate-800">{children}</h4>
  ),
  p: ({ children }) => <AnimatedP>{children}</AnimatedP>,
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-indigo-600 underline underline-offset-2 transition-colors hover:text-indigo-800"
      target={href?.startsWith("http") ? "_blank" : undefined}
      rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}
    >
      {children}
    </a>
  ),
  code: ({ className, children, ...props }) => {
    const isBlock = !props.hasOwnProperty("inline") && String(children).includes("\n");
    if (isBlock) {
      return <CodeBlock>{children}</CodeBlock>;
    }
    return (
      <code className="rounded-md border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-sm text-indigo-700">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <>{children}</>,
  blockquote: ({ children }) => <AnimatedBlockquote>{children}</AnimatedBlockquote>,
  ul: ({ children }) => (
    <ul className="my-4 ml-4 space-y-2 text-slate-600">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-4 ml-4 list-decimal space-y-2 text-slate-600">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="flex gap-2 text-sm leading-relaxed">
      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500" />
      <span>{children}</span>
    </li>
  ),
  table: ({ children }) => <AnimatedTable>{children}</AnimatedTable>,
  thead: ({ children }) => (
    <thead className="border-b border-slate-200 bg-slate-50">
      <tr>{children}</tr>
    </thead>
  ),
  th: ({ children }) => (
    <th className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-slate-500">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-slate-100 px-4 py-3 text-sm text-slate-700">
      {children}
    </td>
  ),
  tr: ({ children }) => (
    <tr className="transition-colors hover:bg-slate-50">{children}</tr>
  ),
  hr: () => (
    <div className="my-10 h-px w-full bg-gradient-to-r from-transparent via-slate-300 to-transparent" />
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-slate-700">{children}</em>
  ),
};
