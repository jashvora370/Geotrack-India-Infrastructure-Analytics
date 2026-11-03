/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['leaflet'],
  images: {
    domains: ['tile.openstreetmap.org', 'cartodb-basemaps-a.global.ssl.fastly.net'],
  },
  webpack: (config, { dev }) => {
    // Fixes npm packages that depend on `fs` module
    config.resolve.fallback = { fs: false, net: false, tls: false };
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
