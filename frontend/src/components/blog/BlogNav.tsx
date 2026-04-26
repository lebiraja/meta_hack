"use client";
import { useEffect, useState } from "react";
import { motion, useScroll, useSpring } from "framer-motion";
import Link from "next/link";
import { cn } from "@/lib/utils";

const NAV_SECTIONS = [
  { id: "hero", label: "Overview" },
  { id: "pain", label: "The Problem" },
  { id: "architecture", label: "Architecture" },
  { id: "challenges", label: "Challenges" },
  { id: "pipeline", label: "Training" },
  { id: "results", label: "Results" },
  { id: "article", label: "Deep Dive" },
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
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled
          ? "bg-slate-950/80 backdrop-blur-xl border-b border-white/8 shadow-xl shadow-black/20"
          : "bg-transparent"
      )}
    >
      {/* Progress bar */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 h-[2px] origin-left bg-gradient-to-r from-indigo-500 via-violet-500 to-cyan-400"
        style={{ scaleX }}
      />
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link
          href="/blog"
          className="text-sm font-semibold tracking-tight text-white hover:text-indigo-300 transition-colors"
        >
          AgentOS
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV_SECTIONS.map(({ id, label }) => (
            <a
              key={id}
              href={`#${id}`}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-200",
                active === id
                  ? "bg-indigo-500/20 text-indigo-300"
                  : "text-slate-400 hover:text-slate-100"
              )}
            >
              {label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/demo"
            className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white transition-all hover:bg-indigo-500 hover:shadow-lg hover:shadow-indigo-500/30"
          >
            Try Demo
          </Link>
          <a
            href="https://github.com/lebiraja/meta_hack"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-white/10 px-4 py-1.5 text-xs font-semibold text-slate-300 transition-all hover:border-white/20 hover:text-white"
          >
            GitHub
          </a>
        </div>
      </div>
    </header>
  );
}
