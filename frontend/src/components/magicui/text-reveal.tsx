"use client";
import { motion } from "framer-motion";
import { useInView } from "react-intersection-observer";
import { cn } from "@/lib/utils";

export function TextReveal({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  const words = text.split(" ");
  const { ref, inView } = useInView({ triggerOnce: true, threshold: 0.3 });

  return (
    <p ref={ref} className={cn("flex flex-wrap gap-x-2", className)}>
      {words.map((word, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: i * 0.05, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        >
          {word}
        </motion.span>
      ))}
    </p>
  );
}
