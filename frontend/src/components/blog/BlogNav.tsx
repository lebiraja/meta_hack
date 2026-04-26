"use client";
import { useEffect, useState } from "react";
import { motion, useScroll, useSpring } from "framer-motion";
import Link from "next/link";
import { cn } from "@/lib/utils";

const NAV_SECTIONS = [
  { id: "hero",         label: "Overview" },
  { id: "architecture", label: "Architecture" },
  { id: "results",      label: "Results" },
  { id: "training-plots", label: "Training" },
  { id: "article",      label: "Deep Dive" },
];

export function BlogNav() {
  const [active, setActive] = useState("hero");
  const [scrolled, setScrolled] = useState(false);
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 200, damping: 30 });

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => { if (e.isIntersecting) setActive(e.target.id); });
      },
      { rootMargin: "-40% 0px -55% 0px" }
    );
    NAV_SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <header className={cn(
      "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
      scrolled ? "bg-white/95 backdrop-blur-xl border-b border-slate-200 shadow-sm" : "bg-transparent"
    )}>
      <motion.div
        className="absolute bottom-0 left-0 right-0 h-[2px] origin-left bg-gradient-to-r from-indigo-500 via-violet-500 to-cyan-500"
        style={{ scaleX }}
      />
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
        <Link href="/blog" className="text-sm font-bold tracking-tight text-slate-900 hover:text-indigo-600 transition-colors">
          AgentOS
        </Link>
        <nav className="hidden items-center gap-0.5 md:flex">
          {NAV_SECTIONS.map(({ id, label }) => (
            <a key={id} href={`#${id}`} className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
              active === id ? "bg-indigo-50 text-indigo-600" : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
            )}>
              {label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link href="/demo" className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 transition-colors">
            Try Demo
          </Link>
          <a href="https://github.com/lebiraja/meta_hack" target="_blank" rel="noopener noreferrer"
            className="rounded-lg border border-slate-200 px-4 py-1.5 text-xs font-semibold text-slate-600 hover:border-slate-300 hover:bg-slate-50 transition-all">
            GitHub
          </a>
        </div>
      </div>
    </header>
  );
}
