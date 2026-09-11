"use client";
import { useState } from "react";
import { useData, CROPS, names, sources, base, num } from "@/lib/data";
import { zhCountry } from "@/lib/labels";
import { Loading } from "./Common";

type Selection = {
  source: string; adopted_national: boolean; source_url: string | null;
  reason: string | null; comparison_reason: string | null; source_target_year: number;
};
type Coverage = {
  generated_at: string; policy_version: string;
  rows: {
    country: string; crop: string; configured_source: string | null;
    authority: string | null; authority_url: string | null; note: string | null; access_error: string | null;
    available_years: number[];
    latest_national: { target_year: number; year_basis: string; commodity_basis: string; status: string; value: number; source_url: string } | null;
    years: Record<string, Selection>;
  }[];
};
const reasons: Record<string, string> = {
  missing_local_target_year: "本国库尚无该目标年的同口径记录",
  national_source_not_integrated: "本国数据库尚未完成接入",
  paddy_to_milled_crosswalk_unverified: "稻谷转精米定义未验证，使用 PSD 精米",
  definition_unverified: "本国数据产品或年度定义尚未核验",
  refined_to_raw_crosswalk_unverified: "精制糖转原糖值未经核验，保留 PSD 原糖口径",
  agricultural_to_marketing_year_unverified: "本国农业年与市场年度对应关系尚未核验",
  calendar_to_marketing_year_unverified: "自然年总量与市场年度对应关系尚未核验",
};
const basis: Record<string, string> = { grain: "谷物", oilseed: "油籽", paddy: "稻谷", milled: "精米", centrifugal_raw_value: "原糖值" };

export default function SourcePolicy() {
  const { data, error } = useData<Coverage>("national_coverage");
  const [crop, setCrop] = useState("corn");
  const [selectedYear, setYear] = useState("");
  if (!data) return <Loading error={error} />;
  const rows = data.rows.filter(r => r.crop === crop);
  const years = [...new Set(rows.flatMap(r => Object.keys(r.years)))].sort((a,b) => Number(b)-Number(a));
  const year = years.includes(selectedYear) ? selectedYear : years[0];
  const adopted = rows.filter(r => r.years[year]?.adopted_national).length;
  return (
    <section id="source-policy">
      <h2>各国权威数据库与实际采用</h2>
      <p>产量优先采用本国政府统计、农业主管部门或权威行业机构数据。美国 USDA 属于美国本国来源；其他国家的 USDA 数据仅作缺口补充。目标年和产品口径必须匹配，不能把上一季产量移作下一季预测。</p>
      <p>本年本国数据存在即采用；缺少同源上年数据时，仅同比留空。全球与地区加总选定的各国产量，任何成员缺少可比基准时，不计算该组合同比。</p>
      <label>品种 <select aria-label="来源作物" value={crop} onChange={e => setCrop(e.target.value)}>
        {CROPS.map(c => <option key={c} value={c}>{names[c]}</option>)}
      </select></label>{" "}
      <label>目标年度 <select aria-label="来源年度" value={year} onChange={e => setYear(e.target.value)}>
        {years.map(y => <option key={y} value={y}>{y}</option>)}
      </select></label>
      <p>{year} 年：{adopted} / {rows.length} 个研究国家或地区采用本国来源。东南亚成员逐国列出，欧盟按共同农业统计口径作为一个研究地区。</p>
      <div className="table-scroll"><table>
        <thead><tr><th>国家／地区</th><th>本国权威数据库</th><th>已入库本国数据</th><th>{year} 年实际采用</th><th>采用与缺口说明</th></tr></thead>
        <tbody>{rows.map(r => {
          const selected = r.years[year];
          const latest = r.latest_national;
          return <tr key={r.country}>
            <td>{zhCountry(r.country)}</td>
            <td>{r.authority_url ? <a href={r.authority_url} target="_blank" rel="noreferrer">{r.authority || sources[r.configured_source || ""] || r.configured_source} ↗</a> : "待核验本国数据入口"}</td>
            <td>{latest ? <><a href={latest.source_url} target="_blank" rel="noreferrer">{latest.target_year}{latest.year_basis === "marketing_year" ? `/${latest.target_year + 1}` : " 年"} · {num(latest.value)} Mt ↗</a><br /><small>{basis[latest.commodity_basis] || latest.commodity_basis} · {latest.status === "actual" ? "实产" : latest.status === "estimate" ? "估计" : "预测"}</small><br /><small>覆盖：{r.available_years.join("、") || "口径未匹配"}</small></> : "尚无已核验记录"}</td>
            <td>{selected?.source_url ? <a href={selected.source_url} target="_blank" rel="noreferrer">{sources[selected.source] || selected.source} ↗</a> : "N/A"}<br /><small>{selected?.adopted_national ? "本国权威来源" : "补充来源"}</small></td>
            <td>{selected?.comparison_reason === "missing_local_prior" ? "已采用本国产量；缺同源上年值，同比为空" : selected?.adopted_national ? "已按该年度采用本国数据" : reasons[selected?.reason || ""] || "无可核验的本国同口径目标年数据"}{r.note && <><br /><small className="muted">{r.note}</small></>}</td>
          </tr>;
        })}</tbody>
      </table></div>
      <p>历史记录保留原机构的实产／估计／预测分类及可得日期。稻谷与精米、甘蔗与食糖不直接替换。PSD／WASDE 完整库存和消费表单独保留，不能与本国产量混算库存消费比。本土覆盖率按当年组合产量计算。</p>
      <small className="muted">政策版本：{data.policy_version} · <a href={`${base}/api/national_coverage.json`}>实际来源覆盖台账 ↗</a> · <a href={`${base}/api/policy.json`}>来源配置 ↗</a></small>
    </section>
  );
}
