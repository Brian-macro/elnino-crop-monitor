import type { Metadata } from "next";
import Navigation from "@/components/SiteNavigation";
import { Wechat } from "@/components/Common";
import Link from "next/link";
import "./globals.css";
import localFont from "next/font/local";
const uiFont = localFont({
  src: "../public/fonts/noto-sans-sc-ui.woff2",
  weight: "100 900",
  display: "swap",
  variable: "--font-ui",
});
export const metadata: Metadata = {
  title: "Brian的厄尔尼诺看盘",
  description: "Global Crop Production, Climate Risk & Commodity Pricing",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={uiFont.variable}>
      <body>
        <Navigation />
        <div className="wrap">
          {children}
          <footer>
            <span>
              Brian的厄尔尼诺看盘 <span className="footer-separator">/</span>{" "}
              气候 · 供给 · 价格
            </span>
            <div>
              <Link href="/methodology/">数据说明</Link>
              <Link href="/about/">Brian的宏观研究笔记 ↗</Link>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
