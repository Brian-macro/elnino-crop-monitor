"use client";
import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as echarts from "echarts";
import Chart, { chartBase } from "./Chart";
import { Loading, Provenance, SourceState } from "./Common";
import {
  useData,
  CropData,
  Production,
  Status,
  names,
  CROPS,
  sources,
  preferred,
  latest,
  sameDefinition,
  revision,
  num,
  pct,
  day,
  yearLabel,
  basisLabel,
  base,
  comparisonReason,
} from "@/lib/data";
import { zhCountry } from "@/lib/labels";
import Revision from "./Revision";
const mapNames: Record<string, string> = {
  "United States of America": "United States",
  "Russian Federation": "Russia",
  "Viet Nam": "Vietnam",
  Myanmar: "Burma",
  "South Korea": "Korea, South",
  "North Korea": "Korea, North",
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
const today = () => new Date().toISOString().slice(0, 10);
export default function Outlook({
  initialCrop = "wheat",
  compact = false,
  navigateCrops = false,
}: {
  initialCrop?: string;
  compact?: boolean;
  navigateCrops?: boolean;
}) {
  const router = useRouter();
  const [crop, setCrop] = useState(initialCrop),
    [year, setYear] = useState(new Date().getFullYear()),
    [source, setSource] = useState("auto"),
    [status, setStatus] = useState<Status>("forecast"),
    [asof, setAsof] = useState(today),
    [country, setCountry] = useState("Global"),
    [region, setRegion] = useState(""),
    [baseline, setBaseline] = useState("reported"),
    [subregion, setSubregion] = useState("all"),
    [view, setView] = useState("regions"),
    [definition, setDefinition] = useState("auto"),
    [mapReady, setMapReady] = useState(false),
    [mapError, setMapError] = useState("");
  const { data, error } = useData<CropData>(crop);
  useEffect(() => {
    if (!data) return;
    if (!data.geographies.some((g) => g.country === country))
      choose(
        data.research_units.includes("Southeast Asia") &&
          subregion === "Southeast Asia"
          ? "Southeast Asia"
          : "Global",
      );
  }, [data, country, subregion]);
  useEffect(() => {
    setCrop(initialCrop);
    setRegion("");
    setDefinition("auto");
  }, [initialCrop]);
  useEffect(() => {
    if (navigateCrops) return;
    const query = new URLSearchParams(window.location.search);
    const queryCrop = query.get("crop"),
      focus = query.get("focus");
    if (queryCrop && CROPS.includes(queryCrop)) setCrop(queryCrop);
    if (focus && ["East Asia", "Southeast Asia"].includes(focus)) {
      setSubregion(focus);
      if (focus === "Southeast Asia") setCountry(focus);
    }
  }, [navigateCrops]);
  useEffect(() => {
    let alive = true;
    fetch(`${base}/world.json`)
      .then((r) => {
        if (!r.ok) throw Error("地图文件不可用");
        return r.json();
      })
      .then((g) => {
        echarts.registerMap("world", g);
        if (alive) setMapReady(true);
      })
      .catch((e) => {
        if (alive) setMapError(e.message);
      });
    return () => {
      alive = false;
    };
  }, []);
  const known = useMemo(
    () => data?.production.filter((r) => day(r.available_date) <= asof) || [],
    [data, asof],
  );
  const candidates = known.filter(
    (r) => r.target_year === year && r.status === status && !r.region,
  );
  const countries = [
    ...new Set([
      ...(data?.geographies || []).map((g) => g.country),
      ...known.map((r) => r.country),
    ]),
  ].sort((a, b) =>
    a === "Global" ? -1 : b === "Global" ? 1 : a.localeCompare(b),
  );
  const choices = known.filter(
    (r) =>
      r.country === country &&
      r.region === region &&
      r.target_year === year &&
      r.status === status &&
      (source === "auto" || r.source === source),
  );
  const defs = [
    ...new Set(choices.map((r) => `${r.year_basis}|${r.commodity_basis}`)),
  ];
  const selected = preferred(
    choices.filter(
      (r) =>
        definition === "auto" ||
        `${r.year_basis}|${r.commodity_basis}` === definition,
    ),
    country,
    source,
  );
  const prevFor = (r: Production, kind = baseline) =>
    r.comparisons?.[kind]?.previous || undefined;
  const geographicRows = countries.filter(
    (c) =>
      (subregion === "all" ||
        data?.geographies?.find((g) => g.country === c)?.subregion ===
          subregion) &&
      (view === "regions"
        ? data?.research_units?.includes(c)
        : data?.geographies?.find((g) => g.country === c)?.level !== "region"),
  );
  const selectedGeo = data?.geographies.find((g) => g.country === country);
  const parentGeo = data?.geographies.find(
    (g) => g.country === selectedGeo?.parent,
  );
  const basket = selectedGeo?.level === "region" ? selectedGeo : parentGeo;
  const rows = countries
    .filter((c) => c !== "Global")
    .map((c) => {
      const row = preferred(
        candidates.filter((r) => r.country === c),
        c,
        source,
      );
      if (!row) return null;
      const previous = prevFor(row);
      const yoy = row.comparisons?.[baseline]?.yoy ?? null;
      return {
        row,
        previous,
        yoy,
        rev: status === "forecast" ? revision(known, row, 1) : null,
      };
    })
    .filter((r): r is NonNullable<typeof r> => r !== null)
    .sort((a, b) => b.row.value - a.row.value);
  const mapOption = useMemo(() => {
    if (!mapReady) return null;
    const canonicalMapName = (name: string) =>
      data?.geographies?.find((g) => g.map_name === name)?.country ||
      mapNames[name] ||
      name;
    const get = (name: string) => {
      const canonical = canonicalMapName(name);
      const parent = data?.geographies.find(
        (g) => g.country === canonical,
      )?.parent;
      return (
        rows.find(
          (r) =>
            r.row.country ===
            (view === "regions" && parent ? parent : canonical),
        ) ||
        (eu.includes(name)
          ? rows.find((r) => r.row.country === "European Union")
          : undefined)
      );
    };
    const geo = echarts.getMap("world")?.geoJSON as
      | { features: { properties: { name: string } }[] }
      | undefined;
    const cells =
      geo?.features.map((f) => {
        const item = get(f.properties.name);
        return {
          name: f.properties.name,
          value: item?.yoy ?? null,
          itemStyle: item?.yoy == null ? { areaColor: "#eef2ef" } : undefined,
        };
      }) || [];
    return {
      backgroundColor: "transparent",
      tooltip: {
        confine: true,
        backgroundColor: "#ffffff",
        borderColor: "#dce6de",
        textStyle: { color: "#254b35" },
        formatter: (p: unknown) => {
          const name = (p as { name: string }).name;
          const r = get(name);
          return r
            ? `${zhCountry(r.row.country)}${eu.includes(name) ? " · EU aggregate" : ""}<br/>${num(r.row.value)} Mt · ${r.row.status}<br/>YoY ${pct(r.yoy)}${r.previous ? ` vs ${r.previous.status} (${r.previous.target_year})` : ` · ${comparisonReason[r.row.comparisons?.[baseline]?.reason || "no_compatible_prior_year"]}`}<br/>${yearLabel(r.row)} · ${basisLabel[r.row.commodity_basis] || r.row.commodity_basis}<br/>${sources[r.row.source]} · available ${day(r.row.available_date)}`
            : `${name}<br/>N/A · 无兼容数据`;
        },
      },
      visualMap: {
        min: -20,
        max: 20,
        orient: "horizontal",
        left: 20,
        bottom: 8,
        itemWidth: 12,
        itemHeight: 170,
        text: ["增产", "减产"],
        textStyle: { color: "#788a7c" },
        inRange: { color: ["#cf846e", "#dbe6df", "#16a366"] },
        calculable: true,
      },
      series: [
        {
          type: "map",
          map: "world",
          roam: true,
          zoom: subregion === "all" ? 1.1 : 2.0,
          center:
            subregion === "East Asia"
              ? [112, 34]
              : subregion === "Southeast Asia"
                ? [111, 10]
                : [12, 12],
          name: "Production YoY",
          data: cells,
          itemStyle: {
            borderColor: "#ffffff",
            borderWidth: 0.6,
            areaColor: "#eef2ef",
          },
          emphasis: {
            label: { show: false },
            itemStyle: { borderColor: "#168d52", borderWidth: 1.5 },
          },
          select: { disabled: true },
        },
      ],
    };
  }, [mapReady, rows, baseline, data, subregion, view]);
  function choose(c: string) {
    setCountry(c);
    setRegion("");
    setDefinition("auto");
  }
  const actual = selected ? prevFor(selected, "actual") : undefined,
    previous = selected ? prevFor(selected) : undefined;
  const five = selected
    ? known.filter(
        (r) =>
          sameDefinition(r, selected) &&
          r.source === selected.source &&
          r.status === "estimate" &&
          r.target_year >= year - 5 &&
          r.target_year < year,
      )
    : [];
  const fiveYears = [
    ...new Map(
      five
        .sort((a, b) => a.available_date.localeCompare(b.available_date))
        .map((r) => [r.target_year, r]),
    ).values(),
  ];
  const average =
    fiveYears.length === 5
      ? fiveYears.reduce((s, r) => s + r.value, 0) / 5
      : null;
  const regions = [
    ...new Set(
      known
        .filter(
          (r) =>
            r.country === country &&
            r.target_year === year &&
            r.status === status,
        )
        .map((r) => r.region)
        .filter(Boolean),
    ),
  ].sort();
  const movers = [...rows]
    .filter((r) => r.rev !== null && r.rev !== 0)
    .sort((a, b) => Math.abs(b.rev!) - Math.abs(a.rev!));
  if (!data) return <Loading error={error} />;
  return (
    <section className="outlook">
      <div className="section-heading">
        <div>
          <div className="eyebrow">PRODUCTION / SUPPLY OUTLOOK</div>
          <h2>Global Crop Production Outlook</h2>
        </div>
        <span className="muted">Global / Country / Region</span>
      </div>
      <div className="toolbar crop-tabs" role="group" aria-label="作物选择">
        {CROPS.map((c) => (
          <button
            key={c}
            className={crop === c ? "active" : ""}
            onClick={() => {
              if (navigateCrops) {
                router.push(`/${c}/`);
                return;
              }
              setCrop(c);
              setRegion("");
              setDefinition("auto");
            }}
          >
            {names[c]}
          </button>
        ))}
      </div>
      <div className="toolbar filters">
        <label>
          Target Year
          <select value={year} onChange={(e) => setYear(+e.target.value)}>
            {[
              ...new Set([
                2025,
                2026,
                2027,
                2035,
                ...known.map((r) => r.target_year),
              ]),
            ]
              .sort((a, b) => b - a)
              .map((y) => (
                <option key={y}>{y}</option>
              ))}
          </select>
        </label>
        <label>
          Source
          <select
            value={source}
            onChange={(e) => {
              setSource(e.target.value);
              setDefinition("auto");
            }}
          >
            <option value="auto">Primary series · 策略主来源</option>
            {[
              "usda_wasde",
              "usda_psd",
              "cropwatch",
              "china_outlook",
              "nbs",
            ].map((s) => (
              <option value={s} key={s}>
                {sources[s]} · 指定来源
              </option>
            ))}
          </select>
        </label>
        <label>
          Data Type
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as Status);
              setDefinition("auto");
            }}
          >
            <option value="forecast">Forecast · 预测</option>
            <option value="actual">Actual · 官方实产</option>
            <option value="estimate">Estimate · 历史估计</option>
          </select>
        </label>
        <label>
          As of · 预测可得日期
          <input
            type="date"
            max={today()}
            value={asof}
            onChange={(e) => e.target.value && setAsof(e.target.value)}
          />
        </label>
        <label>
          YoY 对比基准
          <select
            value={baseline}
            onChange={(e) => setBaseline(e.target.value)}
          >
            <option value="reported">上年同源报告值 · 保留原分类</option>
            <option value="estimate">上年同源 Estimate</option>
            <option value="actual">上年官方 Actual</option>
          </select>
        </label>
        <label>
          Geographic Focus
          <select
            value={subregion}
            onChange={(e) => setSubregion(e.target.value)}
          >
            <option value="all">Global · 全球</option>
            <option value="East Asia">East Asia · 东亚</option>
            <option value="Southeast Asia">Southeast Asia · 东南亚</option>
          </select>
        </label>
      </div>
      <div className="toolbar">
        <div className="segmented">
          <button
            className={view === "regions" ? "active" : ""}
            onClick={() => setView("regions")}
          >
            研究地区
          </button>
          <button
            className={view === "countries" ? "active" : ""}
            onClick={() => setView("countries")}
          >
            成员国家
          </button>
        </div>
        <Link href="/methodology/#source-policy" className="muted">
          来源与数据拼接方案 ↗
        </Link>
      </div>
      <div className="panel-note">
        当前范围 {geographicRows.filter((c) => c !== "Global").length}{" "}
        个国家/地区 · 有产量{" "}
        {rows.filter((r) => geographicRows.includes(r.row.country)).length} ·
        可计算同比{" "}
        {
          rows.filter(
            (r) => geographicRows.includes(r.row.country) && r.yoy !== null,
          ).length
        }
        。
        {baseline === "reported"
          ? "同比基准按同一来源、同一作物口径取上年报告值，优先同一报告；上年数据分类逐项标注。"
          : ""}
      </div>
      <div className="map-layout panel">
        <div className="map-area">
          {mapOption ? (
            <Chart
              option={mapOption as echarts.EChartsOption}
              height={430}
              onClick={(name) => {
                const canonical =
                  data.geographies?.find((g) => g.map_name === name)?.country ||
                  mapNames[name] ||
                  (eu.includes(name) ? "European Union" : name);
                const geo = data.geographies.find(
                  (g) => g.country === canonical,
                );
                if (geo)
                  choose(
                    view === "regions" && geo.parent ? geo.parent : canonical,
                  );
              }}
              label="世界作物产量同比地图；下方提供国家数据表"
            />
          ) : (
            <Loading error={mapError} />
          )}
          <div className="map-note">
            深灰 = N/A · 中灰 = 0% · MY 与 CY
            逐国标记；精米、稻谷与季节作物分别比较。地区视图中东南亚成员统一着色代表地区合计，欧盟为
            EU 合计。
          </div>
        </div>
        <aside className="country-detail">
          <div className="eyebrow">GEOGRAPHIC DRILLDOWN</div>
          <label className="sr-only" htmlFor="countrySelect">
            研究地区 / 国家
          </label>
          <select
            id="countrySelect"
            value={country}
            onChange={(e) => choose(e.target.value)}
          >
            {[...new Set([...geographicRows, country])].map((c) => (
              <option key={c} value={c}>
                {c === "Global" ? "Global · 全球" : `${zhCountry(c)} / ${c}`}
              </option>
            ))}
          </select>
          <div className="breadcrumb">
            <button onClick={() => choose("Global")}>Global</button>
            {parentGeo && (
              <>
                {" "}
                /{" "}
                <button onClick={() => choose(parentGeo.country)}>
                  {zhCountry(parentGeo.country)}
                </button>
              </>
            )}
            {country !== "Global" && (
              <>
                {" "}
                /{" "}
                <button onClick={() => setRegion("")}>
                  {zhCountry(country)}
                </button>
              </>
            )}
            {region && ` / ${region}`}
          </div>
          {basket && (
            <label>
              Member Country
              <select
                value={selectedGeo?.level === "region" ? "" : country}
                onChange={(e) => {
                  choose(e.target.value || basket.country);
                  setSource("auto");
                }}
              >
                <option value="">{zhCountry(basket.country)} · 地区合计</option>
                {basket.members?.map((c) => (
                  <option key={c} value={c}>
                    {zhCountry(c)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {selectedGeo?.level === "region" && (
            <p className="panel-note">
              USDA PSD · {selectedGeo.members?.length} 个固定成员 ·
              同一报告求和。{selectedGeo.members?.map(zhCountry).join("、")}
            </p>
          )}
          <label>
            Region / Province
            <select
              value={region}
              onChange={(e) => {
                setRegion(e.target.value);
                setDefinition("auto");
              }}
            >
              <option value="">National / Global</option>
              {regions.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </label>
          {!regions.length && (
            <small className="muted">Region: N/A · 暂无已验证省级记录</small>
          )}
          {defs.length > 0 && (
            <label>
              口径
              <select
                value={definition}
                onChange={(e) => setDefinition(e.target.value)}
              >
                <option value="auto">优先可用口径</option>
                {defs.map((d) => (
                  <option key={d} value={d}>
                    {d
                      .replace("marketing_year", "MY")
                      .replace("calendar_year", "CY")}
                  </option>
                ))}
              </select>
            </label>
          )}
          <SourceState
            source={data.sources.find((s) => s.source === selected?.source)}
          />
          <div className="big-number">
            {num(selected?.value)}
            <small> Mt</small>
          </div>
          <div className="muted">
            {selected
              ? `${status.toUpperCase()} · ${yearLabel(selected)} · ${basisLabel[selected.commodity_basis] || selected.commodity_basis}`
              : "没有满足所选时点与口径的数据"}
          </div>
          <dl className="stats-list">
            <div>
              <dt>Previous Year Actual</dt>
              <dd>{num(actual?.value)}</dd>
            </div>
            <div>
              <dt>
                上年{" "}
                {previous?.status ||
                  (baseline === "reported" ? "报告值" : baseline)}
              </dt>
              <dd>{num(previous?.value)}</dd>
            </div>
            <div>
              <dt>Production YoY</dt>
              <dd>{pct(selected?.comparisons?.[baseline]?.yoy)}</dd>
            </div>
            <div>
              <dt>5Y mean · 同源历史估计</dt>
              <dd>{num(average)}</dd>
            </div>
            <div>
              <dt>1M forecast revision</dt>
              <dd>
                {pct(
                  selected && status === "forecast"
                    ? revision(known, selected, 1)
                    : null,
                )}
              </dd>
            </div>
          </dl>
          {selected && selected.comparisons?.[baseline]?.yoy == null && (
            <p className="panel-note">
              {
                comparisonReason[
                  selected.comparisons?.[baseline]?.reason ||
                    "no_compatible_prior_year"
                ]
              }
            </p>
          )}
          {previous && (
            <div className="provenance">
              同比基准：{previous.target_year} {previous.status} ·{" "}
              <a href={previous.source_url} target="_blank" rel="noreferrer">
                {sources[previous.source]} ↗
              </a>{" "}
              · Available {day(previous.available_date)}
            </div>
          )}
          <Provenance row={selected} />
        </aside>
      </div>
      {selected && (
        <details className="definition-note">
          <summary>查看当前数字的计算口径与来源说明</summary>
          <p>{selected.methodology}</p>
          <p>
            Available: {day(selected.available_date)}；Publication:{" "}
            {day(selected.publication_date)}。Global 的 PSD
            数据是全部来源国家加总，WASDE 数据为报告中的 World
            行；两者不作为独立机构计算共识。
          </p>
        </details>
      )}
      <div className="two-col research-row">
        <div className="panel">
          <div className="panel-head">
            <h3>Forecast Revision</h3>
            <span>
              {zhCountry(country)} · {year}
            </span>
          </div>
          <Revision rows={known} selected={selected} />
        </div>
        <div className="panel">
          <div className="panel-head">
            <h3>正在上调 / 下调</h3>
            <span>同目标年 · 1M revision</span>
          </div>
          {movers.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Country</th>
                    <th>Forecast (Mt)</th>
                    <th>1M 修正</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {movers.slice(0, 8).map((r) => (
                    <tr
                      key={r.row.country}
                      onClick={() => choose(r.row.country)}
                    >
                      <td>
                        <button className="text-button">
                          {zhCountry(r.row.country)}
                        </button>
                      </td>
                      <td>{num(r.row.value)}</td>
                      <td className={r.rev! < 0 ? "negative" : "positive"}>
                        {pct(r.rev)}
                      </td>
                      <td>{sources[r.row.source]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty">N/A · 尚无两个可比的月度预测版本</div>
          )}
          <div className="panel-note">
            修正比较同一机构、同一目标年度、同一口径；不把同比增减当成预测上调或下调。
          </div>
        </div>
      </div>
      {!compact && (
        <div className="panel">
          <div className="panel-head">
            <h3>
              {view === "regions"
                ? "Production by Research Region"
                : "Member Country Production"}
            </h3>
            <span>
              {
                rows.filter((r) => geographicRows.includes(r.row.country))
                  .length
              }{" "}
              个已覆盖国家 / 地区
            </span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Country</th>
                  <th>{status} (Mt)</th>
                  <th>上年产量 / 分类</th>
                  <th>YoY</th>
                  <th>1M Revision</th>
                  <th>Year / Basis</th>
                  <th>Source · Available</th>
                </tr>
              </thead>
              <tbody>
                {rows
                  .filter((r) => geographicRows.includes(r.row.country))
                  .map(({ row, previous, yoy, rev }) => (
                    <tr key={row.country} onClick={() => choose(row.country)}>
                      <td>
                        <button className="text-button">
                          {zhCountry(row.country)}
                        </button>
                      </td>
                      <td>{num(row.value)}</td>
                      <td>
                        {num(previous?.value)}{" "}
                        <small className="muted">{previous?.status}</small>
                      </td>
                      <td
                        title={
                          comparisonReason[
                            row.comparisons?.[baseline]?.reason || ""
                          ]
                        }
                        className={
                          yoy == null
                            ? "muted"
                            : yoy < 0
                              ? "negative"
                              : "positive"
                        }
                      >
                        {pct(yoy)}
                      </td>
                      <td>{pct(rev)}</td>
                      <td>
                        {yearLabel(row)} /{" "}
                        {basisLabel[row.commodity_basis] || row.commodity_basis}
                      </td>
                      <td>
                        <a
                          href={row.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {sources[row.source]} ↗
                        </a>{" "}
                        · {day(row.available_date)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {!rows.some((r) => geographicRows.includes(r.row.country)) && (
              <div className="empty">N/A · 没有满足筛选的数据</div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
