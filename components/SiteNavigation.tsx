"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { base } from "@/lib/data";
const links = [
  ["/", "产量地图"],
  ["/elnino/", "厄尔尼诺"],
  ["/events/", "历史复盘"],
  ["/methodology/", "数据说明"],
];
export default function SiteNavigation() {
  const path = usePathname();
  const normalized = path.replace(/\/$/, "");
  return (
    <header className="site-header">
      <div className="header-inner">
        <Link className="brand" href="/" aria-label="Brian的厄尔尼诺看盘 首页">
          <span className="brand-mark">
            <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <path
                d="M16 27V12M16 22C8 22 5 17 5 12c7 0 11 4 11 10ZM16 16c7 0 11-5 11-10-7 0-11 4-11 10Z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </span>
          <span>
            Brian的厄尔尼诺看盘<small>El Niño Crop Monitor</small>
          </span>
        </Link>
        <nav aria-label="主导航">
          {links.map(([href, label]) => {
            const active =
              href === "/"
                ? !["/elnino", "/events", "/methodology", "/about"].includes(
                    normalized,
                  )
                : normalized === href.replace(/\/$/, "");
            return (
              <Link href={href} key={href} className={active ? "active" : ""}>
                {label}
              </Link>
            );
          })}
        </nav>
        <Link href="/about/" className="about-link">
          <img
            className="author-avatar"
            src={`${base}/images/brian-avatar.webp`}
            alt="Brian头像"
          />
          <span>Brian的宏观研究笔记</span>
          <span>↗</span>
        </Link>
      </div>
    </header>
  );
}
