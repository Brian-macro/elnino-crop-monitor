"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

type Row = { country: string; forecast: number; prev: number; yoy: number };

export default function CountryBar({ rows }: { rows: Row[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const sorted = [...rows].sort((a, b) => a.yoy - b.yoy);
    chart.setOption({
      grid: { left: 90, right: 60, top: 10, bottom: 24 },
      xAxis: { type: "value", axisLabel: { formatter: "{value}%" } },
      yAxis: { type: "category", data: sorted.map((r) => r.country), axisLabel: { fontSize: 11 } },
      series: [
        {
          type: "bar",
          data: sorted.map((r) => ({
            value: r.yoy,
            itemStyle: { color: r.yoy > 0 ? "#c0392b" : "#1e8449" },
          })),
          label: {
            show: true,
            position: "right",
            formatter: (p: { value: number }) =>
              (p.value > 0 ? "+" : "") + p.value.toFixed(1) + "%",
            fontSize: 10,
          },
        },
      ],
      tooltip: {
        formatter: (p: { dataIndex: number }) => {
          const r = sorted[p.dataIndex];
          return `${r.country}<br/>2026/27 预测：${r.forecast.toFixed(1)} Mt<br/>2025/26：${r.prev.toFixed(
            1
          )} Mt<br/>同比：${(r.yoy > 0 ? "+" : "") + r.yoy.toFixed(1)}%`;
        },
      },
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [rows]);

  return <div ref={ref} style={{ width: "100%", height: Math.max(360, rows.length * 20) }} />;
}
