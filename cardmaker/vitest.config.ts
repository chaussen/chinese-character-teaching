import { defineConfig } from "vitest/config";

// Separate from vite.config.ts (whose root is "web") so tests resolve from the
// package root.
export default defineConfig({
  test: {
    root: ".",
    include: ["test/**/*.test.ts"],
  },
});
