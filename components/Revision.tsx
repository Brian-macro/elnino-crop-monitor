"use client";
import Chart, { chartBase, colors } from "./Chart";
import {
  Production,
  sameDefinition,
  sources,
  revision,
  pct,
  day,
  num,
  latest,
} from "@/lib/data";
import { Provenance } from "./Common";
import type { EChartsOption } from "echarts";
export default function Revision({
  rows,
  selected,
}: {
  rows: Production[];
  selected?: Production;
}) {
  if (!selected || selected.status !== "forecast")
    return <div className="empty">N/A · 选择 Forecast 查看历史机构预测</div>;
  const seriesRows = rows.filter(
    (r) =>
      r.status === "forecast" &&
      r.target_year === selected.target_year &&
      sameDefinition(r, selected),
  );
  const sourceList = [...new Set(seriesRows.map((r) => r.source))];
  const series = sourceList.map((s, i) => ({
    name: sources[s] || s,
    type: "line",
    showSymbol: true,
    symbolSize: 6,
    connectNulls: false,
    lineStyle: { width: 2, type: s === "usda_psd" ? "dotted" : "solid" },
    itemStyle: { color: colors[i] },
    data: seriesRows
      .filter((r) => r.source === s)
      .sort((a, b) => a.available_date.localeCompare(b.available_date))
      .map((r) => [day(r.available_date), r.value]),
  }));
  const own = seriesRows
    .filter((r) => r.source === selected.source)
    .sort((a, b) => a.available_date.localeCompare(b.available_date));
  const first = own[0];
  const actual = latest(
    rows.filter(
      (r) =>
        r.status === "actual" &&
        r.target_year === selected.target_year &&
        sameDefinition(r, selected),
    ),
  );
  // USDA PSD/WASDE are one institution; only independent institutions with identical definitions count.
  const consensusRows = sourceList
    .map((s) => latest(seriesRows.filter((r) => r.source === s))!)
    .filter(
      (r) => !(r.source === "usda_psd" && sourceList.includes("usda_wasde")),
    );
  const comparable = consensusRows.filter(
    (r) =>
      Math.abs(
        new Date(day(r.available_date)).getTime() -
          new Date(day(selected.available_date)).getTime(),
      ) /
        86400000 <=
      45,
  );
  const values = comparable.map((r) => r.value),
    mean =
      values.length >= 2
        ? values.reduce((a, b) => a + b, 0) / values.length
        : null;
  return (
    <>
      <Chart
        height={275}
        option={
          {
            ...chartBase,
            yAxis: { ...chartBase.yAxis, name: "Production · Mt" },
            series,
          } as EChartsOption
        }
        label="产量预测历史版本曲线"
      />
      <div className="metric-inline">
        <span>
          1M <b>{pct(revision(rows, selected, 1))}</b>
        </span>
        <span>
          3M <b>{pct(revision(rows, selected, 3))}</b>
        </span>
        <span>
          First → Latest{" "}
          <b>
            {pct(
              first && own.length > 1 && first.value
                ? (selected.value / first.value - 1) * 100
                : null,
            )}
          </b>
        </span>
      </div>
      <div className="panel-note">
        对照机构统计（不用于主序列拼接）：Consensus {num(mean)} · Min{" "}
        {num(mean === null ? null : Math.min(...values))} · Max{" "}
        {num(mean === null ? null : Math.max(...values))} Mt · 同口径独立机构{" "}
        {comparable.length}。少于两家时不计算分歧；45 天外报告不作为同期共识。
        {mean !== null && (
          <>
            {" "}
            Dispersion (Max − Min):{" "}
            {num(Math.max(...values) - Math.min(...values))} Mt.
          </>
        )}
      </div>
      <div className="panel-note">
        Latest forecast → Actual:{" "}
        {pct(
          actual && selected.value
            ? (actual.value / selected.value - 1) * 100
            : null,
        )}
        {actual && (
          <>
            {" "}
            ·{" "}
            <a href={actual.source_url} target="_blank" rel="noreferrer">
              {sources[actual.source]} ↗
            </a>{" "}
            · {day(actual.publication_date)}
          </>
        )}
      </div>
      <Provenance row={selected} />
    </>
  );
}
