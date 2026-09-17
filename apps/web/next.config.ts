import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output så frontenden også kan køre som container (portabilitetskrav).
  output: "standalone",
};

export default nextConfig;
