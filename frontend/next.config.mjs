/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Native Vercel deployment: Next.js API routes under app/api/v1 handle
  // all data queries using static cached assets and direct edge execution.
};
export default nextConfig;
