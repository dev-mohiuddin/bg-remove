
const nextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.modal.run",
      },
    ],
  },
};

export default nextConfig;
