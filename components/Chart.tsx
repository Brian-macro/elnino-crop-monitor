"use client";
import { useEffect, useRef } from "react";
import * as echarts from "echarts";
export const colors = ["#16995d", "#6e9fa8", "#b0b970", "#cc866d", "#8d96b2"];
export const chartBase = {
  backgroundColor: "transparent",
  color: colors,
  textStyle: {
    color: "#738577",
    fontFamily: "Microsoft YaHei, sans-serif",
    fontSize: 11,
  },
  grid: { top: 50, bottom: 62, left: 60, right: 35 },
  tooltip: {
    trigger: "axis",
    backgroundColor: "#ffffff",
    borderColor: "#dce6de",
    textStyle: { color: "#264a36" },
    confine: true,
  },
  legend: { top: 5, textStyle: { color: "#748679" }, type: "scroll" },
  xAxis: {
    type: "time",
    axisLine: { lineStyle: { color: "#d5e0d7" } },
    splitLine: { show: false },
  },
  yAxis: {
    type: "value",
    scale: true,
    splitLine: { lineStyle: { color: "#e8eee8", type: "dashed" } },
    axisLabel: { color: "#8a9b8b" },
  },
  dataZoom: [
    { type: "inside" },
    {
      type: "slider",
      height: 15,
      bottom: 15,
      borderColor: "transparent",
      fillerColor: "#76b38a28",
      dataBackground: { lineStyle: { color: "#c0d4c3" } },
    },
  ],
  animation: false,
};
export default function Chart({
  option,
  height = 320,
  onClick,
  label = "研究图表",
}: {
  option: echarts.EChartsOption;
  height?: number;
  onClick?: (name: string) => void;
  label?: string;
}) {
  const el = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!el.current) return;
    const c = echarts.init(el.current);
    c.setOption(option);
    if (onClick) c.on("click", (p) => onClick(p.name));
    const ro = new ResizeObserver(() => c.resize());
    ro.observe(el.current);
    return () => {
      ro.disconnect();
      c.dispose();
    };
  }, [option, onClick]);
  return (
    <div
      ref={el}
      role="img"
      aria-label={label}
      style={{ height, width: "100%" }}
    />
  );
}
