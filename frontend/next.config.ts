import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: 'export',
  // Capacitor serves static routes from directories inside the APK. The
  // trailing slash makes /habits/ resolve to habits/index.html instead of
  // falling back to the landing page in the embedded WebView server.
  trailingSlash: true,
  transpilePackages: [],
};

export default nextConfig;
