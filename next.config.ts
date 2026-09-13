import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep Turbopack inside this checkout. A lockfile higher in the user's
  // home directory must not expand the watcher root for local development.
  turbopack: {
    root: process.cwd(),
  },
  webpack(config, { dev }) {
    if (dev) {
      config.watchOptions = {
        ...config.watchOptions,
        // macOS GUI processes commonly inherit a 256-descriptor watch limit.
        // Polling keeps local Fast Refresh reliable without requiring a
        // machine-wide launchctl change.
        poll: 1000,
        ignored:
          /(^|[\\/])(\.git|\.next|\.venv|node_modules|parallax_backend|packages|migrations|tests|docs|outputs|infra|scripts|Initial Documentations)([\\/]|$)/,
      };
    }
    return config;
  },
};

export default nextConfig;
