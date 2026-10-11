import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const packages = (name: string) => path.resolve(__dirname, `../../packages/${name}/src`);

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    // Micro-frontend servi sous /admin (dev comme prod)
    base: "/admin/",
    plugins: [
      react(),
      tailwindcss(),
      {
        // Confort dev : http://localhost:5174/ → /admin/
        name: "redirect-root-to-admin",
        configureServer(server) {
          server.middlewares.use((req, res, next) => {
            if (req.url === "/" || req.url === "") {
              res.statusCode = 302;
              res.setHeader("Location", "/admin/");
              res.end();
              return;
            }
            next();
          });
        },
      },
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
        "@voyara/ui": packages("ui"),
        "@voyara/api": packages("api"),
        "@voyara/auth": packages("auth"),
        "@voyara/i18n": packages("i18n"),
      },
    },
    server: {
      port: 5174,
      proxy: {
        "/api": {
          target: env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ""),
        },
        "/static": {
          target: env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
