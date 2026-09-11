import { useEffect, useState } from "react";
export const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
export const CROPS = ["wheat", "corn", "soybean", "rice", "sugar"];
export const strengthZh: Record<string, string> = {
  "Very strong": "极强",
  Strong: "强",
  Moderate: "中等",
  Weak: "弱",
  Neutral: "中性",
  "La Niña range": "拉尼娜区间",
};
export const names: Record<string, string> = {
  wheat: "Wheat · 小麦",
  corn: "Corn · 玉米",
  soybean: "Soybean · 大豆",
  rice: "Rice · 水稻",
  sugar: "Sugar · 糖",
};
export const sources: Record<string, string> = {
  usda_psd: "USDA PSD",
  usda_wasde: "USDA WASDE",
  local_composite: "本土产量组合",
  casde: "中国 CASDE",
  aafc: "加拿大 AAFC",
  conab: "巴西 CONAB",
  abares: "澳大利亚 ABARES",
  dafw: "印度 DA&FW",
  cec: "南非 CEC",
  ec: "欧盟 EC",
  bcr: "阿根廷 BCR",
  uga: "乌克兰 UGA",
  us_nass: "美国 NASS",
  uk_defra: "英国 DEFRA",
  mx_siap: "墨西哥 SIAP",
  jp_maff: "日本 MAFF",
  ph_psa: "菲律宾 PSA",
  my_dosm: "马来西亚 DOSM",
  pk_pbs: "巴基斯坦 PBS",
  tw_afa: "台湾 AFA",
  kz_bns: "哈萨克斯坦 BNS",
  cropwatch: "CropWatch",
  china_outlook: "中国农业展望",
  nbs: "国家统计局",
  faostat: "FAOSTAT",
  worldbank: "World Bank",
  china_prices: "NBS 国内现货",
};
export type Status = "actual" | "forecast" | "estimate";
export type Production = {
  country: string;
  source_country?: string;
  region: string;
  target_year: number;
  year_basis: string;
  commodity_basis: string;
  value: number;
  source: string;
  status: Status;
  publication_date: string | null;
  available_date: string;
  download_timestamp: string;
  source_url: string;
  methodology: string;
  document_id: string;
  is_primary?: boolean;
  selection_blocked?: boolean;
  missing_members?: string[] | null;
  policy_version?: string | null;
  member_count?: number | null;
  component_records?:
    | { record_id: string; country: string; value: number }[]
    | null;
  comparisons?: Record<
    string,
    { previous: Production | null; yoy: number | null; reason: string }
  >;
};
export type Geography = {
  country: string;
  map_name: string | null;
  label: string | null;
  subregion: string | null;
  level: "global" | "country" | "region";
  parent: string | null;
  members?: string[];
};
export const comparisonReason: Record<string, string> = {
  no_compatible_prior_year: "缺少同口径上年数据",
  zero_prior_year: "上年产量为 0，同比不适用",
  no_observation_for_selection: "该年度/来源暂无记录",
};
export type History = {
  country: string;
  region: string;
  source: string;
  commodity_basis: string;
  year_basis: string;
  status: Status;
  year: number;
  production: number | null;
  yield_value: number | null;
  production_yoy: number | null;
  yield_yoy: number | null;
  yield_anomaly: number | null;
  yield_anomaly_pct: number | null;
  production_gap: number | null;
  available_date: string;
};
export type Price = {
  date: string;
  value: number;
  market: string;
  symbol: string;
  currency: string;
  unit: string;
  source: string;
  price_type: string;
  available_date: string;
  source_url: string;
  download_timestamp: string;
};
export type Source = {
  source: string;
  name: string;
  url: string;
  freq: string;
  status: string;
  error: string | null;
  last_checked: string | null;
  last_success: string | null;
  last_publication_date: string | null;
  latest_observation_date: string | null;
  rows_ingested: number;
  age_days: number | null;
  stale_after_days: number;
};
export type PriceResearch = {
  monthly: Record<string, Record<string, number>>;
  ranges: Record<
    string,
    {
      paired_months: number;
      return_pairs: number;
      index_base: string | null;
      correlation: number | null;
      rolling: { month: string; n: number; value: number | null }[];
      leadlag: { lag: number; n: number; correlation: number | null }[];
    }
  >;
  methodology: string;
};
export type CropData = {
  crop: string;
  asof: string;
  generated_at: string;
  production: Production[];
  history: History[];
  supply: (Production & { metric: string })[];
  prices: Price[];
  price_research: PriceResearch;
  sources: Source[];
  regions: string[];
  geographies: Geography[];
  research_units: string[];
  policy_version: string;
  limitations: string[];
};
export type ClimatePoint = {
  date: string;
  value: number;
  season: string;
  available_date: string;
  source_url: string;
  download_timestamp: string;
};
export type ClimateCurrent = ClimatePoint & {
  strength: string;
  percentile: number;
  chg_1m: number;
  chg_3m: number;
  warm_seasons: number;
  sample_size: number;
};
export type Event = {
  id: string;
  start: string;
  end: string;
  peak: number;
  peak_date: string;
  seasons: number;
  strength: string;
  first_season_period_end?: string;
  criterion_met_period_end?: string;
  announcement_date?: string | null;
};
export type Climate = {
  index_version?: string;
  series: Record<string, ClimatePoint[]>;
  current: Record<string, ClimateCurrent>;
  events: Event[];
  methodology: string;
  roni_url: string;
};
export type Overview = {
  updated: string;
  crops: Record<string, Production | null>;
  climate: Record<string, ClimateCurrent>;
  sources: Source[];
};
export function useData<T>(name: string) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError("");
    fetch(`${base}/api/${name}.json`, {
      signal: controller.signal,
      cache: "no-cache",
    })
      .then((r) => {
        if (!r.ok) throw Error(`数据请求失败 (${r.status})`);
        return r.json();
      })
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(String(e.message));
      });
    return () => controller.abort();
  }, [name]);
  return { data, error };
}
export function num(v: number | null | undefined, d = 2) {
  return v == null || !Number.isFinite(v)
    ? "N/A"
    : v.toLocaleString("en-US", {
        maximumFractionDigits: d,
        minimumFractionDigits: d,
      });
}
export function pct(v: number | null | undefined, d = 1) {
  return v == null || !Number.isFinite(v)
    ? "N/A"
    : `${v > 0 ? "+" : ""}${num(v, d)}%`;
}
export const day = (v: string | null | undefined) => v?.slice(0, 10) || "N/A";
export const yearLabel = (r: Production) =>
  r.year_basis === "marketing_year"
    ? `${r.target_year}/${String(r.target_year + 1).slice(2)} MY`
    : `${r.target_year} CY`;
