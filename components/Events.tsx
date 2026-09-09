"use client";
import { useEffect, useState } from "react";
import Chart, { chartBase } from "./Chart";
import { Loading } from "./Common";
import { useData, CROPS, num, pct, day, Event, strengthZh, sources } from "@/lib/data";
import type { EChartsOption } from "echarts";
const cropNames: Record<string, string> = {
  wheat: "小麦",
  corn: "玉米",
  soybean: "大豆",
  rice: "水稻",
  sugar: "糖",
};
type Balance = {
  production: number | null;
  ending_stocks: number | null;
  consumption: number | null;
  stocks_to_use: number | null;
  source: string | null;
  source_url: string | null;
  document_id: string | null;
  available_date: string | null;
  publication_date: string | null;
  target_year: number;
  year_basis: string | null;
  commodity_basis: string | null;
  status: string;
  derived_global: boolean;
  unit: string;
};
type Series = {
  series_id: string;
  label: string;
  symbol: string | null;
  unit: string | null;
  first_date: string | null;
  last_date: string | null;
  observations: number;
  source_url: string | null;
  download_timestamp: string | null;
};
type Prices = {
  domestic_quality?: {
    n_obs: number;
    invalid_ohlc?: number;
    reason: string;
    volume?: number | null;
  }[];
  overseas_quality?: {
    n_obs: number;
    invalid_ohlc?: number;
    reason: string;
    volume?: number | null;
  }[];
  base_month: string | null;
  domestic_values: (number | null)[];
  overseas_values: (number | null)[];
  domestic_index: (number | null)[];
  overseas_index: (number | null)[];
  domestic_change: number | null;
  overseas_change: number | null;
  domestic_months: number;
  overseas_months: number;
  domestic_series: string;
  overseas_series: string | null;
};
type Window = {
  months: string[];
  oni: (number | null)[];
  years: number[];
  options: Record<string, Prices>;
};
type EventData = {
  crop: string;
  generated_at: string;
  events: Event[];
  windows: Record<string, Window>;
  annual: Record<string, Record<string, Record<string, Balance>>>;
  series: Record<string, Series>;
  domestic_options: string[];
  default_domestic: string;
  notes: string[];
};
const show = (v: number | null | undefined, d = 2) =>
  v == null ? "N/A" : num(v, d);
const percentage = (v: number | null | undefined) =>
  v == null ? "数据缺失" : pct(v);
