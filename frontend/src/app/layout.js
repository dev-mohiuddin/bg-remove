import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata = {
  title: "BG Remover — AI Background Removal in Seconds",
  description:
    "Remove image backgrounds instantly with AI. Pixel-perfect cutouts preserving fine details like hair and transparent fabrics. Free, fast, and commercial-grade quality.",
  keywords: [
    "background remover",
    "remove background",
    "AI background removal",
    "transparent background",
    "image editing",
  ],
  openGraph: {
    title: "BG Remover — AI Background Removal in Seconds",
    description:
      "Remove image backgrounds instantly with AI. Pixel-perfect cutouts preserving fine details.",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "BG Remover — AI Background Removal",
    description:
      "Remove image backgrounds instantly with AI. Pixel-perfect cutouts preserving fine details.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${inter.variable} h-full`}>
      <body className="grain-overlay min-h-full flex flex-col font-[var(--font-inter)]">
        {children}
      </body>
    </html>
  );
}
