"use client";
import { useState } from "react";
import Link from "next/link";
import Chart, { chartBase } from "./Chart";
import { Loading } from "./Common";
import { Climate, useData, num, day, strengthZh } from "@/lib/data";
import type { EChartsOption } from "echarts";
const month = (s: string) => Number(s.slice(0, 4)) * 12 + Number(s.slice(5, 7));
export default function ClimateMonitor() {
  const { data, error } = useData<Climate>("elnino");
  const [idx, setIdx] = useState("Nino3.4");
  if (!data) return <Loading error={error} />;
  const current = data.current[idx];
  const points = data.series[idx] || [];
  const selected = data.events.filter((e) =>
    ["1982", "1997", "2002", "2009", "2014", "2015", "2023"].includes(
      e.start.slice(0, 4),
    ),
  );
  // Both indices share the ONI warm-run origin, independent of wall-clock year.
  const oni = data.series.ONI || [];
  let warmStart = oni.length;
  for (let i = oni.length - 1; i >= 0; i--) {
    if (oni[i].value < 0.5 ||
        (i < oni.length - 1 && month(oni[i + 1].date) - month(oni[i].date) !== 1)) break;
    warmStart = i;
  }
  const warmCount = oni.length - warmStart;
  const currentStart = oni[warmStart]?.date;
  const recentLabel = warmCount >= 5 ? "归档末端暖段" : "归档末端暖段（未满5季）";
  const cycles = selected.filter((e) => e.start !== currentStart).map((e) => ({
    name: `${e.start.slice(0, 4)}/${e.end.slice(2, 4)}`,
    start: e.start,
    recent: false,
  }));
  if (currentStart) cycles.push({ name: recentLabel, start: currentStart, recent: true });
  return (
    <main>
      <div className="page-heading">
        <div>
          <div className="eyebrow">海洋与气候 · NOAA</div>
          <h1>厄尔尼诺追踪</h1>
          <p>查看已归档海温观测、异常幅度与历史周期对比</p>
        </div>
        <a href={data.roni_url} target="_blank" rel="noreferrer">
          NOAA RONI ↗
        </a>
      </div>
      <div className="panel-note">
        气候观测独立来自 NOAA，不随农作物预测来源切换。本页为基础库归档快照，手动维护；每日自动任务只检查农作物预测，不自动刷新气候观测。历史对比不是产量或价格的因果模型。
      </div>
      <div className="toolbar">
        <div className="segmented">
          {["Nino3.4", "ONI"].map((k) => (
            <button
              className={idx === k ? "active" : ""}
              onClick={() => setIdx(k)}
              key={k}
            >
              {k}
            </button>
          ))}
        </div>
        <span className="muted">
          归档最新观测{idx === "ONI" ? "中心月" : "月份"} {current?.date?.slice(0, 7) || "暂无数据"} · {idx === "ONI" ? `${current?.season || ""} 三个月均值` : "月均值"}
        </span>
      </div>
      <div className="stat-grid">
        <div>
          <span>归档最新异常 / {strengthZh[current?.strength] || "暂无数据"}</span>
          <strong>{num(current?.value, idx === "ONI" ? 1 : 2)} °C</strong>
        </div>
        <div>
          <span>历史百分位 / {current?.sample_size || 0} 个观测值</span>
          <strong>{num(current?.percentile, 1)}%</strong>
        </div>
        <div>
          <span>{idx === "ONI" ? "连续暖季（重叠三个月）" : "连续暖月"}</span>
          <strong>{current?.warm_seasons ?? "暂无数据"}</strong>
        </div>
        <div>
          <span>较前1月 / 3月变化</span>
          <strong>
            {num(current?.chg_1m)} / {num(current?.chg_3m)}
          </strong>
          <small> °C</small>
        </div>
      </div>
      <section className="panel">
        <div className="panel-head">
          <h3>{idx} · 历史变化</h3>
          <span>{idx === "ONI" ? "三个月滑动平均 · 日期为中心月" : "月度海温异常"}</span>
        </div>
        <Chart
          height={360}
          option={
            {
              ...chartBase,
              dataZoom: [
                { type: "inside", start: 80 },
                { type: "slider", start: 80, height: 16, bottom: 12 },
              ],
              yAxis: { ...chartBase.yAxis, name: "海温异常 °C" },
              series: [
                {
                  name: idx,
                  type: "line",
                  symbol: "none",
                  lineStyle: { width: 1.8, color: "#68bdc4" },
                  data: points.map((p) => [day(p.date), p.value]),
                  markLine: {
                    symbol: "none",
                    label: { color: "#afb6ba", formatter: "{b}" },
                    data: [
                      { yAxis: 0.5, name: "+0.5°C 暖侧参考" },
                      { yAxis: -0.5, name: "−0.5°C 冷侧参考" },
                    ],
                  },
                },
              ],
            } as EChartsOption
          }
        />
        <div className="provenance">
          来源： <a href={current?.source_url}>NOAA CPC ↗</a> · 观测指数（非预测） · {idx === "ONI" ? "观测中心月" : "观测月份"}： {current?.date?.slice(0, 7)} · 本站归档：{" "}
          {day(current?.download_timestamp)}
        </div>
      </section>
      <section className="panel">
        <div className="panel-head">
          <h3>历史周期对比</h3>
          <span>T = 事后识别的首个暖季中心月</span>
        </div>
        <Chart
          height={350}
          option={
            {
              ...chartBase,
              xAxis: { type: "value", name: "距 T 月数", min: -6, max: 24 },
              yAxis: { ...chartBase.yAxis, name: "海温异常 °C" },
              series: cycles.map((e) => ({
                name: e.name,
                type: "line",
                showSymbol: false,
                lineStyle: {
                  width: e.recent ? 3 : 1.5,
                  type: e.recent ? "solid" : "dashed",
                },
                data: points
                  .filter(
                    (p) =>
                      month(p.date) - month(e.start) >= -6 &&
                      month(p.date) - month(e.start) <= 24,
                  )
                  .map((p) => [month(p.date) - month(e.start), p.value]),
              })),
            } as EChartsOption
          }
        />
        <div className="panel-note">
          {currentStart
            ? `归档末端暖段以 ${currentStart.slice(0, 7)} 为 T，已连续 ${warmCount} 个 ONI 暖季${warmCount < 5 ? "，未满历史事件所需的5季" : ""}。`
            : "归档末端 ONI 未处于连续暖段，不绘制近期暖段。"}
          两种指数均按 ONI 首个暖季中心月对齐，不按日历年起点对齐。使用 NOAA 公布的一位小数 ERSSTv6 表，ONI 历史暖事件要求至少5个连续重叠三月均值达到 +0.5°C；起点不是当时确认时点。
          本页暖侧幅度分档：弱 [0.5, 1.0)、中等 [1.0, 1.5)、强 [1.5, 2.0)、极强 ≥2.0°C；单期分档不是完整事件强度。图中 ±0.5°C 为参考线，月度 Niño3.4 越线不等于正式事件确认。百分位为历史样本中不高于归档最新值的比例。
        </div>
      </section>
      <section className="panel">
        <div className="panel-head">
          <h3>历史厄尔尼诺事件</h3>
          <Link href="/events/">查看历史复盘 ↗</Link>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>开始 / 结束中心月</th>
                <th>ONI 峰值</th>
                <th>峰值中心月</th>
                <th>持续暖季</th>
                <th>强度</th>
              </tr>
            </thead>
            <tbody>
              {[...data.events].reverse().map((e) => (
                <tr key={e.id}>
                  <td>
                    <Link href={`/events/?event=${e.id}`}>
                      {e.start.slice(0, 7)} – {e.end.slice(0, 7)} ↗
                    </Link>
                  </td>
                  <td>{num(e.peak)} °C</td>
                  <td>{day(e.peak_date)}</td>
                  <td>{e.seasons}</td>
                  <td>{strengthZh[e.strength] || e.strength}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="panel-note">
          历史事件按 ONI 事后识别，达到5季条件的观测期结束日不等于官方公告日。NOAA 现行 ENSO 官方监测与预测使用 RONI，本页保留 ONI 历史比较；近期 ONI 估计值仍可能修订。
        </div>
      </section>
    </main>
  );
}
