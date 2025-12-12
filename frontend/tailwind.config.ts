import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: {
          DEFAULT: "#22c55e",
          foreground: "#ffffff",
        },
        secondary: {
          DEFAULT: "#1e293b",
          foreground: "#f8fafc",
        },
        muted: {
          DEFAULT: "#334155",
          foreground: "#94a3b8",
        },
        accent: {
          DEFAULT: "#3b82f6",
          foreground: "#ffffff",
        },
        destructive: {
          DEFAULT: "#ef4444",
          foreground: "#ffffff",
        },
      },
      animation: {
        pulse: "pulse 1.5s ease-in-out infinite",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
