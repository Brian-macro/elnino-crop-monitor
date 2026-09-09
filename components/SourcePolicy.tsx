"use client";
import { useState } from "react";
import { useData, CROPS, names, sources, base } from "@/lib/data";
import { zhCountry } from "@/lib/labels";
import { Loading } from "./Common";
type Policy = {
  version: string;
  source_matrix: {
    crop: string;
    unit: string;
    members: string[];
    history: string;
    actual: string | null;
    forecast: string;
    configured_local_source: string | null;
    fallback: string;
    fallback_reason: string | null;
    long_term: string | null;
    reference: string[];
    splice: string;
  }[];
  splicing: Record<string, string>;
  regions: Record<string, { members_by_crop: Record<string, string[]> }>;
};
export default function SourcePolicy() {
  const { data, error } = useData<Policy>("policy");
  const [crop, setCrop] = useState("rice");
  if (!data) return <Loading error={error} />;
  return (
    <section id="source-policy">
      <h2>地区与数据拼接方案</h2>
      <p>
        有本国预测数据用本国预测数据，无则用 PSD。同比只在本年与上年口径可比时计算，不跨来源计算同比。全球与地区加总各国选定产量，不平均各国同比；成员缺失不缩小样本。香港、澳门、新加坡等不进入生产研究范围。
      </p>
      <label>
        Crop
        <select value={crop} onChange={(e) => setCrop(e.target.value)}>
          {CROPS.map((c) => (
            <option key={c} value={c}>
              {names[c]}
            </option>
          ))}
        </select>
      </label>
      <p>
        东南亚成员：
        {data.regions["Southeast Asia"].members_by_crop[crop]
          .map(zhCountry)
          .join("、") || "该作物不设东南亚研究项"}
        。
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>研究地区/国家</th>
              <th>历史</th>
              <th>配置优先来源</th>
              <th>预测选择</th>
              <th>长期预测</th>
              <th>Actual</th>
            </tr>
          </thead>
          <tbody>
            {data.source_matrix
              .filter((r) => r.crop === crop)
              .map((r) => (
                <tr key={r.unit}>
                  <td>{zhCountry(r.unit)}</td>
                  <td>{sources[r.history] || r.history}</td>
                  <td>{r.configured_local_source ? sources[r.configured_local_source] || r.configured_local_source : r.forecast === "local_composite" ? "按成员国家选择" : "未配置本土来源"}</td>
                  <td>
                    {r.forecast === "local_composite" ? "按成员国家采用本国预测或 PSD" : r.fallback_reason ? `${sources[r.fallback] || "USDA PSD"}` : `${sources[r.forecast] || r.forecast} · 可比成对值齐备才采用`}
                    <br />
                    <small className="muted">{r.fallback_reason === "no_local_source" ? "未配置本土来源，使用 PSD" : r.fallback_reason === "paddy_to_milled_crosswalk_unverified" ? "稻谷转精米定义未验证，使用 PSD 精米" : r.fallback_reason || "缺少可比本年/上年对时不计算同比；实际采用见产量页"}</small>
                  </td>
                  <td>{r.long_term ? sources[r.long_term] || r.long_term : "无独立长期来源"}</td>
                  <td>
                    {r.actual ? sources[r.actual] : "N/A · 独立终值未接入"}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      <p>
        历史基础库保留 USDA PSD 修订后 Estimate，不冒充事件当年的预测。中国玉米、大豆、糖优先配置 CASDE，小麦配置 CropWatch；水稻的稻谷转精米定义尚未验证，使用 PSD 精米。NBS 实产和农业展望长期预测独立保存。配置来源不等于当前报告已可用，实际选择取决于可比成对值。
      </p>
      <p>
        固定名单根据2020–2024五年平均产量筛选：小麦/玉米/水稻≥0.5 Mt，大豆≥0.1
        Mt，糖≥0.25
        Mt。名单按政策版本审查，不随日更自动漂移。地区进出口为成员毛额，包含内部贸易。
      </p>
      <small className="muted">
        Policy: {data.version} ·{" "}
        <a href={`${base}/api/policy.json`}>完整机器可读方案 ↗</a>
      </small>
    </section>
  );
}
