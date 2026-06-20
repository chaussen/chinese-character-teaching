import { resolve } from "path";
import { defineConfig } from "vite";

// Relative base so the built app works from any subpath (GitHub Pages project
// site, a nested folder, or opened from a static file server).
export default defineConfig({
  root: "web",
  base: "./",
  publicDir: "public",
  build: {
    outDir: "../dist-web",
    emptyOutDir: true,
    rollupOptions: {
      // index.html is the public WIP block; app.html is the real app, only
      // reachable if you know the URL — both need to ship for that to work.
      input: {
        index: resolve(__dirname, "web/index.html"),
        app: resolve(__dirname, "web/app.html"),
      },
    },
  },
});
