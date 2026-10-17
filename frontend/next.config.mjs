/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const base = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:4000";
    return [
      { source: "/api/v1/:path*", destination: `${base}/api/v1/:path*` },
    ];
  },
};
export default nextConfig;
