/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // Enable WebSocket proxying in development
  async rewrites() {
    return [
      {
        source: '/ws/:path*',
        destination: 'http://backend:8000/ws/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
