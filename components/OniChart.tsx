"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

type Point = { season: string; year: number; oni: number };

const SEASON_RANK: Record<string, number> = {
  DJF: 1, JFM: 2, FMA: 3, MAM: 4, AMJ: 5, MJJ: 6,
  JJA: 7, JAS: 8, ASO: 9, SON: 10, OND: 11, NDJ: 12,
};

export default function OniChart({ series }: { series: Point[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const data = series.map((p) => {
      const t = p.year + (SEASON_RANK[p.season] - 1) / 12;
      return [t, p.oni];
    });
    chart.setOption({
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: "value",
        min: series[0].year,
        max: series[series.length - 1].year + 1,
        axisLabel: { formatter: (v: number) => String(Math.floor(v)) },
      },
      yAxis: { type: "value", name: "ONI (°C)" },
      series: [
        {
          type: "line",
          data,
          showSymbol: false,
          lineStyle: { width: 1, color: "#555" },
          markArea: {
            itemStyle: { color: "rgba(192,57,43,0.08)" },
            data: [[{ yAxis: 0.5 }, { yAxis: 3 }]],
          },
        },
      ],
      visualMap: {
        show: false,
        dimension: 1,
        pieces: [
          { gt: 0.5, color: "#c0392b" },
          { lt: -0.5, color: "#2471a3" },
        ],
        seriesIndex: 0,
      },
      tooltip: {
        trigger: "axis",
        formatter: (ps: { dataIndex: number }[]) => {
          const p = series[ps[0].dataIndex];
          return `${p.season} ${p.year}<br/>ONI：${(p.oni > 0 ? "+" : "") + p.oni.toFixed(2)}°C`;
        },
      },
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [series]);

  return <div ref={ref} style={{ width: "100%", height: 420 }} />;
}
