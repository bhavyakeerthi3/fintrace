import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: { root: process.cwd() },
  async headers() {
    return [
      {
        source: "/",
        headers: [{ key: "Content-Type", value: "text/html; charset=utf-8" }],
      },
    ];
  },
};

export default nextConfig;
