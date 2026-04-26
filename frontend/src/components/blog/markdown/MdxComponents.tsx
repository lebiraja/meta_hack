"use client";
import { motion } from "framer-motion";
import { Copy, Check } from "lucide-react";
import { useState } from "react";
import { fadeUp, slideInLeft, viewportOnce } from "@/lib/motion";
import type { Components } from "react-markdown";

function AnimatedH2({ children }: { children?: React.ReactNode }) {
  return (
    <motion.h2
      variants={slideInLeft}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="mt-14 mb-5 flex items-center gap-3 text-2xl font-bold text-white"
      style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
    >
      <span className="h-6 w-1 shrink-0 rounded-full bg-gradient-to-b from-indigo-400 to-violet-500" />
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
      className="mt-10 mb-3 text-lg font-semibold text-indigo-300"
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
      className="mb-5 text-base leading-[1.9] text-slate-400"
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
      className="group relative my-6 overflow-hidden rounded-xl border border-white/8 bg-[#0a0f1e]"
    >
      <div className="flex items-center justify-between border-b border-white/8 px-4 py-2">
        <div className="flex gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-rose-500/60" />
          <div className="h-2.5 w-2.5 rounded-full bg-amber-500/60" />
          <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/60" />
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-slate-500 transition-all hover:bg-white/5 hover:text-slate-300"
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
      className="my-6 overflow-hidden rounded-xl border border-indigo-500/20 bg-indigo-500/5 px-6 py-4"
    >
      <div className="text-sm italic leading-relaxed text-slate-300">{children}</div>
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
      className="my-6 overflow-hidden rounded-xl border border-white/8"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">{children}</table>
      </div>
    </motion.div>
  );
}

import React from "react";

export const mdxComponents: Components = {
  h1: ({ children }) => (
    <motion.h1
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="mt-0 mb-6 text-3xl font-bold text-white"
      style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}
    >
      {children}
    </motion.h1>
  ),
  h2: ({ children }) => <AnimatedH2>{children}</AnimatedH2>,
  h3: ({ children }) => <AnimatedH3>{children}</AnimatedH3>,
  h4: ({ children }) => (
    <h4 className="mt-6 mb-2 text-base font-semibold text-slate-200">{children}</h4>
  ),
  p: ({ children }) => <AnimatedP>{children}</AnimatedP>,
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-indigo-400 underline underline-offset-2 transition-colors hover:text-indigo-300"
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
      <code className="rounded-md border border-white/10 bg-white/5 px-1.5 py-0.5 font-mono text-sm text-indigo-300">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <>{children}</>,
  blockquote: ({ children }) => <AnimatedBlockquote>{children}</AnimatedBlockquote>,
  ul: ({ children }) => (
    <ul className="my-4 ml-4 space-y-2 text-slate-400">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-4 ml-4 list-decimal space-y-2 text-slate-400">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="flex gap-2 text-sm leading-relaxed">
      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-indigo-500" />
      <span>{children}</span>
    </li>
  ),
  table: ({ children }) => <AnimatedTable>{children}</AnimatedTable>,
  thead: ({ children }) => (
    <thead className="border-b border-white/8 bg-white/5">
      <tr>{children}</tr>
    </thead>
  ),
  th: ({ children }) => (
    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-slate-400">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-white/5 px-4 py-3 text-sm text-slate-300">
      {children}
    </td>
  ),
  tr: ({ children }) => (
    <tr className="transition-colors hover:bg-white/[0.02]">{children}</tr>
  ),
  hr: () => (
    <div className="my-10 h-px w-full bg-gradient-to-r from-transparent via-white/10 to-transparent" />
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-200">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-slate-300">{children}</em>
  ),
};
