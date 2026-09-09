"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import * as echarts from "echarts";
import Chart, { chartBase } from "./Chart";
import { Loading } from "./Common";
import {
  useData,
  CROPS,
  base,
  num,
  pct,
  day,
  Overview,
  sources,
} from "@/lib/data";
import { zhCountry } from "@/lib/labels";
const cropNames: Record<string, string> = {
  wheat: "小麦",
  corn: "玉米",
  soybean: "大豆",
  rice: "水稻",
  sugar: "糖",
};
const cropEn: Record<string, string> = {
  wheat: "WHEAT",
  corn: "CORN",
  soybean: "SOYBEAN",
  rice: "RICE",
  sugar: "SUGAR",
};
type Ranked = {
  name: string;
  value: number;
  previous: number | null;
  yoy: number | null;
  change: number | null;
  share: number;
  members: string[];
  baseline_yoy?: number | null;
  yoy_spread_pp?: number | null;
  contribution_pp?: number | null;
};
type ProductionEvidence = {
  source: string;
  source_url?: string;
  available_date?: string;
  source_target_year?: number;
  fallback_reason?: string | null;
};
type Snapshot = {
  target_year: number;
  status: string;
  source: string;
  source_url: string | null;
  available_date: string;
  publication_date: string | null;
  download_timestamp: string;
  commodity_basis: string;
  year_basis: string;
  world: Ranked;
  ranking: Ranked[];
  top5_share: number;
  mode: string;
  local_coverage_pct: number;
  baseline: { source: string; value: number; previous: number | null; yoy: number | null; source_url?: string };
  source_evidence: Record<string, ProductionEvidence>;
  china: ProductionEvidence & { value: number | null };
};
type Data = {
  crop: string;
  years: Record<string, Snapshot>;
  history: {
    year: number;
    value: number;
    yoy: number | null;
    status: string;
  }[];
  geographies: { country: string; map_name: string }[];
  updated: string;
  methodology: string;
};
const palette = {
  green: "#16a366",
  greenDeep: "#087e50",
  negative: "#cf846e",
  neutral: "#dbe6df",
  empty: "#eef2ef",
  ink: "#173a2b",
  muted: "#718178",
  border: "#ffffff",
};
const eu = [
  "Austria",
  "Belgium",
  "Bulgaria",
  "Croatia",
  "Cyprus",
  "Czechia",
  "Czech Republic",
  "Denmark",
  "Estonia",
  "Finland",
  "France",
  "Germany",
  "Greece",
  "Hungary",
  "Ireland",
  "Italy",
  "Latvia",
  "Lithuania",
  "Luxembourg",
  "Malta",
  "Netherlands",
  "Poland",
  "Portugal",
  "Romania",
  "Slovakia",
  "Slovenia",
  "Spain",
  "Sweden",
];
const eu15 = [
  "Austria",
  "Belgium",
  "Denmark",
  "Finland",
  "France",
  "Germany",
  "Greece",
  "Ireland",
  "Italy",
  "Luxembourg",
  "Netherlands",
  "Portugal",
  "Spain",
  "Sweden",
  "United Kingdom",
];
function mapEntity(country: string, rank: Ranked[]) {
  const members = new Set(rank.flatMap((r) => r.members));
  if (members.has("EU-15") && eu15.includes(country)) return "EU-15";
  if (
    members.has("EU-25") &&
    (eu15.includes(country) ||
      [
        "Cyprus",
        "Czechia",
        "Czech Republic",
        "Estonia",
        "Hungary",
        "Latvia",
        "Lithuania",
        "Malta",
        "Poland",
        "Slovakia",
        "Slovenia",
      ].includes(country))
  )
    return "EU-25";
  if (
    members.has("European Union") &&
    (eu.includes(country) ||
      (country === "United Kingdom" && !members.has(country)))
  )
    return "European Union";
  return country;
}
function Change({ value }: { value: number | null | undefined }) {
  return (
    <span
      className={`change-pill ${value == null ? "neutral" : value < 0 ? "negative" : "positive"}`}
    >
      {value == null
        ? "暂无可比数据"
        : `${value < 0 ? "↘" : "↗"} ${pct(value)}`}
    </span>
  );
}
function ChinaSource({ crop, year }: { crop: string; year: number }) {
  const { data } = useData<Data>('dashboard_' + crop);
  const row = data?.years[String(year)]?.china;
  return (
    <div className="china-note">
      <strong>中国实际采用的产量来源</strong>
      <span>
        {row
          ? `${sources[row.source]} · ${num(row.value)} 百万吨`
          : "当前年度暂无可用预测"}
      </span>
      <small>
        {row?.source === 'usda_psd' ? 'PSD 数据：该国家暂无可用本国预测。' : '与首页本土成对组合一致；保留机构原始证据。'}
      </small>
      {row?.source_url && (
        <a href={row.source_url} target="_blank" rel="noreferrer">
          查看原报告 ↗
        </a>
      )}
    </div>
  );
}
export default function Dashboard({
  initialCrop = "wheat",
}: {
  initialCrop?: string;
}) {
  const [crop, setCrop] = useState(initialCrop),
    [year, setYear] = useState(new Date().getFullYear()),
    [selected, setSelected] = useState<string | null>(null),
    [ready, setReady] = useState(false),
    [mapError, setMapError] = useState(""),
    [zoom, setZoom] = useState(1.1);
  const { data, error } = useData<Data>("dashboard_" + crop);
  const { data: overview } = useData<Overview>("overview");
  useEffect(() => {
    setCrop(initialCrop);
  }, [initialCrop]);
  useEffect(() => {
    const query = new URLSearchParams(location.search).get("crop");
    if (query && CROPS.includes(query)) setCrop(query);
  }, []);
  useEffect(() => {
    let active = true;
    fetch(`${base}/world.json`)
      .then((r) => {
        if (!r.ok) throw Error("地图加载失败");
        return r.json();
      })
      .then((geo) => {
        geo.features = geo.features.filter(
          (f: { properties: { name: string } }) =>
            f.properties.name !== "Antarctica",
        );
        echarts.registerMap("dashboard-world", geo);
        if (active) setReady(true);
      })
      .catch((e) => active && setMapError(e.message));
    return () => {
      active = false;
    };
  }, []);
  const snapshot = data?.years[String(year)];
  const rank = snapshot?.ranking || [];
  const chosen = rank.find((r) => r.name === selected);
  const mapOption = useMemo(() => {
    if (!ready) return null;
    const lookup = (name: string) => {
      const country =
        data?.geographies.find((g) => g.map_name === name)?.country || name;
      const effective = mapEntity(country, rank);
      return rank.find((r) => r.members.includes(effective));
    };
    const features =
      (
        echarts.getMap("dashboard-world")?.geoJSON as {
          features: { properties: { name: string } }[];
        }
      )?.features || [];
    return {
      backgroundColor: "transparent",
      tooltip: {
        confine: true,
        backgroundColor: "#ffffff",
        borderColor: "#dce6de",
        textStyle: { color: palette.ink, fontSize: 13 },
        padding: [12, 16],
        formatter: (p: unknown) => {
          const name = (p as { name: string }).name;
          const r = lookup(name);
          return r
            ? `<b>${r.name === "其他" ? "其他国家 / 地区合计" : zhCountry(r.name)}</b><br/>${num(r.value)} 百万吨<br/>同比 ${pct(r.yoy)}${r.name === "其他" ? '<br/><span style="color:#718178">统一展示其他合计的变化</span>' : ""}`
            : `${zhCountry(name)}<br/>暂无数据`;
        },
      },
      visualMap: {
        show: false,
        type: "piecewise",
        pieces: [
          { lt: -10, color: "#ca8b72" },
          { gte: -10, lt: -3, color: "#dfae95" },
          { gte: -3, lt: 0, color: "#e4dbc7" },
          { value: 0, color: "#dce6df" },
          { gt: 0, lte: 3, color: "#99d9af" },
          { gt: 3, lte: 10, color: "#4ebd83" },
          { gt: 10, color: "#16995d" },
        ],
      },
      series: [
        {
          type: "map",
          map: "dashboard-world",
          roam: true,
          zoom,
          center: [12, 18],
          name: "产量变化",
          data: features
            .filter((f) => f.properties.name !== "Antarctica")
            .map((f) => {
              const r = lookup(f.properties.name);
              return {
                name: f.properties.name,
                value: r?.yoy ?? null,
                selected: selected !== null && r?.name === selected,
                itemStyle:
                  r?.yoy == null ? { areaColor: palette.empty } : undefined,
              };
            }),
          itemStyle: {
            areaColor: palette.empty,
            borderColor: palette.border,
            borderWidth: 0.8,
          },
          emphasis: {
            label: { show: false },
            itemStyle: { borderColor: palette.greenDeep, borderWidth: 1.6 },
          },
          select: {
            label: { show: false },
            itemStyle: { borderColor: palette.greenDeep, borderWidth: 2 },
          },
          label: { show: false },
        },
      ],
    } as echarts.EChartsOption;
  }, [ready, data, rank, selected, zoom]);
  function mapClick(name: string) {
    const country =
      data?.geographies.find((g) => g.map_name === name)?.country || name;
    const r = rank.find((r) => r.members.includes(mapEntity(country, rank)));
    if (r) setSelected(r.name === selected ? null : r.name);
  }
  const climate = overview?.climate["Nino3.4"];
  const trend = data?.history.filter((p) => p.year <= year).slice(-16) || [];
  if (!data)
    return (
      <main className="dashboard">
        <div className="dashboard-heading">
          <h1>全球产量地图</h1>
        </div>
        <Loading error={error} />
      </main>
    );
  return (
    <main className="dashboard">
      <div className="dashboard-heading">
        <div>
          <h1>全球产量，一图看清</h1>
          <p>追踪主要产区，观察供给变化。</p>
        </div>
        <div className="edition-note">
          <span className="live-dot" />
          数据截至 {day(snapshot?.download_timestamp || data.updated)}
        </div>
      </div>
      <div className="dashboard-controls">
        <div className="product-switch" aria-label="品种选择">
          {CROPS.map((c) => (
            <button
              key={c}
              aria-pressed={crop === c}
              className={crop === c ? "active" : ""}
              onClick={() => {
                setCrop(c);
                setSelected(null);
              }}
            >
              <CropIcon crop={c} />
              <span>{cropNames[c]}</span>
            </button>
          ))}
        </div>
        <label className="year-control">
          <span>年度</span>
          <select
            aria-label="年度"
            value={year}
            onChange={(e) => {
              setYear(+e.target.value);
              setSelected(null);
            }}
          >
            {[
              ...new Set([
                2027,
                2026,
                2025,
                ...Object.keys(data.years).map(Number),
              ]),
            ]
              .sort((a, b) => b - a)
              .map((y) => (
                <option key={y} value={y}>
                  {y} / {String(y + 1).slice(2)}
                </option>
              ))}
          </select>
        </label>
      </div>
      <section
        className="world-panel"
        aria-label={`${cropNames[crop]}全球产量地图`}
      >
        <div className="world-panel-heading">
          <div className="world-title">
            <span className="product-kicker">{cropEn[crop]}</span>
            <h2>
              {cropNames[crop]}产量
              {snapshot?.status === "estimate" ? "回顾" : "展望"}
            </h2>
          </div>
          <div className="world-metrics">
            <div>
              <span>同比变化</span>
              <strong
                className={
                  (snapshot?.world.yoy || 0) < 0 ? "negative" : "positive"
                }
              >
                {pct(snapshot?.world.yoy)}
              </strong>
            </div>
            <div>
              <span>较 PSD 同比</span>
              <strong>{snapshot?.world.yoy_spread_pp == null ? "—" : `${snapshot.world.yoy_spread_pp >= 0 ? "+" : ""}${num(snapshot.world.yoy_spread_pp, 2)}pp`}</strong>
            </div>
            <div>
              <span>全球产量</span>
              <strong>{num(snapshot?.world.value, 1)}<small> 百万吨</small></strong>
            </div>
            <div className="share-metric">
              <span>本土数据覆盖</span>
              <strong>{snapshot ? num(snapshot.local_coverage_pct, 1) + "%" : "—"}</strong>
            </div>
          </div>
        </div>
        <div className="world-body">
          <div className="world-map">
            <div className="map-chart">
              {mapOption ? (
                <Chart
                  height={420}
                  option={mapOption}
                  onClick={mapClick}
                  label={`${cropNames[crop]}前五产区及其他地区的产量变化地图`}
                />
              ) : (
                <Loading error={mapError} />
              )}
            </div>
            <div className="map-actions">
              <button
                title="放大地图"
                aria-label="放大地图"
                onClick={() => setZoom((z) => Math.min(z + 0.25, 3))}
              >
                ＋
              </button>
              <button
                title="缩小地图"
                aria-label="缩小地图"
                onClick={() => setZoom((z) => Math.max(z - 0.25, 0.8))}
              >
                −
              </button>
              <button
                title="重置地图"
                aria-label="重置地图"
                onClick={() => {
                  setZoom(1.1);
                  setSelected(null);
                }}
              >
                ↺
              </button>
            </div>
            <div className="map-bottom">
              <div className="map-legend">
                <span>减产</span>
                <i />
                <span>增产</span>
              </div>
              <span>其他按合计着色 · 点击查看</span>
            </div>
          </div>
          <aside className="ranking-panel">
            <div className="ranking-heading">
              <h3>主要产区</h3>
              <span>前五 + 其他</span>
            </div>
            <div className="ranking-caption">
              <span>国家 / 地区</span>
              <span>产量 · 同比</span>
            </div>
            <div className="ranking-list">
              {rank.map((r, i) => (
                <button
                  key={r.name}
                  className={`rank-item ${selected === r.name ? "selected" : ""} ${r.name === "其他" ? "others" : ""}`}
                  onClick={() =>
                    setSelected(selected === r.name ? null : r.name)
                  }
                >
                  <div className="rank-line">
                    <span className="rank-number">
                      {i < 5 ? String(i + 1).padStart(2, "0") : "+"}
                    </span>
                    <strong>{zhCountry(r.name)}</strong>
                    <span className="rank-value">{num(r.value, 1)}</span>
                  </div>
                  <div className="rank-subline">
                    <div className="rank-track">
                      <i style={{ width: `${r.share}%` }} />
                    </div>
                    <span
                      className={
                        r.yoy == null
                          ? "muted"
                          : r.yoy < 0
                            ? "negative"
                            : "positive"
                      }
                    >
                      {pct(r.yoy)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
            {!snapshot && <div className="empty">该年度尚无可用预测</div>}
            <p className="ranking-footnote">
              单位：百万吨 · 地区按固定成员汇总
            </p>
          </aside>
        </div>
        <div className="world-panel-footer">
          <span>{snapshot?.mode === "local_composite" ? "本土优先产量组合 · 同源同比" : "PSD 历史基础库"}{crop === "rice" ? " · 精米" : ""}</span>
          <details>
            <summary>口径与来源</summary>
            <p>{data.methodology}</p>
            <p>
              “其他”为前五以外的合计，地图统一着色不表示所有成员都同向变化。
              {snapshot?.status === "estimate"
                ? "本年度是修订后历史估计。"
                : "本年度为近年暂定估计/预测，分类为保守规则，后续可能修订。"}
            </p>
            <a
              href={
                snapshot?.baseline.source_url || "https://apps.fas.usda.gov/psdonline/"
              }
              target="_blank"
              rel="noreferrer"
            >
              PSD 历史基础库 ↗
            </a>
            <span> · 组合最近可得日期 {day(snapshot?.available_date)}</span>
          </details>
        </div>
      </section>
      {chosen && (
        <section className="selection-panel" aria-label="产区详情">
          <div className="selection-heading">
            <div>
              <span className="quiet-eyebrow">产区详情</span>
              <h2>{zhCountry(chosen.name)}</h2>
            </div>
            <button
              className="close-button"
              aria-label="关闭产区详情"
              onClick={() => setSelected(null)}
            >
              ×
            </button>
          </div>
          <div className="selection-content">
            <div className="selection-metric">
              <span>产量</span>
              <strong>
                {num(chosen.value, 2)}
                <small> 百万吨</small>
              </strong>
            </div>
            <div className="selection-metric">
              <span>同比增减</span>
              <strong>
                {chosen.change != null
                  ? `${chosen.change > 0 ? "+" : ""}${num(chosen.change, 2)}`
                  : "—"}
                <small> 百万吨</small>
              </strong>
            </div>
            <div>
              <Change value={chosen.yoy} />
              <p className="muted">占全球 {num(chosen.share, 1)}%</p>
            </div>
          </div>
          {chosen.name === "China" && <ChinaSource crop={crop} year={year} />}
          <details className="member-details">
            <summary>
              {chosen.members.length > 1
                ? `查看 ${chosen.members.length} 个成员及计算依据`
                : "查看计算依据"}
            </summary>
            <p>{chosen.members.map(zhCountry).join("、")}</p>
            <p>
              上年同一成员合计 {num(chosen.previous)}{" "}
              百万吨；同比按两年合计计算，缺失不补零。
            </p>
          </details>
        </section>
      )}
      <div className="dashboard-bottom">
        <section className="trend-panel">
          <div className="small-panel-heading">
            <div>
              <span className="quiet-eyebrow">供给趋势</span>
              <h2>{cropNames[crop]}全球产量</h2>
            </div>
            <span className="chart-unit">百万吨</span>
          </div>
          <Chart
            height={240}
            label="全球产量历史与预测趋势"
            option={
              {
                ...chartBase,
                grid: { top: 22, bottom: 35, left: 46, right: 20 },
                legend: { show: false },
                dataZoom: [],
                xAxis: {
                  type: "category",
                  data: trend.map((r) => String(r.year)),
                  axisLine: { lineStyle: { color: "#dce5df" } },
                  axisTick: { show: false },
                  axisLabel: { color: "#7b8b80", interval: 3 },
                },
                yAxis: { ...chartBase.yAxis, axisLabel: { color: "#7b8b80" } },
                series: [
                  {
                    type: "line",
                    name: "历史估计",
                    symbol: "none",
                    lineStyle: { width: 2.5, color: palette.green },
                    areaStyle: { color: "#e7f5eb" },
                    data: trend.map((r) =>
                      r.status === "estimate" ? r.value : null,
                    ),
                  },
                  {
                    type: "line",
                    name: "产量预测",
                    symbol: "circle",
                    symbolSize: 5,
                    lineStyle: {
                      width: 2.5,
                      type: "dashed",
                      color: palette.green,
                    },
                    data: trend.map((r, i) =>
                      r.status === "forecast" ||
                      i === trend.findIndex((p) => p.status === "forecast") - 1
                        ? r.value
                        : null,
                    ),
                  },
                ],
              } as echarts.EChartsOption
            }
          />
          <div className="trend-legend">
            <span>
              <i />
              历史估计
            </span>
            <span>
              <i className="dashed" />
              机构预测
            </span>
          </div>
        </section>
        <Link className="climate-preview" href="/elnino/">
          <div className="small-panel-heading">
            <div>
              <span className="quiet-eyebrow">太平洋气候</span>
              <h2>厄尔尼诺追踪</h2>
            </div>
            <span className="arrow-circle">↗</span>
          </div>
          <div className="climate-preview-value">
            {num(climate?.value, 2)}
            <span>°C</span>
          </div>
          <p>Niño 3.4 海温异常</p>
          <div className="climate-scale">
            <i
              style={{
                left: `${Math.min(98, Math.max(2, (((climate?.value || 0) + 3) / 6) * 100))}%`,
              }}
            />
          </div>
          <div className="climate-preview-meta">
            <span>
              历史分位 <b>{num(climate?.percentile, 1)}%</b>
            </span>
            <span>{day(climate?.date)}</span>
          </div>
        </Link>
      </div>
    </main>
  );
}
function CropIcon({ crop }: { crop: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      aria-hidden="true"
    >
      <path d="M12 21V8M12 16c-5 0-7-3-7-6 4 0 7 2 7 6ZM12 12c5 0 7-3 7-6-4 0-7 2-7 6Z" />
      {crop === "soybean" || crop === "sugar" ? (
        <path d="M12 8c-3-1-4-3-3-6 3 1 4 3 3 6Z" />
      ) : (
        <path d="M12 8c3-2 3-5 0-7-3 2-3 5 0 7Z" />
      )}
    </svg>
  );
}
