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
        每个研究单元只有一个主来源。地区产量求和，不平均各国产量或同比；成员缺失不缩小样本。其他机构只作对照，主序列不混源。香港、澳门、新加坡等不进入生产研究范围。
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
              <th>短期预测</th>
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
                  <td>{sources[r.forecast] || r.forecast}</td>
                  <td>{r.long_term ? sources[r.long_term] : "同主来源"}</td>
                  <td>
                    {r.actual ? sources[r.actual] : "N/A · 独立终值未接入"}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      <p>
        海外历史与预测统一用 USDA PSD，并保留 Estimate/Forecast 区别。中国 NBS
        实产、CropWatch 短期和农业展望长期分开保存；PSD
        中国市场年历史仅作参考，不能拼接成自然年曲线。稻谷/精米口径不混用。
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
