"use client";
import { useState } from "react";
import type { EChartsOption } from "echarts";
import Chart, { chartBase } from "./Chart";
import Outlook from "./Outlook";
import { Loading, SourceState, Provenance } from "./Common";
import {
  useData,
  CropData,
  names,
  num,
  pct,
  sources,
  day,
  preferred,
  sameDefinition,
  revision,
  Production,
  basisLabel,
} from "@/lib/data";
import { zhCountry } from "@/lib/labels";
const windows: Record<string, number> = {
  "1Y": 12,
  "3Y": 36,
  "5Y": 60,
  "10Y": 120,
  Full: 10000,
};
const index = (m: string) =>
  Number(m.slice(0, 4)) * 12 + Number(m.slice(5, 7)) - 1;
const label = (i: number) =>
  `${Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, "0")}`;
export default function CropResearch({ crop }: { crop: string }) {
  const { data, error } = useData<CropData>(crop);
  const [country, setCountry] = useState("Global"),
    [mode, setMode] = useState("indexed"),
    [range, setRange] = useState("10Y"),
    [metric, setMetric] = useState("production_yoy"),
    [histKind, setHistKind] = useState("estimate"),
    [basis, setBasis] = useState("auto");
  if (!data) return <Loading error={error} />;
  const histCountries = [...new Set(data.history.map((r) => r.country))].sort();
  const candidates = data.history.filter(
    (r) => r.country === country && r.status === histKind,
  );
  const definitions = [
    ...new Set(
      candidates.map((r) => `${r.year_basis}|${r.commodity_basis}|${r.source}`),
    ),
  ];
  const definition = basis === "auto" ? definitions[0] : basis;
  const history = candidates.filter(
    (r) => `${r.year_basis}|${r.commodity_basis}|${r.source}` === definition,
  );
  const monthly = data.price_research.monthly;
  const all = Object.keys(monthly.overseas || {})
    .concat(Object.keys(monthly.china || {}))
    .sort();
  const end = all.length ? index(all.at(-1)!) : new Date().getFullYear() * 12;
  const start = Math.max(
    all.length ? index(all[0]) : end,
    end - windows[range] + 1,
  );
  const months = Array.from({ length: Math.max(0, end - start + 1) }, (_, i) =>
    label(start + i),
  );
  const common = months.filter(
    (m) => monthly.china?.[m] != null && monthly.overseas?.[m] != null,
  );
  const hasChina = months.some((m) => monthly.china?.[m] != null);
  const baseMonth = hasChina
    ? common[0]
    : months.find((m) => monthly.overseas?.[m] != null);
  const transform = (market: string) => {
    const raw = months.map((m) => monthly[market]?.[m] ?? null);
    const valid = raw.filter((v): v is number => v !== null);
    const mean = valid.reduce((s, v) => s + v, 0) / valid.length;
    const sd = Math.sqrt(
      valid.reduce((s, v) => s + (v - mean) ** 2, 0) / valid.length,
    );
    const b = baseMonth ? monthly[market]?.[baseMonth] : null;
    return raw.map((v) =>
      v === null
        ? null
        : mode === "raw"
          ? v
          : mode === "indexed"
            ? b
              ? (v / b) * 100
              : null
            : sd
              ? (v - mean) / sd
              : null,
    );
  };
  const metricNames: Record<string, string> = {
    production_yoy: "Production YoY",
    yield_yoy: "Yield YoY",
    production_gap: "Production Gap vs Trend",
    yield_anomaly_pct: "Yield Anomaly vs Trend",
  };
  const prod = months.map((m) => {
    if (!m.endsWith("-01")) return null;
    const r = history.find((r) => r.year === Number(m.slice(0, 4)));
    return r ? (r[metric as keyof typeof r] as number | null) : null;
  });
  const overseas = data.prices.find((p) => p.market === "overseas"),
    china = data.prices.find((p) => p.market === "china");
  const option = {
    ...chartBase,
    grid: { top: 66, bottom: 68, left: 58, right: mode === "raw" ? 115 : 55 },
    xAxis: { type: "category", data: months, axisLabel: { color: "#718478" } },
    yAxis: [
      { ...chartBase.yAxis, name: "Production %", position: "left" },
      {
        ...chartBase.yAxis,
        name:
          mode === "raw"
            ? overseas?.unit || "USD/t"
            : mode === "indexed"
              ? "Price index"
              : "Price Z-score",
        position: "right",
        splitLine: { show: false },
      },
      {
        ...chartBase.yAxis,
        name: mode === "raw" ? "CNY/t" : "",
        position: "right",
        offset: 60,
        show: mode === "raw",
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: `${metricNames[metric]} · ${histKind}`,
        type: "bar",
        data: prod,
        yAxisIndex: 0,
        barMaxWidth: 8,
        itemStyle: { color: "#a7b9a3" },
      },
      {
        name: `Overseas · ${overseas?.symbol || "N/A"}`,
        type: "line",
        symbol: "none",
        connectNulls: false,
        data: transform("overseas"),
        yAxisIndex: 1,
      },
      {
        name: `China · ${china?.symbol || "N/A"}`,
        type: "line",
        symbolSize: 4,
        connectNulls: false,
        data: transform("china"),
        yAxisIndex: mode === "raw" ? 2 : 1,
      },
    ],
  } as EChartsOption;
  const corr = data.price_research.ranges[range];
  const forecast = preferred(
    data.production.filter(
      (r) =>
        r.country === country &&
        !r.region &&
        r.status === "forecast" &&
        r.target_year === new Date().getFullYear(),
    ),
    country,
  );
  const supply = forecast
    ? data.supply.filter(
        (r) =>
          r.source === forecast.source &&
          sameDefinition(r, forecast) &&
          r.target_year === forecast.target_year &&
          day(r.available_date) === day(forecast.available_date),
      )
    : [];
  const val = (m: string) => supply.find((r) => r.metric === m)?.value;
  const stu =
    val("ending_stocks") != null && val("consumption")
      ? (val("ending_stocks")! / val("consumption")!) * 100
      : null;
  const currentMonth = months.at(-1);
  const pastMonth = currentMonth ? label(index(currentMonth) - 3) : "";
  const priceChange =
    currentMonth && monthly.overseas?.[pastMonth]
      ? (monthly.overseas[currentMonth] / monthly.overseas[pastMonth] - 1) * 100
      : null;
  return (
    <section className="advanced-research">
      <div className="page-heading">
        <div>
          <div className="eyebrow">品种研究 / {crop.toUpperCase()}</div>
          <h2>{names[crop]}</h2>
          <p>产量预测 · 预测修正 · 供需平衡 · 市场 价格</p>
        </div>
        <div className="update-clock">
          LAST PUBLISHED<strong>{day(data.generated_at)}</strong>
        </div>
      </div>
      <Outlook initialCrop={crop} compact navigateCrops />
      <section>
        <div className="section-heading">
          <div>
            <div className="eyebrow">产量 · 单产 · 价格</div>
            <h2>历史产量 × 国内外价格</h2>
          </div>
        </div>
        <div className="toolbar filters">
          <label>
            Region / Country
            <select
              value={country}
              onChange={(e) => {
                setCountry(e.target.value);
                setBasis("auto");
              }}
            >
              <optgroup label="研究地区">
                {data.research_units
                  .filter((c) => histCountries.includes(c))
                  .map((c) => (
                    <option key={c} value={c}>
                      {zhCountry(c)}
                    </option>
                  ))}
              </optgroup>
              <optgroup label="成员国家">
                {histCountries
                  .filter((c) => !data.research_units.includes(c))
                  .map((c) => (
                    <option key={c} value={c}>
                      {zhCountry(c)}
                    </option>
                  ))}
              </optgroup>
            </select>
          </label>
          <label>
            History Type
            <select
              value={histKind}
              onChange={(e) => {
                setHistKind(e.target.value);
                setBasis("auto");
              }}
            >
              <option value="estimate">Estimate · 修订后历史估计</option>
              <option value="actual">Actual · 官方实产</option>
            </select>
          </label>
          <label>
            Definition
            <select value={basis} onChange={(e) => setBasis(e.target.value)}>
              <option value="auto">优先可用口径</option>
              {definitions.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
          <label>
            Production Metric
            <select value={metric} onChange={(e) => setMetric(e.target.value)}>
              {Object.entries(metricNames).map(([k, v]) => (
                <option value={k} key={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <div className="segmented" aria-label="价格模式">
            {["raw", "indexed", "standardized"].map((m) => (
              <button
                key={m}
                className={mode === m ? "active" : ""}
                onClick={() => setMode(m)}
              >
                {m === "raw" ? "Raw" : m === "indexed" ? "Indexed" : "Z-score"}
              </button>
            ))}
          </div>
          <div className="segmented" aria-label="历史区间">
            {Object.keys(windows).map((w) => (
              <button
                key={w}
                className={range === w ? "active" : ""}
                onClick={() => setRange(w)}
              >
                {w}
              </button>
            ))}
          </div>
        </div>
        <div className="panel">
          <Chart
            height={390}
            option={option}
            label="历史产量变化与中国海外价格图"
          />
          <div className="panel-note">
            {definition || "N/A"} · 年度产量柱标在目标年 1
            月，仅表示年度归属。价格为各月已获取报价的均值；缺失月份保持空缺。
            {mode === "indexed"
              ? `共同基期 ${baseMonth || "N/A"} = 100。`
              : mode === "raw"
                ? "USD 和 CNY 使用独立纵轴。"
                : "各价格序列在所选窗口内分别计算 Z-score。"}
            <br />
            中国 {china?.price_type || "N/A"}；海外{" "}
            {overseas?.price_type || "N/A"}。产量国家筛选不改变价格基准。
          </div>
          <div className="provenance">
            Source:{" "}
            {overseas && <a href={overseas.source_url}>World Bank ↗</a>} /{" "}
            {china ? <a href={china.source_url}>NBS ↗</a> : "China N/A"} ·
            Forecast Date: N/A · Target: {months[0]} – {months.at(-1)} · Last
            Updated: {day(overseas?.download_timestamp)}
          </div>
        </div>
      </section>
      <div className="two-col">
        <section className="panel">
          <div className="panel-head">
            <h3>国内外价格相关性</h3>
            <span>月均报价环比 · {range}</span>
          </div>
          <div className="stat-grid">
            <div>
              <span>相关系数</span>
              <strong>{num(corr?.correlation, 3)}</strong>
            </div>
            <div>
              <span>配对月均变化样本</span>
              <strong>{corr?.return_pairs ?? 0}</strong>
            </div>
            <div>
              <span>进口平价</span>
              <strong>N/A</strong>
            </div>
            <div>
              <span>原币种价差</span>
              <strong>N/A</strong>
            </div>
          </div>
          <Chart
            height={250}
            option={
              {
                ...chartBase,
                legend: { show: false },
                yAxis: { ...chartBase.yAxis, min: -1, max: 1 },
                series: [
                  {
                    type: "line",
                    name: "Rolling 12M return correlation",
                    data: (corr?.rolling || []).map((r) => [
                      r.month + "-01",
                      r.value,
                    ]),
                    connectNulls: false,
                  },
                ],
              } as EChartsOption
            }
            label="12个月滚动相关性"
          />
          <div className="panel-note">
            至少 12
            对连续月均报价变化才计算；正滞后代表海外领先中国。币种、规格和税费未统一时不计算原价差/进口平价。
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Lag (months)</th>
                  {[-6, -3, 0, 3, 6].map((l) => (
                    <th key={l}>{l}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Correlation</td>
                  {[-6, -3, 0, 3, 6].map((l) => (
                    <td key={l}>
                      {num(
                        corr?.leadlag.find((r) => r.lag === l)?.correlation,
                        3,
                      )}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <h3>供需平衡与价格变化</h3>
            <span>
              {zhCountry(country)} · {forecast?.target_year || "N/A"}
            </span>
          </div>
          <div className="stat-grid">
            <div>
              <span>近3月产量预测修正</span>
              <strong>
                {pct(forecast ? revision(data.production, forecast, 3) : null)}
              </strong>
            </div>
            <div>
              <span>海外价格 3M</span>
              <strong>{pct(priceChange)}</strong>
            </div>
            <div>
              <span>库存消费比</span>
              <strong>{pct(stu)}</strong>
            </div>
            <div>
              <span>库存消费比修正</span>
              <strong>N/A</strong>
            </div>
          </div>
          <dl className="stats-list">
            {[
              "beginning_stocks",
              "ending_stocks",
              "consumption",
              "exports",
              "imports",
            ].map((m) => (
              <div key={m}>
                <dt>{m.replaceAll("_", " ")}</dt>
                <dd>{num(val(m))} Mt</dd>
              </div>
            ))}
          </dl>
          <Provenance row={forecast} />
          <div className="panel-note">
            库存消费比 = Ending stocks / Domestic
            consumption。价格和预测修正分别标注观察窗口；数据不足时不计算精确
            Price-in 比例。
          </div>
          <div className="panel-head">
            <h3>地区天气与生育期</h3>
          </div>
          <dl className="stats-list">
            <div>
              <dt>降水 / 温度异常</dt>
              <dd>N/A</dd>
            </div>
            <div>
              <dt>当前生育期</dt>
              <dd>N/A</dd>
            </div>
          </dl>
          <div className="panel-note">尚无已验证地区天气序列与作物历记录。</div>
        </section>
      </div>
      <section className="panel">
        <div className="panel-head">
          <h3>历史产量记录</h3>
          <span>{definition || "No compatible observations"}</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Target Year</th>
                <th>Production (Mt)</th>
                <th>Production YoY</th>
                <th>Yield (t/ha)</th>
                <th>Yield Anomaly</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history
                .slice(-12)
                .reverse()
                .map((h) => (
                  <tr key={h.year}>
                    <td>{h.year}</td>
                    <td>{num(h.production)}</td>
                    <td>{pct(h.production_yoy)}</td>
                    <td>{num(h.yield_value)}</td>
                    <td>{pct(h.yield_anomaly_pct)}</td>
                    <td>{h.status}</td>
                  </tr>
                ))}
            </tbody>
          </table>
          {!history.length && (
            <div className="empty">N/A · 没有兼容的历史实产/估计记录</div>
          )}
        </div>
      </section>
    </section>
  );
}
