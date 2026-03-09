import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Empty = same-origin; frontend and backend served together, no hardcoded host.
  const apiBaseUrl = env.BASE_URL ?? "";

  return {
    define: {
      BASE_URL: JSON.stringify(apiBaseUrl),
      TOKEN: JSON.stringify(env.TOKEN || ""),
      MOBILE: false,
    },
    plugins: [react()],
    css: {
      modules: {
        localsConvention: "camelCase",
        generateScopedName: "[name]__[local]__[hash:base64:5]",
      },
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
        },
      },
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
        scheduler: path.resolve(__dirname, "node_modules/react-dom/node_modules/scheduler"),
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      allowedHosts: ["test2"],
      // 添加代理配置，解决前后端分别启动时的CORS问题
      proxy: {
        '/api': {
          target: 'http://localhost:8088',
          changeOrigin: true,
          secure: false,
        },
        '/agent': {
          target: 'http://localhost:8088',
          changeOrigin: true,
          secure: false,
        },
        '/docs': {
          target: 'http://localhost:8088',
          changeOrigin: true,
          secure: false,
        },
        '/openapi.json': {
          target: 'http://localhost:8088',
          changeOrigin: true,
          secure: false,
        }
      }
    },
    optimizeDeps: {
      include: ["diff", "scheduler"],
    },
    build: {
      rollupOptions: {
        external: ["scheduler"],
      },
      // Output to CoPaw's console directory,
      // so we don't need to copy files manually after build.
      // outDir: path.resolve(__dirname, "../src/copaw/console"),
      // emptyOutDir: true,
    },
  };
});
