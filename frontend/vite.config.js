import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// amazon-cognito-identity-js expects Node's `global`.
export default defineConfig({ plugins: [react()], define: { global: "globalThis" } });
