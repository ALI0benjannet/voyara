import type { NextConfig } from "next";

// Gateway des microservices (côté serveur Next : SSR + proxy dev)
const GATEWAY = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Image Docker autonome (node server.js)
  output: "standalone",
  // Même convention que l'ancien proxy Vite : le préfixe /api est retiré
  // (axios appelle /api/api/v1/... → le gateway reçoit /api/v1/...)
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${GATEWAY}/:path*` },
      { source: "/static/:path*", destination: `${GATEWAY}/static/:path*` },
    ];
  },
};

export default nextConfig;
