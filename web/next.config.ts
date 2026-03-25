import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/travel",
  output: "standalone",
  reactStrictMode: true,
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
};

export default nextConfig;