const yearName = (year: number) => `${year}/${String(year + 1).slice(2)}`;
export default function Events() {
  const [crop, setCrop] = useState("corn"),
    [eventId, setEventId] = useState(""),
    [domestic, setDomestic] = useState(""),
    [overseasMode, setOverseasMode] = useState("futures"),
    [source, setSource] = useState("actual_production"),
    [year, setYear] = useState(0);
  const { data, error } = useData<EventData>("events_" + crop);
  useEffect(() => {
    const query = new URLSearchParams(location.search);
    if (query.get("event")) setEventId(query.get("event")!);
    if (CROPS.includes(query.get("crop") || "")) setCrop(query.get("crop")!);
  }, []);
  if (!data)
    return (
      <main className="event-page">
        <div className="page-heading">
          <div>
            <h1>历史事件复盘</h1>
            <p>对照气候、内外盘与年度供需。</p>
          </div>
        </div>
        <Loading error={error} />
      </main>
    );
  if (!data.events.length)
    return (
      <main>
        <h1>历史事件复盘</h1>
        <div className="empty">数据缺失</div>
      </main>
    );
  const event =
    data.events.find((e) => e.id === eventId) ||
    data.events.find(
      (e) => eventId >= e.start.slice(0, 7) && eventId <= e.end.slice(0, 7),
    ) ||
    data.events.at(-1)!;
  const window = data.windows[event.id];
  const domesticId = data.domestic_options.includes(domestic)
    ? domestic
    : data.default_domestic;
  const prices = window.options[domesticId + "|" + overseasMode];
  const domesticMeta = data.series[domesticId];
  const foreignMeta = prices.overseas_series
    ? data.series[prices.overseas_series]
    : null;
  const annualYear = window.years.includes(year)
    ? year
    : Number(event.start.slice(0, 4));
  const actualMode = source === "actual_production";
  const balances = data.annual[source]?.[String(annualYear)] || {};
  const world = balances.Global,
    china = balances.China;
  const chart = {
    ...chartBase,
    grid: { top: 58, bottom: 68, left: 48, right: 50 },
    legend: { top: 7, textStyle: { color: "#667f6d", fontSize: 11 } },
    xAxis: {
      type: "category",
      data: window.months,
      axisTick: { show: false },
      axisLabel: { color: "#87988a", interval: 3 },
      axisLine: { lineStyle: { color: "#dce6dc" } },
    },
    yAxis: [
      {
        ...chartBase.yAxis,
        name: "ONI · °C",
        nameTextStyle: { color: "#809687" },
        axisLabel: { color: "#809687" },
      },
      {
        ...chartBase.yAxis,
        name: "价格指数",
        position: "right",
        nameTextStyle: { color: "#809687" },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "ONI",
        type: "line",
        yAxisIndex: 0,
        symbol: "none",
        lineStyle: { color: "#8ca8ac", width: 2 },
        itemStyle: { color: "#8ca8ac" },
        areaStyle: { color: "#dce8e9", opacity: 0.23 },
        data: window.oni,
        connectNulls: false,
        markLine: {
          symbol: "none",
          lineStyle: { color: "#aab8ac", type: "dashed" },
          label: { formatter: "事后识别起点", color: "#7e9180" },
          data: [{ xAxis: event.start.slice(0, 7) }],
        },
      },
      {
        name: domesticMeta.label,
        type: "line",
        yAxisIndex: 1,
        symbolSize: 4,
        lineStyle: { color: "#11955b", width: 2.5 },
        itemStyle: { color: "#11955b" },
        data: prices.domestic_index,
        connectNulls: false,
      },
      {
        name: foreignMeta?.label || "外盘期货（数据缺失）",
        type: "line",
        yAxisIndex: 1,
        symbolSize: 4,
        lineStyle: { color: "#c49757", width: 2.2 },
        itemStyle: { color: "#c49757" },
        data: prices.overseas_index,
        connectNulls: false,
      },
    ],
  } as EChartsOption;
  return (
    <main className="event-page">
      <div className="page-heading">
        <div>
          <div className="quiet-eyebrow">气候 · 内外盘 · 年度供需</div>
          <h1>历史事件复盘</h1>
          <p>把价格变化，放回当年的供需背景。</p>
        </div>
      </div>
      <div className="event-filters">
        <label>
          厄尔尼诺事件
          <select
            aria-label="厄尔尼诺事件"
            value={event.id}
            onChange={(e) => {
              setEventId(e.target.value);
              setYear(0);
            }}
          >
            {[...data.events].reverse().map((e) => (
              <option key={e.id} value={e.id}>
                {e.start.slice(0, 7)} — {e.end.slice(0, 7)} ·{" "}
                {strengthZh[e.strength] || e.strength}
              </option>
            ))}
          </select>
        </label>
        <label>
          品种
          <select
            aria-label="品种"
            value={crop}
            onChange={(e) => {
              setCrop(e.target.value);
              setDomestic("");
            }}
          >
            {CROPS.map((c) => (
              <option value={c} key={c}>
                {cropNames[c]}
              </option>
            ))}
          </select>
        </label>
        <label>
          内盘主连
          <select
            aria-label="内盘主连"
            value={domesticId}
            onChange={(e) => setDomestic(e.target.value)}
          >
            {data.domestic_options.map((id) => (
              <option key={id} value={id}>
                {data.series[id].label}
              </option>
            ))}
          </select>
        </label>
        <label>
          海外价格
          <select
            aria-label="海外价格"
            value={overseasMode}
            onChange={(e) => setOverseasMode(e.target.value)}
          >
            <option value="futures">外盘期货</option>
            <option value="spot">海外现货参考</option>
          </select>
        </label>
      </div>
      <div className="event-metrics">
        <div>
          <span>事件峰值 ONI</span>
          <strong>
            {show(event.peak, 1)}
            <small> °C</small>
          </strong>
        </div>
        <div>
          <span>内盘首末月均价变化</span>
          <strong
            className={
              (prices.domestic_change || 0) < 0 ? "negative" : "positive"
            }
          >
            {percentage(prices.domestic_change)}
          </strong>
        </div>
        <div>
          <span>
            {overseasMode === "spot" ? "海外现货" : "外盘"}首末月均价变化
          </span>
          <strong
            className={
              (prices.overseas_change || 0) < 0 ? "negative" : "positive"
            }
          >
            {percentage(prices.overseas_change)}
          </strong>
        </div>
      </div>
      <div className="event-layout">
        <section className="event-chart-panel">
          <div className="small-panel-heading">
            <div>
              <span className="quiet-eyebrow">T−12 至 T+12 月</span>
              <h2>{cropNames[crop]} · 内外盘与 ONI</h2>
            </div>
            <span className="chart-unit">
              {prices.base_month
                ? `${prices.base_month} = 100`
                : "共同基期数据缺失"}
            </span>
          </div>
          <Chart
            option={chart}
            height={360}
            label="事件窗口内盘外盘主连价格与ONI"
          />
          <p className="event-timing-note">
            T＝事后识别的首个暖季中心月（{event.start.slice(0, 7)}
            ）。连续5季条件对应期末{" "}
            {event.criterion_met_period_end || "数据缺失"}
            ，不是当时的公告或交易信号。
          </p>
          <div className="event-coverage">
            <span className={prices.domestic_months < 25 ? "missing-note" : ""}>
              内盘：
              {prices.domestic_months === 25
                ? "25 / 25个月有可用观测"
                : prices.domestic_months === 0
                  ? "数据缺失"
                  : `数据缺失或低样本 ${25 - prices.domestic_months} 个月`}
            </span>
            <span className={prices.overseas_months < 25 ? "missing-note" : ""}>
              {overseasMode === "spot" ? "海外现货" : "外盘"}：
              {prices.overseas_months === 25
                ? "25 / 25个月有可用观测"
                : prices.overseas_months === 0
                  ? "数据缺失"
                  : `数据缺失或低样本 ${25 - prices.overseas_months} 个月`}
            </span>
          </div>
          <div className="event-annual-heading">
            <span>窗口内年度产量 · {actualMode ? "真实产量数据库" : "独立供需参考"}</span>
            <small>市场年度 · 百万吨</small>
          </div>
          <div className="event-year-strip">
            {window.years.map((y) => {
              const annual = data.annual[source]?.[String(y)];
              return (
                <button
                  className={annualYear === y ? "active-year" : ""}
                  key={y}
                  onClick={() => setYear(y)}
                >
                  <strong>{yearName(y)}</strong>
                  <span>
                    全球 <b>{show(annual?.Global?.production, 1)}</b>
                  </span>
                  <span>
                    中国 <b>{show(annual?.China?.production, 1)}</b>
                  </span>
                </button>
              );
            })}
          </div>
          <details className="event-method">
            <summary>价格与时间窗口说明</summary>
            {data.notes.map((n) => (
              <p key={n}>{n}</p>
            ))}
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>月份</th>
                    <th>内盘有效日</th>
                    <th>外盘有效日</th>
                    <th>内盘状态</th>
                  </tr>
                </thead>
                <tbody>
                  {window.months.map((month, i) => (
                    <tr key={month}>
                      <td>{month}</td>
                      <td>{prices.domestic_quality?.[i]?.n_obs ?? "—"}</td>
                      <td>{prices.overseas_quality?.[i]?.n_obs ?? "—"}</td>
                      <td>
                        {{
                          usable: "通过最低筛选",
                          thin_sample: "观测日不足",
                          thin_volume: "成交不足",
                          incomplete_month: "月份未完成",
                          no_observations: "数据缺失",
                        }[
                          prices.domestic_quality?.[i]?.reason ||
                            "no_observations"
                        ] || "待核对"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              展示的是窗口首末两个月均价之比，只有两端均有合格样本才计算；不等于首末日收益或含换月成本的投资收益。
              {crop === "sugar"
                ? "内盘白糖与外盘原糖规格不同。"
                : crop === "rice"
                  ? "内盘为粳米；现货参考为泰国米，规格不同。"
                  : crop === "soybean"
                    ? "豆二主要反映进口与压榨链，豆一更贴近国产非转基因大豆；中国产量并非豆二价格的唯一供给变量。"
                    : ""}
            </p>
            <p>
              内盘来源：
              <a
                href={domesticMeta.source_url || "#"}
                target="_blank"
                rel="noreferrer"
              >
                新浪期货 ↗
              </a>{" "}
              · 覆盖 {day(domesticMeta.first_date)} 至{" "}
              {day(domesticMeta.last_date)}
            </p>
            <p>
              海外来源：
              {foreignMeta ? (
                <a
                  href={foreignMeta.source_url || "#"}
                  target="_blank"
                  rel="noreferrer"
                >
                  {foreignMeta.label} ↗
                </a>
              ) : (
                "数据缺失"
              )}{" "}
              · 观测数据来自NOAA ONI。
            </p>
          </details>
        </section>
        <aside className="event-balance-panel">
          <div className="small-panel-heading">
            <div>
              <span className="quiet-eyebrow">{actualMode ? "真实产量" : "年度供需"}</span>
              <h2>{yearName(annualYear)} 市场年度</h2>
            </div>
          </div>
          <div className="balance-controls">
            <label>
              数据源
              <select
                aria-label="年度数据源"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                <option value="actual_production">真实产量</option>
                <option value="usda_psd">PSD 供需参考</option>
                <option value="usda_wasde">WASDE 供需参考</option>
              </select>
            </label>
            <label>
              年度
              <select
                aria-label="供需年度"
                value={annualYear}
                onChange={(e) => setYear(+e.target.value)}
              >
                {window.years.map((y) => (
                  <option key={y} value={y}>
                    {yearName(y)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <table className="balance-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>全球</th>
                <th>中国</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>产量</td>
                <td>{show(world?.production)}</td>
                <td>{show(china?.production)}</td>
              </tr>
              {!actualMode && <>
              <tr>
                <td>期末库存</td>
                <td>{show(world?.ending_stocks)}</td>
                <td>{show(china?.ending_stocks)}</td>
              </tr>
              <tr>
                <td>消费 / 用量</td>
                <td>{show(world?.consumption)}</td>
                <td>{show(china?.consumption)}</td>
              </tr>
              <tr className="balance-highlight">
                <td>库存消费比</td>
                <td>
                  {world?.stocks_to_use == null
                    ? "数据缺失"
                    : num(world.stocks_to_use, 1) + "%"}
                </td>
                <td>
                  {china?.stocks_to_use == null
                    ? "数据缺失"
                    : num(china.stocks_to_use, 1) + "%"}
                </td>
              </tr>
              </>}
            </tbody>
          </table>
          <p className="balance-unit">
            {actualMode ? '产量：百万吨。仅展示真实产量数据库中已有的官方实产；未覆盖的国家或年份显示 N/A，不使用预测或历史估计补齐。' : <>
              产量与库存：百万吨<br />库存消费比＝期末库存 ÷ 表列消费或用量<br />
              {source === 'usda_wasde' && ['corn', 'wheat', 'rice'].includes(crop)
                ? 'WASDE全球用量含进出口差额调整，不能与PSD国家消费加总直接拼接。'
                : 'PSD全球分母为各国国内消费合计；糖为国内总消耗。'}
            </>}
          </p>
          <div className="balance-note">
            <span>{actualMode ? '真实产量数据库 · 官方实产' : `${sources[source]} · 独立供需参考`}</span>
            {actualMode ? <>
              <p>全球：{world?.production == null ? '暂无已入库的完整真实产量' : sources[world.source || '']}</p>
              <p>中国：{china?.production == null ? '暂无真实产量' : sources[china.source || '']}</p>
              {china?.source_url && <a href={china.source_url} target="_blank" rel="noreferrer">中国产量原始来源 ↗</a>}
            </> : <p>{world?.derived_global ? 'PSD全球为国家合计，已剔除欧盟成员重复。' : 'WASDE全球采用报告World行。'}此表保留原机构供需口径，产量可能与真实产量数据库不同。</p>}
            <p>{actualMode ? '真实产量会随官方终值修订更新；各国市场年度起止不同，未统一换算。' : '年度值为当前归档的修订后历史估计或预测，不代表事件当时市场已知版本。'}</p>
            <p>各国市场年度起止不同；气候与价格仅作背景对照，不据此推断因果。</p>
          </div>
          {!actualMode && (world || china) && (
            <a
              className="source-inline"
              href={world?.source_url || china?.source_url || undefined}
              target="_blank"
              rel="noreferrer"
            >
              查看原始来源 ↗
            </a>
          )}
        </aside>
      </div>
    </main>
  );
}
