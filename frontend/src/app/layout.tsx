import type { Metadata } from "next";
import { Geist, Geist_Mono, Fraunces } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  axes: ["opsz", "SOFT", "WONK"],
});

export const metadata: Metadata = {
  title: "AgentOS — Multi-Agent RL for Customer Support",
  description:
    "How we trained a hierarchical multi-agent RL system that handles real customer support tickets end-to-end, surpassing GPT-4 baselines by 15–19 percentage points.",
  openGraph: {
    title: "AgentOS — Multi-Agent RL for Customer Support",
    description: "Training an AI that actually handles customer support end-to-end.",
    type: "article",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full scroll-smooth">
      <body
        className={`h-full bg-white text-slate-900 antialiased ${geistSans.variable} ${geistMono.variable} ${fraunces.variable}`}
        style={{ fontFamily: "var(--font-geist-sans), system-ui, sans-serif" }}
      >
        {children}
      </body>
    </html>
  );
}