export const basisLabel: Record<string, string> = {
  grain: "Grain",
  oilseed: "Oilseed",
  milled: "Milled · 精米",
  paddy: "Paddy · 稻谷",
  paddy_early: "Early paddy · 早稻",
  paddy_semi_late: "Semi-late paddy · 半晚稻",
  winter_wheat: "Winter wheat · 冬小麦",
  centrifugal_raw_value: "Raw-value sugar",
  sugar_unspecified: "食糖 · 折算口径未注明",
};
export function sameDefinition(a: Production, b: Production) {
  return (
    a.commodity_basis === b.commodity_basis &&
    a.year_basis === b.year_basis &&
    a.region === b.region &&
    a.country === b.country
  );
}
export function latest(rows: Production[]): Production | undefined {
  return [...rows]
    .sort(
      (a, b) =>
        day(a.available_date).localeCompare(day(b.available_date)) ||
        a.download_timestamp.localeCompare(b.download_timestamp) ||
        (a.document_id || "").localeCompare(b.document_id || ""),
    )
    .at(-1);
}
export function preferred(
  rows: Production[],
  country: string,
  source = "auto",
) {
  rows = rows.filter((r) => !r.selection_blocked);
  if (source !== "auto") rows = rows.filter((r) => r.source === source);
  const whole = rows.filter(
    (r) =>
      !["paddy_early", "paddy_semi_late", "winter_wheat"].includes(
        r.commodity_basis,
      ),
  );
  rows = whole.length ? whole : rows;
  if (source !== "auto") return latest(rows);
  return latest(rows.filter((r) => r.is_primary === true));
}
export function revision(rows: Production[], r: Production, months: number) {
  const anchor = new Date(day(r.available_date) + "T00:00:00Z");
  anchor.setUTCMonth(anchor.getUTCMonth() - months);
  const old = latest(
    rows.filter(
      (p) =>
        p.source === r.source &&
        sameDefinition(p, r) &&
        p.target_year === r.target_year &&
        p.status === r.status &&
        day(p.available_date) <= day(anchor.toISOString()),
    ),
  );
  if (!old || r.value === null) return null;
  const gap =
    (anchor.getTime() - new Date(day(old.available_date)).getTime()) / 86400000;
  return gap > 45 || old.value === 0 ? null : (r.value / old.value - 1) * 100;
}
