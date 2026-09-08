"use client";
import { useState } from "react";
import Link from "next/link";
import Chart, { chartBase, colors } from "./Chart";
import { Loading } from "./Common";
import { Climate, useData, num, pct, day, strengthZh } from "@/lib/data";
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
  const lastWarm = data.events.at(-1);
  const currentStart =
    lastWarm && day(lastWarm.end) >= day(points.at(-1)?.date)
      ? lastWarm.start
      : points.find(
          (p) => p.date.slice(0, 4) === new Date().getFullYear().toString(),
        )?.date;
  const cycles = selected.map((e) => ({
    name: `${e.start.slice(0, 4)}/${e.end.slice(2, 4)}`,
    start: e.start,
  }));
  if (currentStart) cycles.push({ name: "Current", start: currentStart });
  return (
    <main>
      <div className="page-heading">
        <div>
          <div className="eyebrow">海洋与气候 · NOAA</div>
          <h1>厄尔尼诺追踪</h1>
          <p>观察海温异常、当前强度与历史相似周期</p>
        </div>
        <a href={data.roni_url} target="_blank" rel="noreferrer">
          NOAA RONI ↗
        </a>
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
          观测日期 {day(current?.date)} · {current?.season}
        </span>
      </div>
      <div className="stat-grid">
        <div>
          <span>当前异常 / {strengthZh[current?.strength] || "暂无数据"}</span>
          <strong>{num(current?.value, idx === "ONI" ? 1 : 2)} °C</strong>
        </div>
        <div>
          <span>历史百分位 / {current?.sample_size || 0} 个观测值</span>
          <strong>{num(current?.percentile, 1)}%</strong>
        </div>
        <div>
          <span>连续暖月 / 暖季</span>
          <strong>{current?.warm_seasons ?? "N/A"}</strong>
        </div>
        <div>
          <span>近1月 / 3月变化</span>
          <strong>
            {num(current?.chg_1m)} / {num(current?.chg_3m)}
          </strong>
          <small> °C</small>
        </div>
      </div>
      <section className="panel">
        <div className="panel-head">
          <h3>{idx} · 历史变化</h3>
          <span>月度 / 三个月滑动平均</span>
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
                    label: { color: "#afb6ba" },
                    data: [
                      { yAxis: 0.5, name: "El Niño threshold" },
                      { yAxis: -0.5, name: "La Niña threshold" },
                    ],
                  },
                },
              ],
            } as EChartsOption
          }
        />
        <div className="provenance">
          来源： <a href={current?.source_url}>NOAA CPC ↗</a> · 预测日期：
          不适用（观测指数） · 观测期： {day(current?.date)} · 更新：{" "}
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
              xAxis: { type: "value", name: "Months from T", min: -6, max: 24 },
              yAxis: { ...chartBase.yAxis, name: "海温异常 °C" },
              series: cycles.map((e, i) => ({
                name: e.name,
                type: "line",
                showSymbol: false,
                lineStyle: {
                  width: e.name === "Current" ? 3 : 1.5,
                  type: e.name === "Current" ? "solid" : "dashed",
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
          使用NOAA公布的一位小数ERSSTv6表，ONI 暖事件要求 ≥5
          个连续重叠三月季均值达到 +0.5°C。起点不是当时确认时点。强度范围：Weak
          ≥0.5、Moderate ≥1.0、Strong ≥1.5、Very Strong ≥2.0°C。月度 Niño3.4
          越过阈值本身不等于正式事件确认。百分位为历史样本中 ≤ 当前值的比例。
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
                <th>开始 / 结束</th>
                <th>ONI 峰值</th>
                <th>峰值月份</th>
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
        <div className="panel-note">{data.methodology}</div>
      </section>
    </main>
  );
}
