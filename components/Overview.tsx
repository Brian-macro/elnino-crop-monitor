"use client";
import Link from "next/link";
import {
  useData,
  Overview as OverviewData,
  day,
  num,
  names,
  sources,
  CROPS,
} from "@/lib/data";
import { Loading, SourceState, Provenance } from "./Common";
import Outlook from "./Outlook";
export default function Overview() {
  const { data, error } = useData<OverviewData>("overview");
  if (!data) return <Loading error={error} />;
  const c = data.climate["Nino3.4"];
  const stale = data.sources.filter((s) => s.status === "stale");
  return (
    <main>
      <div className="page-heading">
        <div>
          <div className="eyebrow">RESEARCH TERMINAL / OVERVIEW</div>
          <h1>El Niño Crop Monitor</h1>
          <p>Global Crop Production, Climate Risk & Commodity Pricing</p>
        </div>
        <div className="update-clock">
          DATA SNAPSHOT<strong>{day(data.updated)}</strong>
          <span>
            {stale.length} sources stale · {data.sources.length} tracked
          </span>
        </div>
      </div>
      <div className="climate-strip">
        <div>
          <span>NIÑO 3.4 · {day(c?.date)}</span>
          <strong>
            {num(c?.value)}
            <small> °C</small>
          </strong>
        </div>
        <div>
          <span>历史分位</span>
          <strong>
            {num(c?.percentile, 1)}
            <small> %</small>
          </strong>
        </div>
        <div>
          <span>当前异常强度范围</span>
          <strong className="climate-state">{c?.strength || "N/A"}</strong>
        </div>
        <div>
          <span>连续暖月 · ≥0.5°C</span>
          <strong>{c?.warm_seasons ?? "N/A"}</strong>
        </div>
        <Link href="/elnino/">Climate Monitor ↗</Link>
      </div>
      <div className="headline-crops">
        {CROPS.map((crop) => {
          const row = data.crops[crop];
          return (
            <div key={crop} className="crop-summary">
              <Link href={`/${crop}/`}>
                {names[crop]} <span>↗</span>
              </Link>
              <strong>
                {num(row?.value, 1)}
                <small> Mt</small>
              </strong>
              <span className="muted">
                {row
                  ? `${row.target_year} forecast · ${sources[row.source]}`
                  : "Forecast N/A"}
              </span>
              <SourceState
                source={data.sources.find((s) => s.source === row?.source)}
              />
              <Provenance row={row || undefined} />
            </div>
          );
        })}
      </div>
      {stale.length > 0 && (
        <div className="notice">
          Data Stale · {stale.map((s) => s.name).join(" / ")}
          <Link href="/methodology/">来源状态与覆盖 ↗</Link>
        </div>
      )}
      <Outlook compact />
      <section className="research-links">
        <Link href="/events/">
          <span>01 / HISTORICAL ANALOGUES</span>
          <h3>历史 El Niño 事件复盘 ↗</h3>
        </Link>
        <Link href="/methodology/">
          <span>02 / EVIDENCE & DEFINITIONS</span>
          <h3>原始出处、数据口径与覆盖 ↗</h3>
        </Link>
      </section>
    </main>
  );
}
