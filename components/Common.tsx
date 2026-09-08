"use client";
import Link from "next/link";
import { Production, day, yearLabel, sources, Source, base } from "@/lib/data";
export function Loading({ error = "" }: { error?: string }) {
  return (
    <div className="empty">
      {error || "正在读取已验证的研究数据…"}
      {error && <button onClick={() => location.reload()}>重新加载</button>}
    </div>
  );
}
export function Provenance({ row, note }: { row?: Production; note?: string }) {
  return (
    <div className="provenance">
      <span>
        来源：{" "}
        {row ? (
          <a href={row.source_url} target="_blank" rel="noreferrer">
            {sources[row.source] || row.source} ↗
          </a>
        ) : (
          "N/A"
        )}
      </span>
      <span>
        预测日期：{" "}
        {row?.status === "forecast" ? day(row.publication_date) : "N/A"}
        {row?.status === "forecast" && !row.publication_date
          ? " · 月刊/首次观察，见口径"
          : ""}
      </span>
      <span>目标年度： {row ? yearLabel(row) : "N/A"}</span>
      <span>更新： {row ? day(row.download_timestamp) : "N/A"}</span>
      {note && <span>{note}</span>}
    </div>
  );
}
export function SourceState({ source }: { source?: Source }) {
  const status = source?.status || "unavailable";
  return (
    <span title={source?.error || ""} className={`status ${status}`}>
      {status === "ok"
        ? "数据正常"
        : status === "partial"
          ? "部分覆盖"
          : status === "stale"
            ? "待更新"
            : "N/A"}
    </span>
  );
}
export function Wechat({ large = false }: { large?: boolean }) {
  const image =
    process.env.NEXT_PUBLIC_WECHAT_IMAGE || "/images/brian-wechat.jpg";
  return (
    <div className={`wechat ${large ? "large" : ""}`}>
      {image ? (
        <img
          src={
            image.startsWith("http")
              ? image
              : `${base}/${image.replace(/^\//, "")}`
          }
          alt="Brian的宏观研究笔记公众号图片"
        />
      ) : (
        <div className="wechat-placeholder">
          <span>公众号图片</span>
          <small>待提供原图</small>
        </div>
      )}
      <div>
        <strong>Brian的宏观研究笔记</strong>
        <p>宏观研究 · 气候与大宗商品</p>
        {!large && <Link href="/about/">关于 ↗</Link>}
      </div>
    </div>
  );
}
