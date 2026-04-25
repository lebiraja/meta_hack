import type { NextConfig } from "next";

// When NEXT_STATIC_EXPORT=true, build a static site into /out
// so FastAPI can serve it directly on port 7860 (HF Spaces).
const isStaticExport = process.env.NEXT_STATIC_EXPORT === "true";

const nextConfig: NextConfig = {
  output: isStaticExport ? "export" : "standalone",
  distDir: isStaticExport ? "out" : ".next",
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
