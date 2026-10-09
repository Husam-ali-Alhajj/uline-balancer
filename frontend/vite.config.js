import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // allow importing the example JSON from ../contracts (used by the mock API)
    fs: { allow: [".."] },
  },
});
