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
  },
});
