import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["illus/*.svg"],
      manifest: {
        name: "Stride · Project Champion",
        short_name: "Stride",
        description: "Cited motor-skill insight and meet selection for Project Champion",
        theme_color: "#F4F4F1",
        background_color: "#F4F4F1",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,png,svg}"],
        // The on-device model runtime (~6 MB) loads only when the user turns Ask on.
        globIgnores: ["**/llm.worker-*.js", "**/lib-*.js"],
        maximumFileSizeToCacheInBytes: 2.5 * 1024 * 1024,
        navigateFallbackDenylist: [/^\/api/],
        runtimeCaching: [
          { urlPattern: /\/api\/(meta|overview|schools|events|children)/, handler: "NetworkFirst",
            options: { cacheName: "api", networkTimeoutSeconds: 4 } },
        ],
      },
    }),
  ],
  server: { port: 5173, host: true, proxy: { "/api": "http://127.0.0.1:8000" } },
  worker: { format: "es" },
});
